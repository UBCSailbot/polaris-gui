"""
Simple CAN Frame send Test Script for Temperature/Voltage data
Automatically SSHes into rpi and sends a CAN Frame simulating PDB every delay secs
Outputs support messages through terminal

Use Ctrl+C to stop the test
"""

import paramiko
import time
import random
from datetime import datetime

# SSH Credentials
hostname = "192.168.0.10"
username = "sailbot"
password = "sailbot"

can_line = "can0"

# Time between sent frames (in secs)
delay = 1

# CAN Frame IDs
temp_sensor_id = "100" # 0x10X
pH_id = "110" # 0x11X
sal_id = "120" # 0x12X

# Hex Two's complement conversion dict
hex_conversion = {
    "0": "f",
    "1": "e",
    "2": "d",
    "3": "c",
    "4": "b",
    "5": "a",
    "6": "9",
    "7": "8",
    "8": "7",
    "9": "6",
    "a": "5",
    "b": "4",
    "c": "3",
    "d": "2",
    "e": "1",
    "f": "0",
}

negative_hex_starting_digits = ["8", "9", "a", "b", "c", "d", "e", "f"]

slope = -0.1
data_min = 0.2
data_max = 0.95
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
    slope_data = round(slope_data, 2)

    # return slope_data
    

def send_pdb_command(client):
    try:
        # Send sample pdb command with data: 
        # volt1: 3 volt2: 2.4 volt3: 0.8 volt4: 1.3 temp1: 1.5 temp2: 57.8 temp3: 126.32
        # Convert data to CAN format (each is a 2-byte hex number in little endian)
        # Multiplied by 1000 by CAN Frame documentation
        # can_data = 0x5dc0 0096 1f40 e1c8 3158 7530
                    # pH_data = round(slope_data * 15)

        # designed so that volt1 < volt2 < volt3 < volt4 and temp1 < temp2 < temp3 for easy debugging
        volt1 = convert_to_little_endian(convert_to_hex(int((slope_data - 0.05) * 3.8 * 10000), 2))
        volt2 = convert_to_little_endian(convert_to_hex(int((slope_data * 3.8) * 10000), 2))
        volt3 = convert_to_little_endian(convert_to_hex(int((slope_data + 0.1) * 4.0 * 10000), 2))
        volt4 = convert_to_little_endian(convert_to_hex(int((slope_data + 0.2) * 3.8 * 10000), 2))

        print(f"temp1 = {convert_to_hex(int((slope_data - 0.05) * 127.0) * 100, 2)}")
        temp1 = convert_to_little_endian(convert_to_hex(int((slope_data - 0.05) * 127.0) * 100, 2))
        temp2 = convert_to_little_endian(convert_to_hex(int((slope_data) * 127.0) * 100, 2))

        # print(f"temp2 = {convert_to_hex(int((slope_data) * 127.0) * 1000, 2)}")
        temp3 = convert_to_little_endian(convert_to_hex(int((slope_data + 0.15) * 130.0) * 100, 2))
        curr_hp = convert_to_little_endian(convert_to_hex(round((slope_data - 0.05) * 25)* 1000, 2))
        curr_hs = convert_to_little_endian(convert_to_hex(round((slope_data) * 25)* 1000, 2))
        curr_sp = convert_to_little_endian(convert_to_hex(round((slope_data + 0.1) * 25)* 1000, 2))
        curr_ss = convert_to_little_endian(convert_to_hex(round((slope_data + 0.2) * 25)* 1000, 2))

        can_data = volt2  + temp1 + volt3 + temp2 + temp3 + volt4 + volt1 + curr_hp + curr_hs + curr_sp + curr_ss
        # can_data = "c05d9600401fc9416075c8325831"
        can_msg = "cansend " + can_line + " 206##1" + can_data

        # Execute the cansend command
        stdin, stdout, stderr = client.exec_command(can_msg)
        
        # Check for errors
        error = stderr.read().decode().strip()
        output = stdout.read().decode().strip()

        if error:
            print(f"ERROR sending command: {error}")
            return False
        else:
            print(f"✓ Sample PDB msg sent: {can_msg}")
            return True

    except Exception as e:
        print(f"Error sending cansend command: {e}")
        return False
    pass

# Use this function to CAN send a frame for any data sensor
def send_sensor_command(client, frame_id, data: float):
    global pH_id
    global temp_sensor_id
    global sal_id
    try:
        # Convert data to CAN format (2-byte hex number in little endian)
        # Multiplied by 1000 by CAN Frame documentation
        # print(f"Data passed to send_sensor_command: {data}")
        can_data = int(data * 1000)
        # print("data converted to int, * 1000: ", can_data)
        numBytes = 0
        if (frame_id == pH_id): numBytes = 2
        elif (frame_id == temp_sensor_id): numBytes = 3
        elif (frame_id == sal_id): numBytes = 4
        else: print(f"[ERROR] send_sensor_command(): frame_id not recognized")
        hexed_data = convert_to_hex(can_data, numBytes)
        # print("data converted to hex: ", hexed_data)
        hex_bytes = convert_to_little_endian(hexed_data)
        print("hex_bytes: ", hex_bytes)
        can_msg = "cansend " + can_line + " " + frame_id + "##1" + hex_bytes

        # Execute the cansend command
        stdin, stdout, stderr = client.exec_command(can_msg)
        
        # Check for errors
        error = stderr.read().decode().strip()
        output = stdout.read().decode().strip()

        if error:
            print(f"ERROR sending command: {error}")
            return False
        else:
            sent = convert_from_little_endian_str(hex_bytes) / 1000
            print(f"✓ Sent: {sent} - CAN message: {can_msg}")
            return True
        
    except Exception as e:
        print(f"Error sending cansend command: {e}")
        print(f"Attempted command: {can_msg}")
        return False

def send_rudder_command(client):
    """Send rudder CAN message via SSH"""
    try:
        # print(f"actual_angle = {convert_to_hex(int((slope_data) * 90.0 * 100), 2)}")
        actual_angle = convert_to_little_endian(convert_to_hex(int(((slope_data - 0.45) * 90 + 90) * 100), 2))
        # print(f"imu_roll = {convert_to_hex(int((slope_data + 0.1) * 180 * 100), 2)}")
        imu_roll = convert_to_little_endian(convert_to_hex(int((slope_data + 0.1) * 180 * 100), 2))
        # print(f"imu_pitch = {convert_to_hex(int((slope_data + - 0.05) * 180 * 100), 2)}")
        imu_pitch = convert_to_little_endian(convert_to_hex(int((slope_data - 0.05) * 180 * 100), 2))
        # print(f"imu_heading = {convert_to_hex(int((slope_data) * 360 * 100), 2)}")
        imu_heading = convert_to_little_endian(convert_to_hex(int((slope_data) * 360 * 100), 2))
        set_angle = convert_to_little_endian(convert_to_hex(int(((slope_data - 0.50) * 90 + 90) * 100), 2))
        integral = convert_to_little_endian(convert_to_hex(int((slope_data) * 100 + 30000), 2))
        derivative = convert_to_little_endian(convert_to_hex(int((slope_data) * 10000) + 600, 2))
        spd_over_gnd = convert_to_little_endian(convert_to_hex(int((slope_data) * 30 * 1000), 2))
        print(f"derivative: {int(derivative[2:] + derivative[0:2], 16)}")
        # print(f"spd_over_gnd {int(spd_over_gnd, 16)}")
        can_data = actual_angle + imu_roll + imu_pitch + imu_heading + set_angle + integral + derivative + spd_over_gnd
        can_message = "cansend " + can_line + " 204##1" + can_data
        
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
    
def send_data_wind_command(client):
    """Send wind sensor CAN message via SSH"""
    try:
        # print(f"actual_angle = {convert_to_hex(int((slope_data) * 90.0 * 100), 2)}")
        wind_dir = convert_to_little_endian(convert_to_hex(int((slope_data) * 360), 2))
        # print(f"imu_roll = {convert_to_hex(int((slope_data + 0.1) * 180 * 100), 2)}")
        wind_speed = convert_to_little_endian(convert_to_hex(int((slope_data) * 30 * 10), 2))

        can_data = wind_dir + wind_speed
        can_message = "cansend " + can_line + " 041##1" + can_data
        
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
        print(f"Exception sending wind sensor command: {e}")
        return False

def main():
    print("=" * 60)
    print("Debug CAN Frame TEST SCRIPT")
    print("=" * 60)
    print(f"Target: {hostname}")
    print(f"Username: {username}")
    print(f"Sends CAN Frame with debug data every {delay} secs")
    print("=" * 60)
    
    # Connect to SSH
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Connecting to SSH...")
        client.connect(hostname, username=username, password=password)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] SSH connection established!")
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting test...")
        print("Press Ctrl+C to stop the test\n")
        
        cycle_count = 0
        start_time = time.time()

        # current_pH = round(slope_data * 14)
        # current_water_temp = round(slope_data * 130, 3)
        # current_sal = round(slope_data * 80000)

        # send_pdb_command(client)
        # time.sleep(delay)
        # send_pdb_command(client)
        # time.sleep(delay)
        
        while True:
            cycle_count += 1
            print(f"--- CYCLE {cycle_count} ---")
            
            generate_slope_data()

            current_time = time.time()
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Calculate total elapsed time
            total_elapsed = current_time - start_time
            print(f"[{timestamp}] Total elapsed time: {total_elapsed:.1f}s")
        
            # success = send_pdb_command(client)
            # time.sleep(delay)
            # success = send_rudder_command(client)

            pH_data = round(slope_data * 15)
            temp_sensor_data = round((slope_data * 1100.0) + 273.15, 3)
            sal_data = round(slope_data * 575000, 3)

            print(f"generated pH_data = {pH_data}")
            success = send_sensor_command(client, pH_id, pH_data)
            if not success:
                print("Failed to send command, continuing...")

            print(f"generated temp_sensor_data = {temp_sensor_data}")
            success = send_sensor_command(client, temp_sensor_id, temp_sensor_data)
            if not success:
                print("Failed to send command, continuing...")

            print(f"generated sal_data = {sal_data}")
            success = send_sensor_command(client, sal_id, sal_data)
            if not success:
                print("Failed to send command, continuing...")

            time.sleep(delay)
            success = send_data_wind_command(client)
            # # time.sleep(delay)
            if not success:
                print("Failed to send command, continuing...")

            
            print(f"[{timestamp}] Waiting {delay} seconds before next cansend...")
            time.sleep(delay)  # Wait 30 seconds before next angle
    
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Test stopped by user (Ctrl+C)")
    
    except paramiko.AuthenticationException:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] SSH Authentication failed!")
        print("Check username/password credentials")
    
    except paramiko.SSHException as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] SSH connection error: {e}")
    
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Unexpected error: {e}")
    
    finally:
        client.close()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] SSH connection closed")
        print("=" * 60)
        print("PDB DEBUG DATA CANSEND TEST COMPLETED")
        print("=" * 60)

if __name__ == "__main__":
    main()
