from ampConfig import amplifierConfig
import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox
import time

class ConfigDialog(simpledialog.Dialog):
    # Class variables for default config values
    ampname = ""
    ampaddress = ""

    # Simple config dialog to let user set IP address
    def body(self, master):

        # Config field and label layouts in a grid - labels:
        tk.Label(master, text="Amplifier Name:").grid(row=0, sticky="w")
        tk.Label(master, text="IP Address:").grid(row=1, sticky="w")

        # Config fields:
        self.entry1 = tk.Entry(master)
        self.entry1.insert(0, ConfigDialog.ampname)
        self.entry2 = tk.Entry(master)
        self.entry2.insert(0, ConfigDialog.ampaddress)
        self.checkVar = tk.IntVar()
        self.savecheck = tk.Checkbutton(master, text='Save Config', variable=self.checkVar)

        self.entry1.grid(row=0, column=1)
        self.entry2.grid(row=1, column=1)
        self.savecheck.grid(row=3, column=1)

        return self.entry1 # initial focus

    # The apply function is called when the user hits 'OK'
    def apply(self):
        amp_name = self.entry1.get()
        ip_address = self.entry2.get()
        save_config = self.checkVar.get()
        self.result = (amp_name, ip_address, save_config)

# Main GUI class - quick and dirty layout and callbacks.
# Eventually this will likely have the updates being handled in a separate thread
# so the GUI doesn't stutter when it's talking to the amp (and it would be able to
# poll the amp periodically to detect source changes done via the front panel or
# remote), but this is OK enough for a first stab.

class RotelRemoteGuiMain:

    # Utility method to try to connect to an amp's IP address
    def connectIfPossible(self):
        if self.ampConfig == None:
            return (False, "No config loaded")

        # Use the ampConfig's connect method to set up a TCP link
        (retcode, connectMessage) = self.ampConfig.connect()
        if retcode == False:
            return

    # GUI class constructor - set up our defaults and widget layouts.
    def __init__(self, ampConfig):
        self.ampConfig = ampConfig

        self.connectIfPossible()
        connected = self.ampConfig.isConnected()

        # couple of defaults
        connectText = 'Not Connected'
        powerOn = False
        self.bypassValue = True

        # create a main window with a frame, the window can be expanded
        self.mainwin = tk.Tk()
        self.mainwin.title("Rotel Remote CB v0.01")
        self.mainwin.geometry("600x400")
        self.mainframe = tk.Frame(self.mainwin)
        self.mainframe.pack(fill='both', expand=1)

        self.rowCount = 6
        # let's start with 3 columns then play with layouts to see what works
        # power/volume in the left, sources in the middle, status/config on right
        self.mainframe.grid_columnconfigure(tuple(range(3)), weight=1)
        self.mainframe.grid_rowconfigure(tuple(range(self.rowCount)), weight=1)

        # Power button at top left (0, 0)
        self.powerButton = tk.Button(self.mainframe, text='Power', borderwidth=2, relief='groove', command=self.powerToggle)
        self.powerButton.grid(column=0, row=0, sticky='news', columnspan=1)

        self.sourcesLabel = tk.Label(self.mainframe, text='Sources', borderwidth=2, relief='groove')
        self.sourcesLabel.grid(row=0, column=1, sticky='news', columnspan=1)

        self.statusLabel = tk.Label(self.mainframe, text='Status', borderwidth=2, relief='groove')
        self.statusLabel.grid(row=0, column=2, sticky='news', columnspan=1)

        # Config button at bottom right (2, rowCount -1)
        self.configButton = tk.Button(self.mainframe, text='Settings', borderwidth=2, relief='groove', command=self.show_dialog)
        self.configButton.grid(column=2, row=(self.rowCount - 1), sticky='news', columnspan=1)

        # Mute button at bottom left (0, rowCount -1)
        self.muteButton = tk.Button(self.mainframe, text='Mute is Off', borderwidth=2, relief='groove', command=self.muteToggle)
        self.muteButton.grid(column=0, row=self.rowCount - 1, sticky='news', columnspan=1)

        # source frame in the middle will have list and scrollbar
        self.sourceFrame = tk.Frame(self.mainframe)
        self.sourceScroll = tk.Scrollbar(self.sourceFrame)
        self.sourceScroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.sourceList = tk.Listbox(self.sourceFrame, bd=2, selectmode=tk.SINGLE, yscrollcommand=self.sourceScroll.set, exportselection=False)
        self.sourceList.bind('<<ListboxSelect>>', self.selectSource)
        self.sourceList.pack(side=tk.LEFT, expand=1, fill=tk.BOTH)
        self.sourceFrame.grid(row=1, column=1, rowspan=(self.rowCount - 2), sticky='news', columnspan=1)
        self.sourceScroll.config(command=self.sourceList.yview)

        # populate the source list using the ampConfig's methods
        sourcenames = []
        sources = self.ampConfig.getSourceIds()
        for s in sources:
            self.sourceList.insert(tk.END, ampConfig.getSourceLabel(s))

        # Volume slider
        self.volumeValue = tk.IntVar()

        # tone sliders
        self.bassValue = tk.IntVar()
        self.trebleValue = tk.IntVar()
        self.balanceValue = tk.IntVar()

        # get the amp's supported volume range. Note that Rotel amps can sometimes have
        # fixed volumes for selected inputs, or an amp could have a preset maximum that
        # does not match this config file. YMMV.
        minVol, maxVol = self.ampConfig.getVolumeMinMax()

        self.volumeSlider = tk.Scale(self.mainframe, label='Volume', variable=self.volumeValue, orient=tk.HORIZONTAL, from_=minVol, to=maxVol, command=self.volumeUpdate)
        self.volumeSlider.grid(row=(self.rowCount - 1), column=1, sticky='news', columnspan=1)
        self.volumeSlider.set(20)

        self.toneFrame = tk.Frame(self.mainframe)

        # Get the tone sliders' min/max values from the amp's config file
        tone_min, tone_max = self.ampConfig.getToneMinMax()
        self.bassSlider = tk.Scale(self.toneFrame, label='Bass', variable=self.bassValue, orient=tk.HORIZONTAL, from_=tone_min, to=tone_max, command=self.bassUpdate)
        self.bassSlider.pack(side=tk.TOP, expand=1, fill=tk.Y)
        self.bassSlider.set(0)

        self.trebleSlider = tk.Scale(self.toneFrame, label='Treble', variable=self.trebleValue, orient=tk.HORIZONTAL, from_=tone_min, to=tone_max, command=self.trebleUpdate)
        self.trebleSlider.pack(side=tk.TOP, expand=1, fill=tk.Y)
        self.trebleSlider.set(0)

        # Tone bypass button will disable the bass and treble sliders if the bypass is on.
        self.bypassButton = tk.Button(self.toneFrame, text='Bypass is on', borderwidth=2, relief='groove', command=self.bypassToggle)
        self.bypassButton.pack(side=tk.TOP, expand=1, fill=tk.Y)

        balance_min, balance_max = self.ampConfig.getBalanceMinMax()
        self.balanceSlider = tk.Scale(self.toneFrame, label='Balance (L-R)', variable=self.balanceValue, orient=tk.HORIZONTAL, from_=balance_min, to=balance_max, command=self.balanceUpdate)
        self.balanceSlider.pack(side=tk.TOP, expand=1, fill=tk.Y)
        self.balanceSlider.set(0)

        self.toneFrame.grid(row=1, column=0, sticky='news', columnspan=1)

        # Status frame will have one big free-form status label
        self.statusFrame = tk.Frame(self.mainframe)

        # Enable the power button if we're connected
        if connected:
            self.powerButton['state'] = tk.NORMAL
            connLabelText = 'Connected'
        else:
            connLabelText = 'Not Connected'

        addr = self.ampConfig.getAddress()
        name = self.ampConfig.getName()

        # Put some config info on the status label
        connLabelText += '\nConfig: ' + name

        if addr != None and len(addr) > 0:
            connLabelText += '\nIP Address: ' + addr
        else:
            connLabelText += '\nNo address - please configure'

        self.connLabel = tk.Label(self.statusFrame, text=connLabelText, borderwidth=2, relief='groove')
        self.connLabel.pack(side=tk.TOP, expand=1, fill=tk.BOTH)
        self.statusFrame.grid(row=1, column=2, rowspan=(self.rowCount -2), sticky='news', columnspan=1)

        # The adjustControls method queries stuff from the amp and sets the widgets accordingly
        self.adjustControls(doPower=True)

        # Start the GUI
        self.mainwin.mainloop()

    # adjustControls does all fo the heavy lifting when it comes to updating the interface's
    # controls to match the current state of the amp. If connected, it checks the power state
    # and if the amp is on it queries a bunch of the config values.

    def adjustControls(self, doPower=False):

        # There isn't really a good way that I found to figure out if a source's
        # volume is set to a fixed value. This attempts to handle that by setting
        # the 'fixed' value to false, then handling a special condition later when
        # we attempt to set the volume (see notes around the setVolume function)
        self.volumeFixed = False
        self.volumeSlider.config(label='Volume')

        # See if we are connected
        connected = self.ampConfig.isConnected()
        if not connected:
            # disable a bunch of controls
            self.powerButton['state'] = tk.DISABLED
            self.muteButton['state'] = tk.DISABLED
            self.sourceList['state'] = tk.DISABLED
            self.volumeSlider['state'] = tk.DISABLED
            self.bassSlider['state'] = tk.DISABLED
            self.trebleSlider['state'] = tk.DISABLED
            self.balanceSlider['state'] = tk.DISABLED
            self.bypassButton['state'] = tk.DISABLED
        else:
            # We're connected, so we need to find our power state before
            # adjusting the other widgets. The 'doPower' argument will be false
            # if we are calling this function from a callback that would need
            # power to operate, so it's a shortcut that makes an assumption

            if doPower == False:
                # assume the power is on
                powerOn = True
            else:
                # query the power - if the amp is in standby, this is the only
                # query it can answer
                powerOn = False
                (ret, powerResp) = self.ampConfig.queryPower()
                if ret == True and 'power' in powerResp:
                    if powerResp['power'] == 'on':
                        powerOn = True

            if powerOn:
                # great, the amp's power is on, let's activate some controls
                self.powerButton.config(text='Power is on')
                self.muteButton['state'] = tk.NORMAL
                self.sourceList['state'] = tk.NORMAL
                self.volumeSlider['state'] = tk.NORMAL
                self.bassSlider['state'] = tk.NORMAL
                self.trebleSlider['state'] = tk.NORMAL
                self.balanceSlider['state'] = tk.NORMAL
                self.bypassButton['state'] = tk.NORMAL

                # get source information - this returns a bunch of config info
                # about the amp all in one go.
                (ret, resp) = self.ampConfig.querySourceInfo()
                if not ret:
                    # if the query fails, we can't do much.
                    # TODO: do a popup here with the error message from ampConfig
                    return
                # the 'resp' return value is a dict with a bunch of keys that we
                # map to widgets
                if 'source' in resp:
                    sourceMsg = resp['source']
                    # our source list is in the same order as the ampConfig's source
                    # list so we can re-use the index to highlight our list value.
                    # The longer-term goal would be to add the ability to show/hide
                    # sources, so this may not always be the case, but for now it works.
                    self.sourceList.selection_set(self.ampConfig.getSourceIndex(sourceMsg))

                # get volume
                if 'volume' in resp:
                    volMsg = resp['volume']
                    self.volumeValue.set(int(volMsg))

                # mute
                if 'mute' in resp:
                    self.muteButton.config(text='Mute is ' + resp['mute'])

                # tone bypass state
                if 'bypass' in resp:
                    self.bypassButton.config(text='Bypass is ' + resp['bypass'])
                    if resp['bypass'] == 'on':
                        self.bypassValue = True
                        # disable the bass and trble sliders
                        self.trebleSlider['state'] = tk.DISABLED
                        self.bassSlider['state'] = tk.DISABLED
                    else:
                        self.bypassValue = False
                        # enable the bass and treble sliders
                        self.trebleSlider['state'] = tk.NORMAL
                        self.bassSlider['state'] = tk.NORMAL

                # find and set the bass and treble values
                if 'bass' in resp:
                    self.bassValue.set(resp['bass'])
                if 'treble' in resp:
                    self.trebleValue.set(resp['treble'])

            else:
                # power is not on, but we're connected so we must be in standby
                self.powerButton.config(text='<Standby>')
                self.muteButton['state'] = tk.DISABLED
                self.sourceList['state'] = tk.DISABLED
                self.volumeSlider['state'] = tk.DISABLED
                self.bassSlider['state'] = tk.DISABLED
                self.trebleSlider['state'] = tk.DISABLED
                self.balanceSlider['state'] = tk.DISABLED
                self.bypassButton['state'] = tk.DISABLED

    ## Callback functions

    # selectSource is called when a source is clicked in the sources list
    def selectSource(self, evt):
        w = evt.widget
        index = int(w.curselection()[0])

        # For now, our sources list matches the list of sources in the ampConfig.
        # This may not always be the case in the future.
        sources = self.ampConfig.getSourceIds()
        sourceId = sources[index]

        # Ask the amp to set the new source
        (ret, newSource) = self.ampConfig.setSource(sourceId)

        # adjust widgets based on new source value
        self.adjustControls()

    # Called when the power button is clicked
    def powerToggle(self):
        # Send a power toggle command to the amp
        self.ampConfig.powerToggle()

        # powering on might take a few seconds, sleep for 5 sec.
        time.sleep(5)
        # adjust the controls, along with a power query
        self.adjustControls(doPower=True)

    # Toggle the mute status
    def muteToggle(self):
        self.ampConfig.muteToggle()
        self.adjustControls()

    # Toggle the tone bypass status
    def bypassToggle(self):
        # we cached the previous bypass value when we connected or
        # powered on, so we ask for the opposite state since the amp
        # does not have a 'bypass_toggle' command.
        if self.bypassValue == True:
            self.ampConfig.setBypass(False)
        else:
            self.ampConfig.setBypass(True)
        self.adjustControls()

    # Pop up the config dialog.
    def show_dialog(self):
        # Default values are set using class variables on the
        # conifg popup before it is created.
        ConfigDialog.ampname = self.ampConfig.getName()
        ConfigDialog.ampaddress = self.ampConfig.getAddress()
        dialog = ConfigDialog(self.mainwin, title="Configure Remote")

        if dialog.result:
            # we got an 'OK' - process the values
            self.ampConfig.setName(dialog.result[0])
            self.ampConfig.setAddress(dialog.result[1])

            # This will save the configuration but will not attempt to
            # connect - the user will need to restart the GUI to connect.
            # TODO: connect automatically if address is new/changed
            if dialog.result[2] == 1:
                self.ampConfig.saveConfig()

    # Callback for adjusting the volume level
    def volumeUpdate(self, newvalue):
        if self.volumeFixed == False:
            # if we don't think the volume level for the current source is fixed, update the volume
            ret, replies = self.ampConfig.setVolume(newvalue)

            # Special case that was mentioned previously - if the volume is
            # fixed, the amp will ignore this command and will not send a
            # response - so if we successfully sent the command (ret is true)
            # but we did not get anything in the replies, we assume the volume is
            # fixed and we don't try updating the volume again until the source is
            # changed.
            if ret == True and len(replies) == 0:
                self.volumeFixed = True
                # update the volume slider label
                self.volumeSlider.config(label='Volume (fixed)')

    # Callback for the bass slider
    def bassUpdate(self, newvalue):
        if self.bypassValue == False:
            ret, replies = self.ampConfig.setBass(newvalue)


    # Callback for the treble slider
    def trebleUpdate(self, newvalue):
        if self.bypassValue == False:
            ret, replies = self.ampConfig.setTreble(newvalue)

    # Balance slider callback - always active
    def balanceUpdate(self, newvalue):
        ret, replies = self.ampConfig.setBalance(newvalue)






