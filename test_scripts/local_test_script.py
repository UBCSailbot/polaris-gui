"""
Contains test functions 
Automatically SSHes into rpi and sends a CAN Frame simulating external system/data every delay secs
Outputs support messages through terminal

Use Ctrl+C or Space to stop sending

NOTE: (CURRENTLY) THIS SCRIPT MUST BE RUN AS A MODULE USING `python -m test_scripts.local_test_script` from the ROOT directory (polaris-gui)
"""

import sys
from time import sleep
from datetime import datetime
import random
import multiprocessing
from PyQt5.QtWidgets import (
    QApplication
)

# import project.utility as util
# from project.remote_debugger import (
#     CANWindow
# )

# sys.path.append("../src")

# import src.utils as util
import utils as util
from main import (
    CANWindow
)
from widgets import *
# from ..src.utils import all_objs, heartbeat_modules
# from polaris-gui import utils as util
# from src.main import (
#     CANWindow
# )

import math



can_line = "can0"

# Time before starting tests to allow remote debugger to initialize (in secs)
start_delay = 0

# Time between sent frames (in secs)
delay = 0.20

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
    return round(big_endian, 16)

def generate_slope_data():
    global slope
    global slope_data
    if ((slope_data < data_min) or (slope_data > data_max)):
        slope *= -1

    slope_data += slope

def format_as_candump(cmd: str):
    '''
    Helper function for putting cansend commands into the same format as candump received messages\n
    '''
    try:
        frame_id = cmd[13:16]  # TODO: changed from 12 to 13, see if this is a problem
        data = cmd[19:]     # TODO: changed from 18 to 19, see if this is a problem
        data_length = round(len(data) / 2)
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

def generate_gps_msg(lat_val: float = None, lon_val: float = None):
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
        # lat = convert_to_little_endian(convert_to_hex(round((slope_data + 90) * 1000000), 4))
        # lon = convert_to_little_endian(convert_to_hex(round((slope_data + 90) * 1000000), 4))
        lat = 0
        lon = 0
        if (lat_val is not None and lon_val is not None):
            # print(f"lat_val (float) = {lat_val}")
            # print(f"lat (float) = {(lat_val + 90) * 1000000}")
            # print(f"lat (int) = {int((lat_val + 90) * 1000000)}")
            lat = convert_to_little_endian(convert_to_hex(round((lat_val + 90) * 1000000), 4))
            lon = convert_to_little_endian(convert_to_hex(round((lon_val + 180) * 1000000), 4)) 
        else:
            lat = convert_to_little_endian(convert_to_hex(round((49.2621 + 90) * 1000000), 4))
            lon = convert_to_little_endian(convert_to_hex(round((-33.2482 + 180) * 1000000), 4)) 

        secs = convert_to_little_endian(convert_to_hex(10, 2))
        mins = convert_to_little_endian(convert_to_hex(20, 2))
        hrs = convert_to_little_endian(convert_to_hex(30, 2))
        unused = convert_to_little_endian(convert_to_hex(0, 2))
        sog = convert_to_little_endian(convert_to_hex(round(slope_data) * 1000, 4))

        can_data = lat + lon + secs + mins + hrs + unused + sog
        can_message = "cansend " + can_line + " 070##1" + can_data
        return can_message
            
    except Exception as e:
        print(f"Exception creating gps command: {e}")
        return None
    
def generate_ais_msgs(num_msgs, id: int = None, lon: float = None, lat: float = None):
        # TODO: Send num_msgs can messages (multiple commands) to reflect actual AIS behaviour
        # note: should ais_obj be a subclass of dataobject?

        data_points = [1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
        # data_points.reverse()

        for i in range(num_msgs):
            # x_data = data_points[i % len(data_points)] # prevent errors for too-short array
            # y_data = data_points[len(data_points) - 1 - (i % len(data_points))]
            # x_data = random.random() * 75
            # y_data = random.random() * 150
            try:

                # lat = convert_to_little_endian(convert_to_hex(round((x_data) * 1000000), 4)) # should change by 1
                # lon = convert_to_little_endian(convert_to_hex(round((y_data) * 1000000), 4))
                
                if (id is not None and lon is not None and lat is not None):
                    id = convert_to_little_endian(convert_to_hex(id, 4))
                    lat_float = (lat + 90) * 1000000
                    lon_float = (lon + 180) * 1000000 
                else:
                    id = convert_to_little_endian(convert_to_hex(i * 10000000, 4))
                    lat_float = (49.2629 + (slope_data * 0.0001) + 90) * 1000000
                    lon_float = (100.4489 + (slope_data * 0.0001) + 180) * 1000000
                
                lat_value = round(lat_float)
                lon_value = round(lon_float)
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


def generate_rudder_msg(actual_angle, imu_roll, imu_pitch, imu_heading, set_angle, integral, derivative, spd_over_gnd) -> str:
    """Send rudder CAN message via SSH"""
    try:
        # print(f"actual_angle = {convert_to_hex(round((slope_data) * 90.0 * 100), 2)}")
        actual_angle = convert_to_little_endian(convert_to_hex(round((actual_angle + 90) * 100), 2))
        # print(f"imu_roll = {convert_to_hex(round((slope_data + 0.1) * 180 * 100), 2)}")
        imu_roll = convert_to_little_endian(convert_to_hex(round((imu_roll + 180) * 100), 2))
        # print(f"imu_pitch = {convert_to_hex(round((slope_data + - 0.05) * 180 * 100), 2)}")
        imu_pitch = convert_to_little_endian(convert_to_hex(round((imu_pitch + 180) * 100), 2))
        # print(f"imu_heading = {convert_to_hex(round((slope_data) * 360 * 100), 2)}")
        imu_heading = convert_to_little_endian(convert_to_hex(round(imu_heading * 100), 2))
        set_angle = convert_to_little_endian(convert_to_hex(round((set_angle + 90) * 100), 2))
        integral = convert_to_little_endian(convert_to_hex(round(integral), 2))
        derivative = convert_to_little_endian(convert_to_hex(round(derivative), 2))
        spd_over_gnd = convert_to_little_endian(convert_to_hex(round(spd_over_gnd * 1000), 2))
        # print(f"derivative: {int(derivative[2:] + derivative[0:2], 16)}")
        # print(f"spd_over_gnd {int(spd_over_gnd, 16)}")
        can_data = actual_angle + imu_roll + imu_pitch + imu_heading + set_angle + integral + derivative + spd_over_gnd
        can_message = "cansend " + can_line + " 204##1" + can_data

        return can_message

    except Exception as e:
        print(f"Exception creating rudder command: {e}")
        return None
    
def format_data(data: int | float, num_bytes: int) -> str:
    return convert_to_little_endian(convert_to_hex(round(data), num_bytes))

def format_as_can_frame(frame_id: str, data: str) -> str:
    return "cansend " + can_line + " " + frame_id + "##1" + data


def generate_main_heading_msg(heading: int, steering_select_bit: bool, steering_enable_bit: bool) -> str:
    heading_data = ""
    if steering_select_bit:
        heading_data = format_data((heading + 90) * 1000, 4) # Rudder angle
    else: 
        heading_data = format_data(heading * 1000, 4) # Desired heading angle

    status_bit_data = format_data((0x80 & steering_select_bit) | (0x40 & steering_enable_bit), 1)

    return format_as_can_frame("001", heading_data + status_bit_data)

    
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

def get_can_sent_msgs(from_queue: multiprocessing.Queue, to_queue: multiprocessing.Queue): 
    '''Puts messages from the from_queue into the to_queue'''
    print("get_can_sent_msgs() process started!")
    while True:
        try:
            msg = format_as_candump(from_queue.get())
            to_queue.put(msg)
            sleep(delay)
        except KeyboardInterrupt:
            print("get_can_sent_msgs() process closed!")
            return
        except Exception as e:
            print(f"ERROR - get_can_sent_msgs() threw exception {e}")


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

def start_remote_debugger(current_time: float, timestamp: str, queue, parent_conn, cmd_queue, response_queue, can_log_queue):
    app = QApplication(sys.argv)
    for obj in util.all_objs:
        obj.initialize(timestamp) # create QWidgets
    for mod in util.heartbeat_modules:
        mod.init_time(current_time)
    window = CANWindow(queue, parent_conn, cmd_queue, response_queue, can_log_queue, timestamp)
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
    # take data as an input and feed it into can_dump process with testing = true,
    # this should remove the need to ssh and simplify testing
    # This repeatedly sends messages at regular intervals: has a while loop which is broken out of by 
    # What I want to figure out is a good way to send different types of data, different commands etc.
        # enable some, disable other messages easily
    
    cycle = 0
    sleep(start_delay)

    # Jericho Beach coords (Decimal degrees): 49.2722° N, -123.1985° W
    # I expect the data points will be in a straight line path (upwards to the right)
    # I expect the boat to move about a meter per point
    # Single desired heading value pointing upwards to the right (deg)
    # Actual heading fluctuates between directly upwards (North), and directly right (East)
    # NOTE: Degrees for heading values are defined as 0° for North and increasing clockwise
        # NOTE: BE CAREFUL!! Using standard libraries, will likely need to do conversion
    # NOTE: these values will be put into the local_test_script, and visually checked manually
    # lat_test_straight_line = [49.2722, 49.272201, 49.272202, 49.272203, 49.272204, 49.272205, 49.272206, 49.272207, 49.272208, 49.272209]
    num_dp = 300
    lat_ref = 49.2722 
    lon_ref = -123.1985
    lat_test_straight_line = [49.2722 + (i * 0.000001) for i in range(0, num_dp)]
    lon_test_straight_line = [-123.1985 + (i * 0.000001) for i in range(0, num_dp)]
    d_heading_straight_line = [45] * len(lat_test_straight_line) 
    a_heading_straight_line = [0, 90] * (len(lat_test_straight_line) // 2 + 1)
    
    lat_test_sine_path = [lat_ref + (0.001 * math.sin(i * 0.1)) for i in range(0, num_dp)]
    lon_test_sine_path = [lon_ref + (0.00001 * (i * 0.1)) for i in range(0, num_dp)]
    d_heading_sine_path = [90 * math.sin(i) for i in range(0, num_dp)]
    a_heading_sine_path = [90, 90, 90, 45, 45, 45, 90, 90, 90, 135, 135, 135] * num_dp
    
    while True:
        try:
            cycle += 1
            print(f"--- CYCLE {cycle} ---")
            
            # ais_msg = make_pretty(generate_ais_msgs(1, 0, 49.9999, 181.35))
            # msg_queue.put(ais_msg)
            # print(f"Message: {ais_msg}")

            # ais_msg = make_pretty(generate_ais_msgs(1, 1, 49, 179)) # only visible with range >= 2 DD
            # msg_queue.put(ais_msg)
            # print(f"Message: {ais_msg}")

            # ais_msg = make_pretty(generate_ais_msgs(1, 2, 50, 181.5))
            # msg_queue.put(ais_msg)
            # print(f"Message: {ais_msg}")

            # ais_msg = make_pretty(generate_ais_msgs(1, 3, 48.444, 178.75))
            # msg_queue.put(ais_msg)
            # print(f"Message: {ais_msg}")

            # ais_msg = make_pretty(generate_ais_msgs(1, 4, 50.3061, 181.1691))
            # msg_queue.put(ais_msg)
            # print(f"Message: {ais_msg}")

            if (cycle > 0):
                if (num_dp > (cycle - 1)):

                    # ==== IMUHeadingObject Test ====
                    # Testing the graph axis modulo while other functionality should remain unchanged
                    # NOTE: Desired Heading must be tested manually
                    # heading = ((math.sin(cycle) * 100) + 100 - (15 * cycle)) % 360
                    heading = ((math.sin(0.1 * cycle) * 100) + 270) % 360
                    rudder_data = generate_rudder_msg(50, 12, 13, heading, 0, 30001, 29999, 3)
                    msg = format_as_candump(rudder_data)
                    msg_queue.put(msg)
                    print(f"Message: {msg}")

                    # heading = (cycle * -10) % 360
                    heading_data = generate_main_heading_msg(heading + 10, 0, 0)
                    msg = format_as_candump(heading_data)
                    msg_queue.put(msg)
                    print(f"Message: {msg}")
                    
                    # ==== PLRS PATH + Heading Test ====
                    # # rudder_data is pretty random except for the actual heading
                    # rudder_data = generate_rudder_msg(50, 1.1, 1.2, a_heading_sine_path[cycle - 1], 45, 10, 11, 1.5) # TODO: fill in args - most can be just static values
                    # msg = format_as_candump(rudder_data)
                    # msg_queue.put(msg)
                    # print(f"Message: {msg}")
                    # gps_data = generate_gps_msg(lat_test_sine_path[cycle - 1], lon_test_sine_path[cycle - 1])
                    # msg = format_as_candump(gps_data)
                    # msg_queue.put(msg)  # NOTE: do I need to make this non-blocking or smth?
                    # # print(f"Unformatted: {gps_data}")
                    # print(f"Message: {msg}")

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
    send_queue = multiprocessing.Queue() # queue for sent can msgs
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
    # TODO: I would like to implement a keyboard-press thing that can pause and unpause sending data
    data_proc = multiprocessing.Process(target=run_local_test, args=(msg_queue, delay))
    post_sent_msgs_proc = multiprocessing.Process(target=get_can_sent_msgs, args=(send_queue, msg_queue))

    dump_proc.start()
    data_proc.start()
    post_sent_msgs_proc.start()

    # Cleanup (CTRL + C) initialization # TODO: implement later? 
    # signal.signal(signal.SIGINT, key_interrupt_cleanup)

    print("=" * 60)
    print("Local test script - Sets up and passes sample data into an instance of a CANWindow application")
    print("=" * 60)

    start_remote_debugger(current_time, timestamp, msg_queue, parent_conn, send_queue, empty_queue, dump_queue)

    # Clean up all processes etc. here
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
    
