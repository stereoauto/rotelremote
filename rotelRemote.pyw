import os
import sys
from ampConfig import amplifierConfig
from rotelRemoteGui import RotelRemoteGuiMain

def main():
    # TODO: arg parsing, config selection - only one config so far.
    configDir = "configs"
    configFile = os.path.join(configDir, "Rotel_A14_mkii_fw3_08.json")

    # Read the amp config from the config file
    myAmpConfig = amplifierConfig(configFile)

    # start the GUI and pass in the config file
    gui = RotelRemoteGuiMain(myAmpConfig)

    # disconnect from the amp if needed
    myAmpConfig.close()

if __name__ == "__main__":
    main()