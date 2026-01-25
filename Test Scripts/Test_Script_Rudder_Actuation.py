#!/usr/bin/env python3
"""
Simple Rudder Actuation Test Script
Sweeps rudder from 45 to -45 degrees in 15 degree increments every 30 seconds
No GUI - terminal output only
"""

import paramiko
import time
import random
from datetime import datetime

# SSH Credentials
hostname = "192.168.0.10"
username = "sailbot"
password = "sailbot"

### ----------  Utility Functions ---------- ###
def convert_to_hex(decimal, num_digits):
    return format(decimal, "X").zfill(num_digits)

def convert_to_little_endian(hex_str):
    raw = bytes.fromhex(hex_str)
    return raw[::-1].hex()

def send_rudder_command(client, angle):
    """Send rudder CAN message via SSH"""
    try:
        # Convert angle to CAN message format (same as Remote_Debugger_V3.py)
        # Convert float angle to integer for hex conversion
        angle_int = int((angle + 90) * 1000)
        value = convert_to_hex(angle_int, 8)
        can_message = "cansend can1 001##1" + convert_to_little_endian(value) + "80"
        
        # Execute the command
        stdin, stdout, stderr = client.exec_command(can_message)
        
        # Check for errors
        error = stderr.read().decode().strip()
        output = stdout.read().decode().strip()
        
        if error:
            print(f"ERROR sending rudder command: {error}")
            return False
        else:
            print(f"✓ Rudder set to {angle:7.3f}° - CAN message: {can_message}")
            return True
            
    except Exception as e:
        print(f"Exception sending rudder command: {e}")
        return False

def main():
    print("=" * 60)
    print("RUDDER ACTUATION TEST SCRIPT")
    print("=" * 60)
    print(f"Target: {hostname}")
    print(f"Username: {username}")
    print("Rudder sweep: Random angles between -45° and +45° every 30 seconds")
    print("Angle precision: 3 decimal places")
    print("=" * 60)
    
    # Connect to SSH
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Connecting to SSH...")
        client.connect(hostname, username=username, password=password)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] SSH connection established!")
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting rudder sweep...")
        print("Press Ctrl+C to stop the test\n")
        
        cycle_count = 0
        start_time = time.time()
        
        while True:
            cycle_count += 1
            print(f"--- CYCLE {cycle_count} ---")
            
            # Generate random angle between -45 and +45 degrees with 3 decimal places
            angle = round(random.uniform(-45.0, 45.0), 3)
            
            current_time = time.time()
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Calculate total elapsed time
            total_elapsed = current_time - start_time
            print(f"[{timestamp}] Total elapsed time: {total_elapsed:.1f}s")
            
            print(f"[{timestamp}] ", end="")
            success = send_rudder_command(client, angle)
            
            if not success:
                print("Failed to send command, continuing...")
            
            print(f"[{timestamp}] Waiting 30 seconds before next angle...")
            time.sleep(30)  # Wait 30 seconds before next angle
    
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
        print("RUDDER ACTUATION TEST COMPLETED")
        print("=" * 60)

if __name__ == "__main__":
    main()
