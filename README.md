# polaris-gui

This repository contains source code for the GUI application designed to interface with POLARIS during testing.

## Project Setup

1. Install/verify python3 installation
2. Create virtual environment with `venv` using `python3 -m venv .venv`
3. Activate the python virtual environment. You can either:
    1. Associate the `.venv` folder with the project in VSCode (`cmd + shift + p` to open command palette > `Python: Select Interpreter`)
    2. Run `source .venv/bin/activate` you will need to do this whenever open a new terminal
        * Note: On Windows run `.\.venv\Scripts\activate`. If you get an error saying "Running scripts is disabled on this system", run `Set-ExecutionPolicy Unrestricted -Scope Process` and then try the activation command again.
4. Install project dependencies with `pip install -r requirements.txt`
5. Run the application with `python .\src\Remote_Debugger_V15.py`
6. Deactive the virtual environment with `deactivate`
    * Note: `deactivate` should work for both Linux and Windows.

## Important usage notes

- May need to put CAN line down and back up before CAN works properly
- salinity is measured in big numbers - assumes range is between 40,000 and 55,000, graphs values in units of µS/cm * 1000
- temp is assumed to be between -15 and 140 degrees celsius
- If Raspberry pi is returning the message "device or resource busy" when attempting to put up CAN1 line with loopback on, and you have confirmed no other application/session is using the pi, try "sudo reboot"

## Comments on repo structure
* \test_scripts contains automation scripts for manual and hardware-in-the-loop testing of the GUI
* \tests contains automated pytest tests
* \src\test_files contains files used to produce simpler & experimental versions of features and functions used in the GUI

## Steps for setting up mainframe/CAN stuff (for testing)

- Need: mainframe, 1 nucleo with CAN hat (use a CAN test board) to transmit CAN messages, bullet wifi modem, special ethernet cable for bullet - mainframe, CAN connector with wires thing (white = 12V power, black = ground, brown = CAN high, blue = CAN low), micro-USB cable, assorted alligator clips

1. Connect bullet to mainframe with ethernet cable
2. Set up power supply (12V, 2A), connect power & ground appropriately - green, yellow light for ethernet, red lights on for pi = correct setup
3. Connect nucleo to mainframe (Nucleo wires: white = CAN high, blue = CAN low, green = ground)
4. Ensure laptop is connected to raye_wifi; "sudo putty" on ubuntu laptop or just open putty; On ubuntu laptop, do serial connection for nucleo with serial line /dev/ttyACM0, baudrate = 115200 (static ip address: sailbot@192.168.0.10)
    - Login as: "sailbot"; password is "sailbot" (without the quotation marks)
    - Note: to connect to the PI on the bullet connect to raye_wifi and run ssh sailbot@192.168.0.10 . For first time you will also likely have to configure your own IPv4 settings to an IP like 192.168.0.xx where xx is any number but 10 and netmask to 255.255.255.0. (Don't set a gateway.) Turn your wifi off and on and now you should always be setup to ssh in for all future connections. See below for how to do this on Linux and see Adarsh's message for how to do this on Windows.
5. If necessary, re-flash nucleo with code "FDCAN_Serial" - on github somewhere - ask Alisha if necessary
6. Set up can line on raspberry pi (run ip up)
7. Run GUI

note: add auto setup of can line (run ip up) to program
note: add function to reset can line (down then up)

"Can1 down", "sudo ip link set can1 down"
Regular CAN up:
"CAN1 Up", "sudo ip link set can1 up type can bitrate 500000 dbitrate 1000000 fd on"
CAN up command with loopback (use if using candump can1):
"CAN1 Up", "sudo ip link set can1 up type can bitrate 500000 dbitrate 1000000 fd on loopback on"
