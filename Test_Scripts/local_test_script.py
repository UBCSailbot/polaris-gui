"""
Contains test functions 
Automatically SSHes into rpi and sends a CAN Frame simulating external system/data every delay secs
Outputs support messages through terminal

Use Ctrl+C or Space to stop sending
"""

import multiprocessing


can_line = "can0"

# Time between sent frames (in secs)
delay = 1

# CAN Frame IDs
temp_sensor_id = "100" 
pH_id = "110" 
sal_id = "120" 

slope = 0.1
data_min = 0.2
data_max = 0.8
slope_data = data_min

### ----------  Utility Functions ---------- ###
# Works only for positive numbers
def convert_to_hex(decimal, num_bytes):
    return format(decimal, "X").zfill(2 * num_bytes)

def convert_to_little_endian(hex_str):
    raw = bytes.fromhex(hex_str)
    return raw[::-1].hex()

def convert_from_little_endian_str(hex_str):
    raw = bytes.fromhex(hex_str)
    big_endian = raw[::-1].hex()
    return int(big_endian, 16)

def generate_slope_data():
    global slope
    global slope_data
    if ((slope_data < data_min) or (slope_data > data_max)):
        slope *= -1

    slope_data += slope

def produce_gps_data(client):
    '''
    [31:0] uint32_t latitude
    Latitude in (Decimal Degrees + 90) * 1,000,000

    [63:32] uint32_t longitude
    Longitude in (Decimal Degrees + 180) * 1,000,000

    [95:64] uint32_t seconds
    UTC seconds * 1000.

    [103:96] uint8_t minutes
    UTC minutes.

    [111:104] uint8_t hours
    UTC hours.

    [127:112] reserved
    unused

    [159:128] uint32_t speed
    Speed over ground in km/h * 1000.
    '''

    try:
        lat = convert_to_little_endian(convert_to_hex(int((slope_data + 90) * 1000000), 4))
        lon = convert_to_little_endian(convert_to_hex(int((slope_data + 90) * 1000000), 4))
        secs = convert_to_little_endian(convert_to_hex(10, 2))
        mins = convert_to_little_endian(convert_to_hex(20, 2))
        hrs = convert_to_little_endian(convert_to_hex(30, 2))
        unused = convert_to_little_endian(convert_to_hex(0, 2))
        sog = convert_to_little_endian(convert_to_hex(int(slope_data) * 1000, 4))

        can_data = lat + lon + secs + mins + hrs + unused + sog
        can_message = "cansend " + can_line + " 070##1" + can_data

        # Execute the cansend command
        stdin, stdout, stderr = client.exec_command(can_message)
        
        # Check for errors
        error = stderr.read().decode().strip()
        output = stdout.read().decode().strip()
        
        if error:
            print(f"ERROR sending command: {error}")
            return False
        else:
            print(f"✓ Sent - CAN message: {can_message}")
            return True
            
    except Exception as e:
        print(f"Exception sending rudder command: {e}")
        return False


def run_local_test(data = None):
    # TODO
    # This should setup and run the Remote debugger
    # take data as an input and feed it into can_dump process with testing = true,
    # this should remove the need to ssh and simplify testing
    print("local tests started running!")
    generate_slope_data()
    return