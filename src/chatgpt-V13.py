import sys
import paramiko
import multiprocessing
import time
import csv
import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QTextEdit, QHBoxLayout, QCheckBox, QGridLayout, QScrollArea,
    QSizePolicy
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from DataObject import *

# SSH Credentials
hostname = "192.168.0.10"
username = "sailbot"
password = "sailbot"

can_line = "can0"

timestamp = 0  # global; runtime timestamp is created in __main__

value_label_min_width = 100
value_label_max_height = 40

value_style = """
            color: black;
            font-size: 16px;
            font-weight: bold;
            font-family: 'Courier New', monospace;
            padding: 1px;
            background-color: #f0f0f0;
            border: 2px solid #cccccc;
            border-radius: 3px;
            margin: 2px;
        """
bold_text = "font-weight: bold;"

linewidth = 2
graph_xlabel = "Time (s)"  # all graphs read in seconds
graph_min_width = 275
graph_min_height = 250
scroll_window = 60  # in seconds

### ----------  Utility Functions ---------- ###
def convert_to_hex(decimal, num_bytes):
    return format(decimal, "X").zfill(2 * num_bytes)

def convert_to_little_endian(hex_str):
    raw = bytes.fromhex(hex_str)
    return raw[::-1].hex()

def convert_from_little_endian_str(hex_str):
    raw = bytes.fromhex(hex_str)
    big_endian = raw[::-1].hex()
    return int(big_endian, 16)

### ---------- Creating UI Objects ---------- ###
def create_label(title, min_width=value_label_min_width, max_height=value_label_max_height):
    label = QLabel(title)
    label.setMinimumWidth(min_width)
    label.setMaximumHeight(max_height)
    label.setAlignment(Qt.AlignLeft)
    label.setStyleSheet(value_style)
    return label

def create_graph(title, ylabel, ymin, ymax):
    """
    Used for creating graphs - does not create lines
    ymin : initial minimum graph y-value
    ymax : initial maximum graph y-value
    """
    figure = Figure(figsize=(8, 4), tight_layout=True)
    canvas = FigureCanvas(figure)
    canvas.setMinimumSize(graph_min_width, graph_min_height)
    ax = figure.add_subplot(111)
    ax.set_title(title)
    ax.set_xlabel(graph_xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(0, 60)  # Initial X range is 0-60 secs
    ax.set_ylim(ymin, ymax)  # Initial ymin and ymax
    ax.grid(True, alpha=0.3)
    return (figure, canvas, ax)

### ----------  Parsing Data Frames  ---------- ###

def parse_0x206_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 16:
        raise ValueError("Incorrect data length (num bytes): ID 0x206")

    val = lambda s, e, div: int.from_bytes(raw_bytes[s:e], 'little') / div
    return {
        volt2_obj.name: val(0, 2, 1000.0),
        temp1_obj.name: val(2, 4, 100.0),
        volt3_obj.name: val(4, 6, 1000.0),
        temp2_obj.name: val(6, 8, 100.0),
        temp3_obj.name: val(8, 10, 100.0),
        volt4_obj.name: val(10, 12, 1000.0),
        volt1_obj.name: val(12, 14, 1000.0)
    }

def parse_0x204_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 16:
        raise ValueError("Incorrect data length (num bytes): ID 0x204")
    
    val = lambda s, e, div: int.from_bytes(raw_bytes[s:e], 'little') / div
    return {
        actual_rudder_obj.name: val(0, 2, 100.0) - 90,
        imu_roll_obj.name: val(2, 4, 100.0) - 180,
        imu_pitch_obj.name: val(4, 6, 100.0) - 180,
        imu_heading_obj.name: val(6, 8, 100.0),
        set_rudder_obj.name: val(8, 10, 100.0) - 90,
        integral_obj.name: val(10, 12, 1.0) - 30000,
        derivative_obj.name: val(12, 14, 100.0) - 300
    }

def actual_rudder_parsing_fn(parsed_dict):
    return parsed_dict[actual_rudder_obj.name]

def set_rudder_parsing_fn(parsed_dict):
    return parsed_dict[set_rudder_obj.name]

def parse_0x041_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 4:
        raise ValueError("Incorrect data length (num bytes): ID 0x041")
    
    val = lambda s, e, div: int.from_bytes(raw_bytes[s:e], 'little') / div
    return {
        data_wind_dir_obj.name: val(0, 2, 1.0),
        data_wind_spd_obj.name: val(2, 4, 10.0)
    }

# Salinity data frame
def parse_0x12X_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 4:
        raise ValueError("Incorrect data length (num bytes): ID 0x12X")
    
    raw = convert_from_little_endian_str(data_hex)
    actual = raw / 1000

    if (actual < 1 and actual != 0) or (actual > 550000):
        print(f"[ERROR]: sal data parsed as {actual}")    
        print(f"data_hex = {data_hex}")
        print(f"raw = {raw}")
        raise ValueError()
    
    if actual < 100:
        actual = round(actual, 2)
    elif actual < 1000:
        actual = round(actual, 1)
    elif actual < 10000:
        actual = round(actual)
    elif actual < 100000:
        actual = round(actual, -1)
    return {"sal": actual} 

def sal_parsing_fn(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 4:
        raise ValueError("Incorrect data length (num bytes): ID 0x12X")
    
    raw = convert_from_little_endian_str(data_hex)
    actual = raw / 1000

    if (actual < 1 and actual != 0) or (actual > 550000):
        print(f"[ERROR]: sal data parsed as {actual}")    
        print(f"data_hex = {data_hex}")
        print(f"raw = {raw}")
        raise ValueError()
    
    if actual < 100:
        actual = round(actual, 2)
    elif actual < 1000:
        actual = round(actual, 1)
    elif actual < 10000:
        actual = round(actual)
    elif actual < 100000:
        actual = round(actual, -1)
    return actual

# pH data frame
def parse_0x11X_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 2:
        raise ValueError(
            f"Incorrect data length (num bytes): ID 0x11X\nExpecting: 2 bytes, Received: {len(raw_bytes)}"
        )
    
    raw = convert_from_little_endian_str(data_hex)
    actual = raw / 1000

    if (actual < 1 and actual != 0) or (actual > 14):
        print(f"[ERROR]: pH data parsed as {actual}")  
        print(f"data_hex = {data_hex}")
        print(f"raw = {raw}")
        raise ValueError()  
    
    return {"pH": round(actual, 2)}

def pH_parsing_fn(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 2:
        raise ValueError(
            f"Incorrect data length (num bytes): ID 0x11X\nExpecting: 2 bytes, Received: {len(raw_bytes)}"
        )
    
    raw = convert_from_little_endian_str(data_hex)
    actual = raw / 1000

    if (actual < 1 and actual != 0) or (actual > 14):
        print(f"[ERROR]: pH data parsed as {actual}")  
        print(f"data_hex = {data_hex}")
        print(f"raw = {raw}")
        raise ValueError()  
    
    return round(actual, pH_obj.rounding)

# temp data frame
def parse_0x10X_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 3:
        raise ValueError("Incorrect data length (num bytes): ID 0x10X")

    raw = convert_from_little_endian_str(data_hex)
    actual = (raw / 1000.0) - 273.15

    if (actual < -130 and actual != 0) or (actual > 1350):
        print(f"[ERROR]: temp_sensor data parsed as {actual}")  
        print(f"data_hex = {data_hex}")
        print(f"raw = {raw}")
        raise ValueError()  
    
    return {"temp_sensor": round(actual, 3)}

def temp_sensor_parsing_fn(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 3:
        raise ValueError("Incorrect data length (num bytes): ID 0x10X")
    
    raw = convert_from_little_endian_str(data_hex)
    actual = (raw / 1000.0) - 273.15

    if (actual < -130 and actual != 0) or (actual > 1350):
        print(f"[ERROR]: temp_sensor data parsed as {actual}")  
        print(f"data_hex = {data_hex}")
        print(f"raw = {raw}")
        raise ValueError()  
    
    return round(actual, temp_sensor_obj.rounding)

def make_pretty(cmd):
    """
    Helper function for putting cansend commands into the same format as candump received messages
    """
    try:
        frame_id = cmd[12:15]
        data = cmd[18:]
        data_length = int(len(data) / 2)
        padding = "0" if (data_length < 10) else ""
        data_nice = ""
        for i in range(len(data)):
            data_nice += data[i]
            if (i % 2) == 1:
                data_nice += " "
        msg = can_line + "  " + frame_id + "  [" + padding + str(data_length) + "]  " + data_nice
        return msg
    except Exception as e:
        print(f"ERROR - Command not logged: {str(e)}")
        return cmd

### ---------- Data Objects ---------- ###
pH_graph = create_graph("pH vs Time", "pH", 0, 15)
pH_line, = pH_graph[2].plot([], [], 'r-', linewidth=linewidth, label='Current pH')
pH_graph_obj = GraphObject(pH_graph, 0, 14)
pH_label = create_label("pH: ---- ")
pH_obj = DataObject("pH", 1, "", pH_parsing_fn, pH_graph_obj, pH_line, pH_label)

temp_sensor_graph = create_graph("Water Temp vs Time", "Temp (°C)", 0, 100)
temp_sensor_line, = temp_sensor_graph[2].plot([], [], 'b-', linewidth=linewidth, label="Water Temp")
temp_sensor_graph_obj = GraphObject(temp_sensor_graph, 0, 1400)
temp_sensor_label = create_label("Water temp: ----   ")
temp_sensor_obj = DataObject("Water_Temp", 3, "°C", temp_sensor_parsing_fn, temp_sensor_graph_obj, temp_sensor_line, temp_sensor_label)

sal_graph = create_graph("Salinity vs Time", "Salinity (µS/cm)", 0, 100000)
sal_line, = sal_graph[2].plot([], [], 'g-', linewidth=linewidth, label="Salinity")
sal_graph_obj = GraphObject(sal_graph, 0, 550000)
sal_label = create_label("Salinity: ----    ")
sal_obj = DataObject("Salinity", 3, "µS/cm", sal_parsing_fn, sal_graph_obj, sal_line, sal_label)

data_objs = [pH_obj, temp_sensor_obj, sal_obj]

pdb_temp_graph = create_graph("Battery Temperatures vs Time", "Temp (°C)", 0, 100)
temp1_line, = pdb_temp_graph[2].plot([], [], 'r-', label='Temp 1')
temp2_line, = pdb_temp_graph[2].plot([], [], 'g-', label='Temp 2')
temp3_line, = pdb_temp_graph[2].plot([], [], 'y-', label='Temp 3')
pdb_temp_graph_obj = GraphObject(pdb_temp_graph, 0, 127.0)
temp1_label = create_label("Temp1: ----  ")
temp2_label = create_label("Temp2: ----  ")
temp3_label = create_label("Temp3: ----  ")
temp1_obj = DataObject("Temp1", 2, "°C", None, pdb_temp_graph_obj, temp1_line, temp1_label)
temp2_obj = DataObject("Temp2", 2, "°C", None, None, temp2_line, temp2_label)
temp3_obj = DataObject("Temp3", 2, "°C", None, None, temp3_line, temp3_label)

pdb_volt_graph = create_graph("Cell Voltages vs Time", "Voltage (V)", 0, 5)
volt1_line, = pdb_volt_graph[2].plot([], [], 'b-', label='Volt 1')
volt2_line, = pdb_volt_graph[2].plot([], [], 'c-', label='Volt 2')
volt3_line, = pdb_volt_graph[2].plot([], [], 'm-', label='Volt 3')
volt4_line, = pdb_volt_graph[2].plot([], [], 'orange', label='Volt 4')
pdb_volt_graph_obj = GraphObject(pdb_volt_graph, 0, 3.5)
volt1_label = create_label("Volt1: --- ")
volt2_label = create_label("Volt2: --- ")
volt3_label = create_label("Volt3: --- ")
volt4_label = create_label("Volt4: --- ")
volt1_obj = DataObject("Volt1", 2, "V", None, pdb_volt_graph_obj, volt1_line, volt1_label)
volt2_obj = DataObject("Volt2", 2, "V", None, None, volt2_line, volt2_label)
volt3_obj = DataObject("Volt3", 2, "V", None, None, volt3_line, volt3_label)
volt4_obj = DataObject("Volt4", 2, "V", None, None, volt4_line, volt4_label)

pdb_objs = [temp1_obj, temp2_obj, temp3_obj, volt1_obj, volt2_obj, volt3_obj, volt4_obj]

rudder_graph = create_graph("Rudder Angles vs Time", "degrees (°)", -50, 50)
actual_rudder_line, = rudder_graph[2].plot([], [], 'r-', linewidth=2, label='Actual Rudder Angle')
set_rudder_line, = rudder_graph[2].plot([], [], 'b--', linewidth=2, label='Commanded Rudder Angle')
rudder_graph_obj = GraphObject(rudder_graph, -90, 90)
actual_rudder_label = create_label("Actual_rdr_deg: ---- ")
set_rudder_label = create_label("Set_rdr_deg: ---- ")
actual_rudder_obj = DataObject("Actual_rdr_deg", 2, "°", actual_rudder_parsing_fn, rudder_graph_obj, line=actual_rudder_line, label=actual_rudder_label)
set_rudder_obj = DataObject("Set_rdr_deg", 2, "°", set_rudder_parsing_fn, line=set_rudder_line, label=set_rudder_label)

headings_graph = create_graph("IMU & Desired Headings vs Time", "degrees (°)", 0, 360)
imu_heading_line, = headings_graph[2].plot([], [], 'r-', linewidth=2, label="IMU heading")
desired_heading_line, = headings_graph[2].plot([], [], 'b--', linewidth=2, label="Desired heading")
imu_heading_label = create_label("IMU_heading: ---- ")
imu_heading_graph_obj = GraphObject(headings_graph, 0, 360)
imu_heading_obj = DataObject("IMU_heading", 3, "°", None, imu_heading_graph_obj, imu_heading_line, imu_heading_label)

desired_heading_label = create_label("Desired_heading: ---- ")
desired_heading_obj = DataObject("Desired_heading", 3, "°", None, None, desired_heading_line, desired_heading_label)

imu_roll_pitch_graph = create_graph("IMU Roll & Pitch vs Time", "degrees (°)", 0, 360)
imu_roll_line, = imu_roll_pitch_graph[2].plot([], [], 'g-', linewidth=2, label="IMU Roll")
imu_pitch_line, = imu_roll_pitch_graph[2].plot([], [], 'brown', linewidth=2, label="IMU Pitch")
imu_roll_pitch_graph_obj = GraphObject(imu_roll_pitch_graph, 0, 360)
imu_roll_label = create_label("IMU_roll: ---- ")
imu_pitch_label = create_label("IMU_pitch: ---- ")
imu_roll_obj = DataObject("IMU_roll", 2, "°", None, imu_roll_pitch_graph_obj, imu_roll_line, imu_roll_label)
imu_pitch_obj = DataObject("IMU_pitch", 2, "°", None, None, imu_pitch_line, imu_pitch_label)

int_der_graph = create_graph("IMU Integral & Derivative vs Time", "", 0, 100)
der_line, = int_der_graph[2].plot([], [], 'mediumseagreen', linewidth=2, label="Derivative")
int_line, = int_der_graph[2].plot([], [], 'm--', linewidth=2, label="Integral")
int_der_graph_obj = GraphObject(int_der_graph, 0, 360)
int_label = create_label("IMU_integral: ---- ")
der_label = create_label("IMU_derivative: ---- ")
integral_obj = DataObject("IMU_integral", 2, "", None, int_der_graph_obj, int_line, int_label)
derivative_obj = DataObject("IMU_derivative", 2, "", None, None, der_line, der_label)

data_wind_spd_graph = create_graph("Data_Wind Speed vs Time", "Speed (knots)", 0, 20)
data_wind_spd_line, = data_wind_spd_graph[2].plot([], [], 'purple', linewidth=2, label="Wind Speed")
data_wind_spd_graph_obj = GraphObject(data_wind_spd_graph, 0, 360)
data_wind_spd_label = create_label("Data_wind_spd: ---- ")
data_wind_spd_obj = DataObject("Data_wind_spd", 0, "knots", None, data_wind_spd_graph_obj, data_wind_spd_line, data_wind_spd_label)

data_wind_dir_graph = create_graph("Data_Wind Direction vs Time", "degrees (°)", 0, 360)
data_wind_dir_line, = data_wind_dir_graph[2].plot([], [], 'orange', linewidth=2, label="Wind Direction")
data_wind_dir_graph_obj = GraphObject(data_wind_dir_graph, 0, 360)
data_wind_dir_label = create_label("Data_wind_dir: ---- ")
data_wind_dir_obj = DataObject("Data_wind_dir", 0, "°", None, data_wind_dir_graph_obj, data_wind_dir_line, data_wind_dir_label)

data_wind_objs = [data_wind_spd_obj, data_wind_dir_obj]

rudder_objs = [actual_rudder_obj, set_rudder_obj, imu_roll_obj, imu_pitch_obj,
               integral_obj, derivative_obj, imu_heading_obj]

all_objs = pdb_objs + rudder_objs + [desired_heading_obj] + data_wind_objs
# TODO: add data_objs back when pH/sal/temp frames are wired up

### ----------  Background CAN Dump Process ---------- ###
def candump_process(gui_queue: multiprocessing.Queue, log_queue: multiprocessing.Queue):
    """
    Efficient reader: blocks on recv(), streams candump,
    and pushes every complete line to both GUI and log queues.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname, username=username, password=password)
        transport = client.get_transport()
        session = transport.open_session()
        session.exec_command(f"candump {can_line}")

        buffer = ""
        while True:
            data = session.recv(4096)
            if not data:
                break
            buffer += data.decode(errors="ignore")
            lines = buffer.split("\n")
            buffer = lines[-1]  # last may be partial
            for l in lines[:-1]:
                line = l.strip()
                if not line:
                    continue
                # No dropping: blocking puts
                gui_queue.put(line)
                log_queue.put(line)

        # flush remainder
        buffer = buffer.strip()
        if buffer:
            gui_queue.put(buffer)
            log_queue.put(buffer)

    except Exception as e:
        err = f"[ERROR] {str(e)}"
        try:
            gui_queue.put(err)
            log_queue.put(err)
        except Exception:
            pass
    finally:
        client.close()

### ---------- Background Temp Reader Process ---------- ###
def temperature_reader(pipe):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname, username=username, password=password)
        while True:
            try:
                stdin, stdout, stderr = client.exec_command("cat /sys/class/thermal/thermal_zone0/temp")
                raw = stdout.read().decode().strip()
                if raw:
                    temp = float(raw) / 1000
                    pipe.send((True, f"{temp:.1f}°C"))
                else:
                    pipe.send((False, "ERROR"))
            except Exception:
                pipe.send((False, "ERROR"))
            time.sleep(1)
    except Exception:
        while True:
            pipe.send((False, "DISCONNECTED"))
            time.sleep(1)
    finally:
        client.close()

### ---------- Background CAN Send Worker ---------- ###
def cansend_worker(cmd_queue: multiprocessing.Queue, response_queue: multiprocessing.Queue,
                   can_log_queue: multiprocessing.Queue):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname, username=username, password=password)
        while True:
            cmd = cmd_queue.get()
            if cmd == "__EXIT__":
                break
            try:
                stdin, stdout, stderr = client.exec_command(cmd)
                out = stdout.read().decode()
                err = stderr.read().decode()
                response_queue.put((cmd, out, err))
                if not err:
                    # Never drop command logs: blocking put
                    can_log_queue.put(make_pretty(cmd))
                else:
                    raise Exception(f"Command not logged: {cmd}")
            except Exception as e:
                response_queue.put((cmd, "", f"Exec error: {str(e)}"))
    except Exception as e:
        response_queue.put(("ERROR", "", f"SSH error: {str(e)}"))
    finally:
        client.close()

### ---------- Background CAN Logging Process ---------- ###
def can_logging_process(log_queue: multiprocessing.Queue, timestamp: str):
    """
    Dedicated process for logging CAN messages without blocking graphics.
    Uses blocking .get() so no messages are ever dropped.
    """
    try:
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        candump_log_file = os.path.join('logs', f'candump_{timestamp}.csv')
        
        with open(candump_log_file, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['Timestamp', 'Elapsed_Time_s', 'CAN_Message'])
            csv_file.flush()
            
            start_time = time.time()
            print(f"CAN Logging started: {candump_log_file}")
            
            while True:
                message = log_queue.get()
                if message == "__EXIT__":
                    break
                now = datetime.now().isoformat()
                elapsed_time = time.time() - start_time
                writer.writerow([now, f'{elapsed_time:.3f}', message])
                csv_file.flush()
                    
    except Exception as e:
        print(f"Failed to initialize CAN logging: {e}")
    
    print("CAN logging process terminated")

### ----------  PyQt5 GUI ---------- ###
class CANWindow(QWidget):
    def __init__(self, queue, temp_pipe, cmd_queue, response_queue,
                 can_log_queue, run_timestamp: str):
        super().__init__()
        self.queue = queue
        self.temp_pipe = temp_pipe
        self.cansend_queue = cmd_queue
        self.cansend_response_queue = response_queue
        self.can_log_queue = can_log_queue
        self.run_timestamp = run_timestamp

        self.rudder_angle = 0  # degrees
        self.trimtab_angle = 0  # degrees
        self.last_temp_update = time.time()  # Track last temperature update

        self.setWindowTitle("Remote Node GUI - POLARIS")
        self.setGeometry(50, 30, 1300, 450)
        self.setFocusPolicy(Qt.StrongFocus)

        self.time_start = time.time()
        self.time_history = []

        self.init_ui()

        # Fast, but not insane
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(100)  # ms

    def init_ui(self):
        # === Top Bar ===
        self.logo_label = QLabel()
        pixmap = QPixmap("logo.png")
        pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo_label.setPixmap(pixmap)

        self.temp_label = QLabel("RPI Temp: --")
        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setStyleSheet("color: red")

        top_bar_layout = QHBoxLayout()
        top_bar_layout.addWidget(self.logo_label)
        top_bar_layout.addSpacing(10)
        top_bar_layout.addWidget(self.temp_label)
        top_bar_layout.addSpacing(10)
        top_bar_layout.addWidget(self.status_label)
        top_bar_layout.addStretch()

        # === Left Panel ===
        small_spacing = 2
        self.manual_steer_checkbox = QCheckBox("Manual Steering")
        self.manual_steer_checkbox.toggled.connect(self.set_manual_steer)
        self.keyboard_checkbox = QCheckBox("Keyboard Mode")
        self.keyboard_checkbox.toggled.connect(self.toggle_keyboard_mode)

        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(self.manual_steer_checkbox)
        checkbox_layout.addWidget(self.keyboard_checkbox)

        self.instructions1_display = QLabel(
            "For Rudder    (+/- 3 degrees): A / S / D  (Left / Center / Right)"
        )
        self.instructions2_display = QLabel(
            "For Trim Tab (+/- 3 degrees): Q / W / E (Left / Center / Right)"
        )

        self.rudder_display = QLabel("Current Set Rudder Angle:  0 degrees")
        self.trimtab_display = QLabel("Current Trim Tab Angle:   0 degrees")

        self.desired_heading_input_layout = QVBoxLayout()
        self.desired_heading_input = QLineEdit()
        self.desired_heading_button = QPushButton("Set Desired Heading")
        self.desired_heading_label = QLabel("Heading Angle:")
        self.desired_heading_label.setStyleSheet(bold_text)
        self.desired_heading_input_layout.addWidget(self.desired_heading_label)
        self.desired_heading_input_layout.addSpacing(small_spacing)
        self.desired_heading_input_layout.addWidget(self.desired_heading_input)
        self.desired_heading_input_layout.addSpacing(small_spacing)
        self.desired_heading_input_layout.addWidget(self.desired_heading_button)
        self.desired_heading_button.clicked.connect(self.send_desired_heading)
        self.desired_heading_input_group = QWidget()
        self.desired_heading_input_group.setLayout(self.desired_heading_input_layout)

        self.rudder_input_layout = QVBoxLayout()
        self.rudder_input = QLineEdit()
        self.rudder_button = QPushButton("Send Rudder")
        self.rudder_input_label = QLabel("Rudder Angle:")
        self.rudder_input_label.setStyleSheet(bold_text)
        self.rudder_input_layout.addWidget(self.rudder_input_label)
        self.rudder_input_layout.addSpacing(small_spacing)
        self.rudder_input_layout.addWidget(self.rudder_input)
        self.rudder_input_layout.addSpacing(small_spacing)
        self.rudder_input_layout.addWidget(self.rudder_button)
        self.rudder_button.clicked.connect(self.send_rudder)
        self.rudder_input_group = QWidget()
        self.rudder_input_group.setLayout(self.rudder_input_layout)

        self.trim_input = QLineEdit()
        self.trim_button = QPushButton("Send Trim Tab")
        self.trim_button.clicked.connect(self.send_trim_tab)
        self.trim_input_layout = QVBoxLayout()
        self.trim_input_label = QLabel("Trim Tab Angle:")
        self.trim_input_label.setStyleSheet(bold_text)
        self.trim_input_layout.addWidget(self.trim_input_label)
        self.trim_input_layout.addSpacing(small_spacing)
        self.trim_input_layout.addWidget(self.trim_input)
        self.trim_input_layout.addSpacing(small_spacing)
        self.trim_input_layout.addWidget(self.trim_button)
        self.trim_input_group = QWidget()
        self.trim_input_group.setLayout(self.trim_input_layout)

        self.p_input = QLineEdit()
        self.p_input.setPlaceholderText("P")
        self.i_input = QLineEdit()
        self.i_input.setPlaceholderText("I")
        self.d_input = QLineEdit()
        self.d_input.setPlaceholderText("D")
        self.pid_input_layout = QHBoxLayout()
        self.pid_input_layout.addWidget(self.p_input)
        self.pid_input_layout.addWidget(self.i_input)
        self.pid_input_layout.addWidget(self.d_input)
        self.pid_input_button = QPushButton("Send PID")
        self.pid_input_button.clicked.connect(self.send_pid)
        self.pid_layout = QVBoxLayout()
        self.pid_layout.addLayout(self.pid_input_layout)
        self.pid_layout.addWidget(self.pid_input_button)

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setMinimumWidth(350)

        self.terminal_output_display = QTextEdit()
        self.terminal_output_display.setReadOnly(True)

        # Emergency controls
        self.emergency_checkbox = QCheckBox("Enable Emergency Controls")
        self.emergency_checkbox.stateChanged.connect(self.toggle_emergency_buttons)

        self.power_off_btn = QPushButton("Power Off Indefinitely")
        self.power_off_btn.setEnabled(False)
        self.power_off_btn.clicked.connect(self.send_power_off_indefinitely)

        self.restart_btn = QPushButton("Restart Power After 20s")
        self.restart_btn.setEnabled(False)
        self.restart_btn.clicked.connect(self.send_restart_power)

        self.ssh_instructions_label = QLabel(
            "SSH Terminal Instructions:\n"
            "1. Open separate terminal/PowerShell\n"
            "2. ssh sailbot@192.168.0.10\n"
            "3. Password: sailbot\n"
            "\nUse buttons below to copy commands:"
        )
        self.ssh_instructions_label.setStyleSheet("""
            QLabel {
                color: blue;
                font-size: 11px;
                font-weight: bold;
                padding: 4px;
                background-color: #e6f3ff;
                border: 2px solid #4d94ff;
                border-radius: 3px;
                margin: 2px;
            }
        """)

        self.commands_grid = QGridLayout()
        commands = [
            ("SSH Connect", "ssh sailbot@192.168.0.10"),
            ("CAN0 Down", "sudo ip link set can0 down"),
            ("CAN0 Up", "sudo ip link set can0 up type can bitrate 500000 dbitrate 1000000 fd on"),
            ("Check CAN Status", "ip link show can0"),
            ("View System Logs", "dmesg | tail"),
            ("System Info", "uname -a")
        ]
        
        self.command_buttons = []
        for i, (label, command) in enumerate(commands):
            btn = QPushButton(f"Copy: {label}")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4d94ff;
                    color: white;
                    border: none;
                    padding: 2px 4px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0066cc;
                }
                QPushButton:pressed {
                    background-color: #003d7a;
                }
            """)
            btn.clicked.connect(lambda checked, cmd=command: self.copy_to_clipboard(cmd))
            self.command_buttons.append(btn)
            row = i // 2
            col = i % 2
            self.commands_grid.addWidget(btn, row, col)

        red_button_style = """
                QPushButton {
                    background-color: red;
                    color: white;
                    border: none;
                    padding: 3px 6px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover:enabled {
                    background-color: yellow;
                    color: black;
                }
                QPushButton:disabled {
                    background-color: yellow;
                    color: black;
                }
            """
        
        self.power_off_btn.setStyleSheet(red_button_style)
        self.restart_btn.setStyleSheet(red_button_style)

        left_layout = QVBoxLayout()
        left_layout.addLayout(top_bar_layout)
        left_layout.addLayout(checkbox_layout)
        left_layout.addSpacing(5)
        left_layout.addWidget(self.instructions1_display)
        left_layout.addWidget(self.instructions2_display)
        left_layout.addSpacing(5)
        left_layout.addWidget(self.rudder_display)
        left_layout.addWidget(self.trimtab_display)
        left_layout.addSpacing(5)
        input_layout = QGridLayout()
        input_layout.setSpacing(0)
        input_layout.addWidget(self.rudder_input_group, 0, 0)
        input_layout.addWidget(self.trim_input_group, 0, 1)
        input_layout.addWidget(self.desired_heading_input_group, 0, 0)
        left_layout.addLayout(input_layout)
        left_layout.addLayout(self.pid_layout)

        self.rudder_input_group.setVisible(False)

        left_layout.addSpacing(5)
        left_layout.addWidget(QLabel("Candump Output:"))
        left_layout.addWidget(self.output_display)
        left_layout.addSpacing(5)
        left_layout.addWidget(self.emergency_checkbox)
        left_layout.addSpacing(5)
        left_layout.addWidget(self.power_off_btn)
        left_layout.addWidget(self.restart_btn)
        left_layout.addSpacing(5)
        left_layout.addWidget(self.ssh_instructions_label)
        left_layout.addSpacing(5)
        left_layout.addLayout(self.commands_grid)

        right_layout = QVBoxLayout()
        labels_layout = QVBoxLayout()
        labels_layout.setSpacing(0)

        for obj in all_objs:
            if obj.label is not None:
                labels_layout.addWidget(obj.label)
        labels_layout.addStretch(1)
                
        right_graphs_layout = QVBoxLayout()
        for obj in all_objs:
            if obj.graph is not None:
                right_graphs_layout.addWidget(obj.graph.canvas)

        container_widget = QWidget()
        container_widget.setLayout(right_graphs_layout)
        container_sp = container_widget.sizePolicy()
        container_sp.setHorizontalPolicy(QSizePolicy.Minimum)
        container_widget.setSizePolicy(container_sp)
        container_widget.setMinimumWidth(300)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(container_widget)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn) 
        
        right_layout.addWidget(scroll_area)

        bottom_layout = QHBoxLayout()
        bottom_layout.addLayout(left_layout)
        bottom_layout.addLayout(labels_layout)
        bottom_layout.addLayout(right_layout, 1)

        self.setLayout(bottom_layout)
    
    def set_manual_steer(self, checked):
        self.rudder_input_group.setVisible(checked)
        self.desired_heading_input_group.setVisible(not checked)

    def toggle_keyboard_mode(self, checked):
        self.rudder_input.setDisabled(checked)
        self.rudder_button.setDisabled(checked)
        self.trim_input.setDisabled(checked)
        self.trim_button.setDisabled(checked)

    def toggle_emergency_buttons(self, state):
        enabled = state == Qt.Checked
        self.power_off_btn.setEnabled(enabled)
        self.restart_btn.setEnabled(enabled)

    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.output_display.append(f"[COPIED] {text}")

    def keyPressEvent(self, event):
        if not self.keyboard_checkbox.isChecked():
            return

        key = event.key()
        if key == Qt.Key_A:
            self.rudder_angle = max(self.rudder_angle - 3, -45)
            self.send_rudder(from_keyboard=True)
        elif key == Qt.Key_D:
            self.rudder_angle = min(self.rudder_angle + 3, 45)
            self.send_rudder(from_keyboard=True)
        elif key == Qt.Key_S:
            self.rudder_angle = 0
            self.send_rudder(from_keyboard=True)
        elif key == Qt.Key_Q:
            self.trimtab_angle = max(self.trimtab_angle - 3, -45)
            self.send_trim_tab(from_keyboard=True)
        elif key == Qt.Key_E:
            self.trimtab_angle = min(self.trimtab_angle + 3, 45)
            self.send_trim_tab(from_keyboard=True)
        elif key == Qt.Key_W:
            self.trimtab_angle = 0
            self.send_trim_tab(from_keyboard=True)
    
    def can_send(self, frame_id, data, display_msg):
        """
        Helper function for sending CAN messages
        frame_id: full frame id of message as a string WITHOUT 0x prefix (eg. 001, 041)
        data: hex string of message in little endian
        display_msg: Message to be outputted on GUI CAN_DUMP display
        """
        try:
            msg = "cansend " + can_line + " " + frame_id + "##0" + data
            self.cansend_queue.put(msg)
            self.output_display.append(f"[{display_msg}] {msg}")
        except Exception as e:
            print(f"ERROR - Command not logged: {str(e)}")

    def send_trim_tab(self, from_keyboard=False):
        try:
            angle = self.trimtab_angle if from_keyboard else int(self.trim_input.text())
            if not from_keyboard:
                self.trimtab_angle = angle
            if angle < -90:
                raise ValueError("Invalid angle input for Trim Tab")
            value = convert_to_hex((angle + 90) * 1000, 4)
            self.can_send("002", convert_to_little_endian(value), "TRIMTAB SENT")
            self.trimtab_display.setText(f"Current Trim Tab Angle: {self.trimtab_angle} degrees")
        except ValueError as e:
            print(f"ValueError: {e}")
            self.show_error(f"ValueError: {e}")

    def send_desired_heading(self):
        try:
            heading = float(self.desired_heading_input.text())
            data = convert_to_little_endian(convert_to_hex(int(heading * 1000), 4))
            status_byte = "00"  # a = 0, b = 0, c = 0
            self.can_send("001", data + status_byte, "HEADING SENT")
            desired_heading_obj.add_datapoint(time.time() - self.time_start, heading)
            desired_heading_obj.update_label()
        except ValueError as e:
            self.show_error(f"Invalid angle input for desired heading: {e}")
        except Exception:
            self.show_error("Exception thrown from send_desired_heading")

    def send_rudder(self, from_keyboard=False):
        try:
            angle = self.rudder_angle if from_keyboard else int(self.rudder_input.text())
            if not from_keyboard:
                self.rudder_angle = angle
            if angle < -90:
                raise ValueError("Invalid angle input for Rudder")
            data = convert_to_little_endian(convert_to_hex((angle + 90) * 1000, 4))
            status_byte = "80"
            self.can_send("001", data + status_byte, "RUDDER SENT")
            self.rudder_display.setText(f"Current Set Rudder Angle:  {self.rudder_angle} degrees")
            set_rudder_obj.add_datapoint(time.time() - self.time_start, angle)
            set_rudder_obj.update_label()
        except ValueError:
            self.show_error("Invalid angle input for Rudder")
        except Exception:
            self.show_error("Exception thrown from send_rudder")

    def send_power_off_indefinitely(self):
        self.can_send("202", "0A", "POWER OFF")

    def send_restart_power(self):
        self.can_send("202", "14", "RESTART POWER")
        self.can_send("003", "0F", "")

    def send_pid(self):
        try:
            p = convert_to_little_endian(
                convert_to_hex(int(float(self.p_input.text()) * 1000000), 4)
            )
            i = convert_to_little_endian(
                convert_to_hex(int(float(self.i_input.text()) * 1000000), 4)
            )
            d = convert_to_little_endian(
                convert_to_hex(int(float(self.d_input.text()) * 1000000), 4)
            )

            can_data = p + i + d
            self.can_send("200", can_data, "SEND PID")

        except ValueError as v:
            self.show_error(f"Invalid input for p, i, or d: {v}")
        except Exception as e:
            print(f"Exception thrown from send_pid: {e}")
            self.show_error(f"Exception thrown from send_pid: {e}")

    def update_status(self):
        current_time = time.time() - self.time_start
        data_updated = False
        candump_lines = []

        # Process all pending CAN lines quickly
        while not self.queue.empty():
            line = self.queue.get()
            candump_lines.append(line)

            if not line.startswith(can_line):
                continue

            parts = line.split()
            if len(parts) <= 2:
                continue

            frame_id = parts[1].lower()
            # Extract payload once
            raw_part = line.split(']')[-1].strip()
            if not raw_part:
                continue
            raw_data = raw_part.split()
            data_hex = ''.join(raw_data)
            if not data_hex:
                continue

            self.time_history.append(current_time)
            data_updated = True

            try:
                if frame_id == "206":
                    parsed = parse_0x206_frame(data_hex)
                    for obj in pdb_objs:
                        obj.parse_frame(current_time, None, parsed)
                        obj.update_label()
                elif frame_id == "204":
                    parsed = parse_0x204_frame(data_hex)
                    for obj in rudder_objs:
                        obj.parse_frame(current_time, None, parsed)
                        obj.update_label()
                elif frame_id == "041":
                    parsed = parse_0x041_frame(data_hex)
                    for obj in data_wind_objs:
                        obj.parse_frame(current_time, None, parsed)
                        obj.update_label()
            except Exception as e:
                self.output_display.append(f"[PARSE ERROR 0x{frame_id}] {str(e)}")

        # If any data was updated, trim histories, update plots, and log values
        if data_updated and len(self.time_history) > 0:
            # Trim histories once per update cycle
            for obj in all_objs:
                obj.update_data(current_time, scroll_window)

            self._update_plot_ranges(current_time)

        # Desired heading periodic point (for plotting continuity)
        current_dheading = desired_heading_obj.get_current()
        if (current_dheading[1] is not None
                and (current_time - current_dheading[0]) > 5):
            desired_heading_obj.add_datapoint(current_time, current_dheading[1])

        # Temperature / connection status
        if self.temp_pipe.poll():
            connected, value = self.temp_pipe.recv()
            self.temp_label.setText(f"RPI Temp: {value}" if connected else "RPI Temp: --")
            self.status_label.setText("CONNECTED" if connected else "DISCONNECTED")
            self.status_label.setStyleSheet("color: green" if connected else "color: red")
            self.last_temp_update = time.time()
        else:
            if time.time() - self.last_temp_update > 5.0:
                self.temp_label.setText("RPI Temp: --")
                self.status_label.setText("DISCONNECTED")
                self.status_label.setStyleSheet("color: red")

        # CAN send responses
        while not self.cansend_response_queue.empty():
            cmd, out, err = self.cansend_response_queue.get()
            if err:
                self.output_display.append(f"[ERR] {err.strip()}")
            elif out:
                self.output_display.append(f"[OUT] {out.strip()}")

    def _update_plot_ranges(self, current_time):
        # X axis scrolling
        if len(self.time_history) > 1:
            for obj in all_objs:
                if obj.graph is not None:
                    obj.graph.ax.set_xlim(max(0, current_time - scroll_window), current_time)
        else:
            for obj in all_objs:
                if obj.graph is not None:
                    obj.graph.ax.relim()
                    obj.graph.ax.autoscale_view()

        # Auto Y adjustment
        for obj in all_objs:
            if obj.graph is not None:
                obj.adjust_ylim()

        # Redraw canvases
        for obj in all_objs:
            if obj.graph is not None:
                obj.graph.canvas.draw()

    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")

    queue = multiprocessing.Queue()
    parent_conn, child_conn = multiprocessing.Pipe()
    cmd_queue = multiprocessing.Queue()
    response_queue = multiprocessing.Queue()
    can_log_queue = multiprocessing.Queue()
    run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    candump_proc = multiprocessing.Process(
        target=candump_process, args=(queue, can_log_queue)
    )
    temp_proc = multiprocessing.Process(
        target=temperature_reader, args=(child_conn,)
    )
    cansend_proc = multiprocessing.Process(
        target=cansend_worker, args=(cmd_queue, response_queue, can_log_queue)
    )
    can_logging_proc = multiprocessing.Process(
        target=can_logging_process, args=(can_log_queue, run_timestamp)
    )

    candump_proc.start()
    temp_proc.start()
    cansend_proc.start()
    can_logging_proc.start()

    app = QApplication(sys.argv)
    window = CANWindow(queue, parent_conn, cmd_queue, response_queue,
                       can_log_queue, run_timestamp)
    window.show()

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print("Cleaning up...")

        try:
            window.closeEvent(None)
        except Exception:
            pass

        cmd_queue.put("__EXIT__")
        can_log_queue.put("__EXIT__")

        candump_proc.terminate()
        temp_proc.terminate()
        cansend_proc.terminate()
        can_logging_proc.terminate()

        candump_proc.join(timeout=2)
        temp_proc.join(timeout=2)
        cansend_proc.join(timeout=2)
        can_logging_proc.join(timeout=2)

        parent_conn.close()
        child_conn.close()

        queue.close()
        response_queue.close()
        cmd_queue.close()
        can_log_queue.close()
        
        print("Cleanup complete.")
