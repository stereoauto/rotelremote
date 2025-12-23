import os
import json
import socket

def findConfigs():
    # search for config JSON files in the 'configs' directory
    configPath = "configs"
    contents = os.listdir(configPath)
    configList = []
    for item in contents:
        try:
            with open(item, 'r') as file:
                data = json.load(file)
                configName = None
                if 'name' in data:
                    configName = data['name']

                configList.add({ filename: item, name: configName })
        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            pass
    return configList

# This class attempts to implement an abstraction layer between an integrated amp
# or preamp's usual functions (source selection, tone controls, volume, mute, etc.)
# and translate those functions to IP-based commands based on a configuration file.
#
# This implementation has been tested using a Rotel A14 mkII integrated amp that
# is running firmware 3.08. See README in the configs dir for more details. No
# guarantees are made with respect to this library's# functionality with this or
# any other amplifier, it is provided as-is.

# Functions here typically return a tuple that contains a true/false return code
# and either a returned value/list (ir the return code is true) or an error string
# if the return code is false.

class amplifierConfig:
    # Parse a JSON configuration file that provides command and query info.
    def readConfig(self, fname):
        try:
            with open(fname, 'r') as file:
                # Use json lib to parse the file
                data = json.load(file)

                # Grab some values and populate our instance variables
                self.configName = None
                if 'name' in data:
                    self.configName = data['name']
                # see if our three main lists are in the file - we need all 3 to work.
                if 'sources' in data and 'queries' in data and 'commands' in data:
                    self.configValid = True
                    self.configData = data
                else:
                    self.configValid = False
                    self.configData = None
        # the usual exceoption handling for files.
        except FileNotFoundError:
            print('File not found: ' + fname)
            pass
        except json.JSONDecodeError:
            print('JSON decode error: ' + fname)
            pass


    # Constructor for the ampConfig
    def __init__(self, fname):

        # set defaults
        self.filename = None
        self.configData = None
        self.configValid = False
        self.connected = False
        self.ampSocket = None

        if fname != None:
            self.filename = fname
            self.readConfig(fname)

    # access methods - config name
    def setConfigName(self, configName):
        self.configName = configName
        self.configData['name'] = configName

    # set the configuration's IP address
    def setConfigAddress(self, ipaddress):
        self.configData['address'] = ipaddress

    # try to connect tot he amplifier's IP address/port
    def connect(self):
        if not self.configValid:
            return False, "Invalid configuration"
        if self.configData['address'] == "":
            return False, "Missing IP address"

        # Construct our address
        addr = (self.configData['address'], self.configData['port'])
        self.ampSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Timeout defines how long we wait until we decide the amp has
        # stopped sending data for the current action. On initial connect,
        # we wait for 5 seconds but later we use th value from the config
        # (250ms during testing, this could change)
        self.ampSocket.settimeout(5)
        try:
            self.ampSocket.connect(addr)
            self.connected = True
            self.ampSocket.settimeout(self.configData['timeout'])
            return (True, "Success")
        except TimeoutError:
            return (False, "Timeout error" )
        except ConnectionRefusedError:
            return (False, "Connection refused")

    # Access method to query connection state
    def isConnected(self):
        return self.connected

    # Close the current connection
    def close(self):
        if self.connected:
            self.ampSocket.close()
        self.connected = False
        self.ampSocket = None

    # Utility method to bundle a command and read the replies
    def doCommand(self, commandString, optArg=None, argLength=None, doLoop=True):

        # Check our setup before trying to send
        if not self.configValid:
            return (False, "Invalid config")
        if not self.connected:
            return (False, "Not connected")

        # See if we recognize this command
        if commandString not in self.configData["commands"]:
            return (False, "Missing command")

        # Translate the command to a protocol command string
        cmdString = self.configData["commands"][commandString]

        # Sub in an argument if we need to (this could be more flexible, we have
        # a few special cases/formatting in the methods below)
        if optArg != None and '#' in cmdString:
            if argLength != None:
                # Rotel's arguments all need to be the same length, so '5' becomes '05'
                # for 2-digit numbers.
                newCmd = cmdString.replace('#', str(optArg).zfill(argLength))
            else:
                newCmd = cmdString.replace('#', str(optArg))
            cmdString = newCmd

        # send the command on the socket
        self.ampSocket.sendall(cmdString.encode('utf-8'))
        data = bytes()
        # this took a bit to figure out - multiple responses could be sent for a single
        # command, so we loop on the recv() until we run out of replies.
        try:
            if doLoop == True:
                while True:
                    data += self.ampSocket.recv(1024)
            else:
                data += self.ampSocket.recv(1024)
        except TimeoutError:
            # drop out of the recv() loop
            pass

        # the data is a 'bytes' object so we need to decode it
        dataStr = data.decode('utf-8')
        # responses are delimited my dollar signs, so let's make a list and check it
        responses = dataStr.split('$')
        respdict = dict()
        for r in responses:
            if '=' in r:
                elems = r.split('=')
                respdict[elems[0]] = elems[1]
        # Generally the GUI ignores the responses from the commands and does its own new
        # queries after a command finishes - so we don't do any special processing on the
        # responses here for now. For queries we handle these differently (see below)
        return (True, respdict)

    # Send a configuration query to the amp and read the reply
    def doQuery(self, queries):
        # Contrary to the Rotel specs, we can get multiple responses from a single query.
        queryStr = ''

        # Check if our config state is valid
        if not self.configValid:
            return (False, "Invalid config")
        if not self.connected:
            return (False, "Not connected")

        # Loop through the query string list and translate them to queries.
        # Queries don't have any arguments so no need to sub in numbers.
        for queryString in queries:
            if queryString not in self.configData["queries"]:
                return (False, "Missing query")
            queryStr += self.configData["queries"][queryString]
        # Send all of thr queries in one packet/stream
        self.ampSocket.sendall(queryStr.encode('utf-8'))

        # Responses may come back in pieces so we loop until we get a timeout
        data = bytes()
        try:
            while True:
                data += self.ampSocket.recv(1024)
        except TimeoutError:
            # drop out of the recv() loop
            pass
        dataStr = data.decode('utf-8')
        responses = dataStr.split('$')
        respdict = dict()
        # The replies are using the Rotel amp's nomenclature for the values - for
        # example, if we query for 'volume' from the ampConfig's query list,
        # the reply will have 'amp:volume=##$'. So to give the GUI the same key
        # back that it asked for, we have to map the query string back to the
        # query key.
        for r in responses:
            if '=' in r:
                elems = r.split('=')
                # a query like 'amp:volume?' will come back as 'amp:volume=##$'.
                for q, qstring in self.configData['queries'].items():
                    # strip the last character ('?') off the qstring
                    qTerm = qstring[:-1]
                    if elems[0] == qTerm:
                        respdict[q] = elems[1]
        return (True, respdict)

    ## Wrapper functions to send the supported queries

    # query power state
    def queryPower(self):
        return self.doQuery(["power"])

    # get current source
    def querySource(self):
        return self.doQuery(["source"])

    # get current volume
    def queryVolume(self):
        return self.doQuery(["volume"])

    def querySourceInfo(self):
        # multi query to get all info about the current source
        return self.doQuery(['source', 'volume', 'bass', 'treble', 'mute',
                             'balance', 'bypass'])

    ## Command wrappers to give access to supported commands

    # set a new volume level
    def setVolume(self, volValue):
        # volume numeric value, needs to be zero-padded if < 10
        return self.doCommand('volume_set', volValue, 2, doLoop=False)

    # Set a new active source
    def setSource(self, sourceId):
        # This isn't ideal, but the query source returns just the source ID, but
        # to set the source one needs 'amp:source!' instead of just 'source!'. Maybe
        # another config item is needed in the sources JSON. This will likely
        # not work for older amp firmware versions.
        sourceCmd = 'amp:' + sourceId + '!'

        # Send the command
        self.ampSocket.sendall(sourceCmd.encode('utf-8'))

        # We only expect a single reply back so no need for a loop
        try:
            data = self.ampSocket.recv(1024)
        except TimeoutError:
            return (False, 'Timeout during query')

        # decode the reply and return it
        dataStr = data.decode('utf-8')
        if dataStr.endswith('$'):
            dataStr = dataStr[:-1]
        dataStr.replace('$', '')
        value = dataStr.split('=')[1]
        return (True, value)

    # Utility methods for getting source list and mapping indexes to labels

    # Get a list of supported sources
    def getSourceIds(self):
        names = []
        if 'sources' in self.configData:
            for key in self.configData['sources'].keys():
                names.append(key)
        return names

    # Get the index of a source in the list
    def getSourceIndex(self, sourceid):
        if 'sources' in self.configData:
            i = 0
            for s in self.configData['sources'].keys():
                if s == sourceid:
                    return i
                i += 1
        return None

    # get the user-friendly label for a source
    def getSourceLabel(self, sourceid):
        if 'sources' in self.configData:
            if sourceid in self.configData['sources']:
                return self.configData['sources'][sourceid]['label']
        return None

    # get the configured IP address
    def getAddress(self):
        if 'address' in self.configData:
            return self.configData['address']
        return None

    # fetch the volume parameters
    def getVolumeMinMax(self):
        min = 0
        max = 100
        if 'volume_min' in self.configData:
            min = self.configData['volume_min']
        if 'volume_max' in self.configData:
            max = self.configData['volume_max']
        return min, max

    def getToneMinMax(self):
        min = -10
        max = 10
        if 'tone_min' in self.configData:
            min = self.configData['tone_min']
        if 'tone_max' in self.configData:
            max = self.configData['tone_max']
        return min, max

    def getBalanceMinMax(self):
        min = -10
        max = 10
        if 'balance_min' in self.configData:
            min = self.configData['balance_min']
        if 'balance_max' in self.configData:
            max = self.configData['balance_max']
        return min, max

    # fetch the amplifier config name
    def getName(self):
        return self.configData['name']

    # set the amplifier config name
    def setName(self, newname):
        self.configData['name'] = newname

    # get the IP address
    def getAddress(self):
        return self.configData['address']

    # set the IP address
    def setAddress(self, newaddress):
        self.configData['address'] = newaddress

    # More command wrappers - toggle the power value
    def powerToggle(self):
        return self.doCommand('power_toggle')

    # Toggle the muting status
    def muteToggle(self):
        return self.doCommand('mute_toggle')

    # Set the tone bypass status
    def setBypass(self, bypassVal):
        if bypassVal == False:
            return self.doCommand('bypass_off')
        else:
            return self.doCommand('bypass_on')

    # set the new bass level, note the special formatting
    def setBass(self, bassValue):
        # bass value is 000 for none, or -## or +##
        bassInt = int(bassValue)
        if bassInt == 0:
            bstring = "000"
        elif bassInt > 0:
            bstring = '+' + str(bassInt).zfill(2)
        else:
            bstring = str(bassInt).zfill(3)
        return self.doCommand('bass_set', bstring, doLoop=False)

    # set the new treble level, note the special formatting (same as bass)
    def setTreble(self, trebValue):
        # treb value is 000 for none, or -## or +##
        trebInt = int(trebValue)
        if trebInt == 0:
            tstring = "000"
        elif trebInt > 0:
            # zfill will pad with zeroes but not add the '+'
            tstring = '+' + str(trebInt).zfill(2)
        else:
            # zfill handles negative numbers properly
            tstring = str(trebInt).zfill(3)
        return self.doCommand('treble_set', tstring, doLoop=False)

    # set the new balance level, note the special formatting (subtly different)
    def setBalance(self, balValue):
        balInt = int(balValue)
        # balance value is 000 (centered), or L## or R##
        if balInt == 0:
            bstring = "000"
        elif balInt > 0:
            # zfill will pad with zeroes but not add the '+'
            bstring = 'r' + str(balInt).zfill(2)
        else:
            # zfill handles negative numbers properly
            bstring = 'l' + str(abs(balInt)).zfill(2)
        return self.doCommand('balance_set', bstring, doLoop=False)

    # write config data to a JSON file
    def saveConfig(self):
        if self.filename == None:
            return False, "No file name"
        with open(self.filename, 'w') as json_file:
            json.dump(self.configData, json_file, indent=4)
        return True, "Save successful"

    # these show/hide methods may be used in the future but they are just stubs for now
    def hideSource(self, sourceName):
        if sourceName in self.configData['sources']:
            sources[sourceName].visible = False

    def showSource(self, sourceName):
        if sourceName in self.sources:
            sources[sourceName].visible = True











