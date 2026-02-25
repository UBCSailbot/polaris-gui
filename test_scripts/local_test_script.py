"""
Contains test functions 
Automatically SSHes into rpi and sends a CAN Frame simulating external system/data every delay secs
Outputs support messages through terminal

Use Ctrl+C or Space to stop sending
"""

import sys
from time import sleep
from datetime import datetime
import random
import multiprocessing
from PyQt5.QtWidgets import (
    QApplication
)

import project.utility as util
from project.remote_debugger import (
    CANWindow
)



can_line = "can0"

# Time between sent frames (in secs)
delay = 1.05

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

def make_pretty(cmd: str):
    '''
    Helper function for putting cansend commands into the same format as candump received messages\n
    '''
    try:
        frame_id = cmd[13:16]  # TODO: changed from 12 to 13, see if this is a problem
        data = cmd[19:]     # TODO: changed from 18 to 19, see if this is a problem
        data_length = int(len(data) / 2)
        padding = "0" if (data_length < 10) else ""
        data_nice = ""
        for i in range(len(data)):
            data_nice += data[i]
            if ((i % 2) == 1):
                data_nice += " "
        msg = can_line + "  " + frame_id + "  [" + padding + str(data_length) + "]  " + data_nice
        # print("pretty_CAN msg = ", msg)
    except Exception as e:
        print(f"ERROR - Command not logged: {str(e)}")
    
    return msg

def create_can_msg(data, frame) -> str:
    return "cansend " + can_line + " " + frame + "##1" + data

def generate_hb_msg(frame):
    return create_can_msg("", frame)

def generate_gps_msg():
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
        # lat = convert_to_little_endian(convert_to_hex(int((slope_data + 90) * 1000000), 4))
        # lon = convert_to_little_endian(convert_to_hex(int((slope_data + 90) * 1000000), 4))
        lat = convert_to_little_endian(convert_to_hex(int((49.2621 + 90) * 1000000), 4))
        lon = convert_to_little_endian(convert_to_hex(int((-33.2482 + 90) * 1000000), 4)) 
        secs = convert_to_little_endian(convert_to_hex(10, 2))
        mins = convert_to_little_endian(convert_to_hex(20, 2))
        hrs = convert_to_little_endian(convert_to_hex(30, 2))
        unused = convert_to_little_endian(convert_to_hex(0, 2))
        sog = convert_to_little_endian(convert_to_hex(int(slope_data) * 1000, 4))

        can_data = lat + lon + secs + mins + hrs + unused + sog
        can_message = "cansend " + can_line + " 070##1" + can_data
        return can_message
            
    except Exception as e:
        print(f"Exception creating rudder command: {e}")
        return None
    
def generate_ais_msgs(num_msgs):
        # TODO: Send num_msgs can messages (multiple commands) to reflect actual AIS behaviour
        # note: should ais_obj be a subclass of dataobject?

        data_points = [1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
        # data_points.reverse()

        for i in range(num_msgs):
            # x_data = data_points[i % len(data_points)] # prevent errors for too-short array
            # y_data = data_points[len(data_points) - 1 - (i % len(data_points))]
            x_data = random.random() * 75
            y_data = random.random() * 150
            try:

                id = convert_to_little_endian(convert_to_hex(i * 10000000, 4))
                # lat = convert_to_little_endian(convert_to_hex(int((x_data) * 1000000), 4)) # should change by 1
                # lon = convert_to_little_endian(convert_to_hex(int((y_data) * 1000000), 4))
                
                lat_float = (49.2629 + (slope_data * 0.0001) + 90) * 1000000
                lon_float = (100.4489 + (slope_data * 0.0001) + 180) * 1000000
                lat_value = int(lat_float)
                lon_value = int(lon_float)
                # print("lat_float = ", lat_float)
                # print("lon_float = ", lon_float)
                # print("lat = ", lat_value)
                # print("lon = ", lon_value)
                lat = convert_to_little_endian(convert_to_hex(lat_value, 4)) # should be received/logged as 85
                lon = convert_to_little_endian(convert_to_hex(lon_value, 4)) # should received/logged as 120
                # print("lat sent = ", lat)
                # print("lon sent = ", lon)
                sog = 0
                if (i == 3):
                    sog = convert_to_little_endian(convert_to_hex(1023, 2)) # test sog not available 
                else:
                    # sog = convert_to_little_endian(convert_to_hex(35, 2)) # should be received as 3.5
                    sog = convert_to_little_endian(convert_to_hex(0, 2)) # should be received as 0

                cog = 0
                if (i == 0):
                    cog = convert_to_little_endian(convert_to_hex(3600, 2)) # test cog not available
                else:
                    cog = convert_to_little_endian(convert_to_hex(0, 2)) # received as 0
                
                true_heading = 0
                if (i == 0):
                    true_heading = convert_to_little_endian(convert_to_hex(511, 2)) # test true heading not available
                else:
                    # true_heading = convert_to_little_endian(convert_to_hex(359, 2)) # received as 359
                    true_heading = convert_to_little_endian(convert_to_hex(0, 2)) # received as 0

                rot = 0
                if (i == 4):
                    rot = convert_to_little_endian(convert_to_hex(0, 1)) # test rot not available (ROT = -128, sent as ROT + 128)
                else:
                    # rot = convert_to_little_endian(convert_to_hex(-54 + 128, 1)) # received as -54
                    rot = convert_to_little_endian(convert_to_hex(0 + 128, 1)) # received as 0


                ship_len = 0
                if (i == 0):
                    ship_len = convert_to_little_endian(convert_to_hex(0, 2)) # test ship length not available
                else:
                    ship_len = convert_to_little_endian(convert_to_hex(10, 2)) # received as 10

                ship_wid = 0
                if (i == 0):
                    ship_wid = convert_to_little_endian(convert_to_hex(0, 2)) # test ship length not available
                else:
                    ship_wid = convert_to_little_endian(convert_to_hex(30, 2)) # received as 30

                idx = convert_to_little_endian(convert_to_hex(i, 1))

                num_ships = convert_to_little_endian(convert_to_hex(num_msgs, 1))

                can_data = id + lat + lon + sog + cog + true_heading + rot + ship_len + ship_wid + idx + num_ships
                can_message = "cansend " + can_line + " 060##1" + can_data
                return can_message
            
            except Exception as e:
                print(f"ERROR - send_ais_command threw error {e}")

def send_message(client, can_message):
    try:
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
        print(f"ERROR - send_message threw error {e}")

# def init_joystick():
#     # Joystick initialization
#     pygame.init()
#     pygame.joystick.init()

#     if pygame.joystick.get_count() == 0:
#         print("No joystick detected.")
#     try:
#         js = pygame.joystick.Joystick(0)
#         js.init()
#         print(f"Connected to: {js.get_name()}")
#     except Exception as e:
#         js = None
#         print(f"Joystick Connection Error: {e}")

def simple_consumer(queue: multiprocessing.Queue, delay):
    while True:
        try:
            queue.get()
            sleep(delay)
        except KeyboardInterrupt:
            print("simple_consumer() process closed!")
            return
        except Exception as e:
            print(f"ERROR - simple_consumer() threw exception {e}")

def start_remote_debugger(current_time: float, timestamp: str, queue, parent_conn, cmd_queue, response_queue, can_log_queue, joystick = None):
    app = QApplication(sys.argv)
    for obj in util.all_objs:
        obj.initialize(timestamp) # create QWidgets
    for mod in util.heartbeat_modules:
        mod.init_time(current_time)
    window = CANWindow(queue, parent_conn, cmd_queue, response_queue, can_log_queue, timestamp, joystick = joystick)
    window.show()

    print("Remote debugger has been setup!")

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt: # note: Ctrl+C doesn't work due to QT loop taking over
        print("\nKeyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")


def run_local_test(msg_queue: multiprocessing.Queue, delay, data = None):
    '''
    msg_queue is the queue in which to put the data\n
    delay is the delay between messages\n
    data is not yet defined but I'm thinking it could be smth that's just sent?'''
    # TODO
    # This should setup and run the Remote debugger
    # take data as an input and feed it into can_dump process with testing = true,
    # this should remove the need to ssh and simplify testing
    # This repeatedly sends messages at regular intervals: has a while loop which is broken out of by 
    # What I want to figure out is a good way to send different types of data, different commands etc.
        # enable some, disable other messages easily
    
    cycle = 0
    
    while True:
        try:
            cycle += 1
            print(f"--- CYCLE {cycle} ---")

            if ((cycle % 10) == 0): 
                pdb_hb_msg = make_pretty(generate_hb_msg("130"))
                msg_queue.put(pdb_hb_msg)
                print(f"Message: {pdb_hb_msg}")

            ais_msg = make_pretty(generate_ais_msgs(1))
            msg_queue.put(ais_msg)
            print(f"Message: {ais_msg}")

            gps_data = generate_gps_msg()
            msg = make_pretty(gps_data)
            msg_queue.put(msg)  # NOTE: do I need to make this non-blocking or smth?
            print(f"Message: {msg}")

            generate_slope_data()
            sleep(delay)
        except KeyboardInterrupt:
            print("Test stopped by user")
            return
        except Exception as e:
            print(f"ERROR - run_local_test threw error {e}")
            return
    


def main():
    multiprocessing.set_start_method("spawn")

    # Queue initialization
    msg_queue = multiprocessing.Queue()
    dump_queue = multiprocessing.Queue() # here goes all the stuff I don't want to deal with
    empty_queue = multiprocessing.Queue() # here is an empty queue for functions that take input from a queue
    parent_conn, child_conn = multiprocessing.Pipe() # TODO: do I need a simple_pipe_consumer() ? Will there be a problem if I don't connect the child end?

    current_time = datetime.now()
    timestamp = current_time.strftime('%Y%m%d_%H%M%S')
    current_time = current_time.timestamp() # convert to seconds since epoch

    # NOTE: For now, I'll ignore pretty much all 'extra' processes: 
    # - temp_reader (just show disconnected)
    # - can_send_worker (msgs will just go into a queue and not be sent)
    # - can_logging_process (msgs will just go into a queue and not be sent)
    #   - a mock consumer process will remove messages from the above queues
    # Later I may create a simulator for temp reader
    # can_dump will be replaced by run_local_test
    # 

    dump_proc = multiprocessing.Process(target=simple_consumer, args=(dump_queue, delay / 2))
    # TODO 1: I would like to implement a keyboard-press thing that can pause and unpause sending data
    data_proc = multiprocessing.Process(target=run_local_test, args=(msg_queue, delay))

    dump_proc.start()
    data_proc.start()

    # Cleanup (CTRL + C) initialization # TODO: implement later? 
    # signal.signal(signal.SIGINT, key_interrupt_cleanup)

    # TODO: Implement later?
    # init joystick() - ctrl+f to find this commented-out fn

    print("=" * 60)
    print("Local test script - Sets up and passes sample data into an instance of a CANWindow application")
    print("=" * 60)

    start_remote_debugger(current_time, timestamp, msg_queue, parent_conn, dump_queue, empty_queue, dump_queue)

    # TODO: clean up all processes etc. here
    print("Cleaning up...")
    dump_proc.terminate()
    data_proc.terminate()

    dump_proc.join(timeout=2)
    data_proc.join(timeout=2)

    parent_conn.close()
    child_conn.close()

    msg_queue.close()
    dump_queue.close()
    empty_queue.close()

    print("Cleanup complete.")

    print("=" * 60)
    print("local_test_script finished")
    print("=" * 60)

if __name__ == "__main__":
    main()
    
