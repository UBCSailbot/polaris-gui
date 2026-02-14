import sys
import signal
import paramiko
import multiprocessing
import time
import csv
import os
import pygame
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QTextEdit, QHBoxLayout, QCheckBox, QGridLayout, QComboBox,
    QSizePolicy
)

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QFont

from can_processes import (
    candump_process, cansend_worker, temperature_reader, can_logging_process
)

from data_object import *
from utility import *

### ----------  Background CAN Dump Process ---------- ###
# def candump_process(queue: multiprocessing.Queue, testing):
#     client = paramiko.SSHClient()
#     client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     if (testing):
#         # TODO
#         print("TESTING MODE ON")
#     else:
#         try:
#             client.connect(hostname, username=username, password=password)
#             transport = client.get_transport()
#             # session = transport.open_session()
#             # session.exec_command("bash sailbot_workspace/scripts/canup.sh -l")
#             session = transport.open_session()
#             session.exec_command(f"candump {can_line}")
#             while True:
#                 if session.recv_ready():
#                     line = session.recv(1024).decode()
#                     lines = line.split("\n")
#                     for l in lines:
#                         if (l != ""): queue.put(l.strip())
#                 time.sleep(0.1)
#         except Exception as e:
#             queue.put(f"[ERROR] {str(e)}")
#         finally:
#             client.close()

### ---------- Background Temp Reader Process ---------- ###
# def temperature_reader(pipe):
#     client = paramiko.SSHClient()
#     client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     try:
#         client.connect(hostname, username=username, password=password)
#         while True:
#             try:
#                 stdin, stdout, stderr = client.exec_command("cat /sys/class/thermal/thermal_zone0/temp")
#                 raw = stdout.read().decode().strip()
#                 if raw:
#                     temp = float(raw) / 1000
#                     pipe.send((True, f"{temp:.1f}°C"))
#                 else:
#                     pipe.send((False, "ERROR"))
#             except Exception:
#                 pipe.send((False, "ERROR"))
#             time.sleep(1)
#     except Exception:
#         while True:
#             pipe.send((False, "DISCONNECTED"))
#             time.sleep(1)
#     finally:
#         client.close()

### ---------- Background CAN Send Worker ---------- ###
# def cansend_worker(cmd_queue: multiprocessing.Queue, response_queue: multiprocessing.Queue, can_log_queue: multiprocessing.Queue):
#     client = paramiko.SSHClient()
#     client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     try:
#         client.connect(hostname, username=username, password=password)
#         while True:
#             cmd = cmd_queue.get()
#             if cmd == "__EXIT__":
#                 break
#             try:
#                 out = ""
#                 err = ""
#                 if (cmd[0:4] == "sudo"):
#                     stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
#                     buf = ""
#                     while (not buf.endswith("[sudo] password for sailbot: ")):
#                         buf += stdout.channel.recv(1024).decode()
#                     stdin.write(f"{password}\n")
#                     stdin.flush()
#                     out = stdout.read().decode()
#                     err = stderr.read().decode()
#                 else:
#                     stdin, stdout, stderr = client.exec_command(cmd)
#                     out = stdout.read().decode()
#                     err = stderr.read().decode()

#                 response_queue.put((cmd, out, err))
#                 if (not err):
#                     can_log_queue.put_nowait(make_pretty(cmd))
#                 else:
#                     raise Exception(f"Command not logged: {cmd}")
#             except Exception as e:
#                 response_queue.put((cmd, "", f"Exec error: {str(e)}"))
#     except Exception as e:
#         response_queue.put(("ERROR", "", f"SSH error: {str(e)}"))
#     finally:
#         client.close()

### ---------- Background CAN Logging Process ---------- ###
# def can_logging_process(queue: multiprocessing.Queue, log_queue: multiprocessing.Queue, timestamp):
#     """Dedicated process for logging CAN messages without blocking graphics"""
#     try:
#         # Create logs directory if it doesn't exist
#         if not os.path.exists('logs'):
#             os.makedirs('logs')
        
#         # Create timestamped filename
#         # timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#         candump_log_file = os.path.join('logs', f'candump_{timestamp}.csv')
        
#         with open(candump_log_file, 'w', newline='') as csv_file:
#             writer = csv.writer(csv_file)
#             writer.writerow(['Timestamp', 'Elapsed_Time_s', 'CAN_Message'])
#             csv_file.flush()
            
#             start_time = time.time()
#             print(f"CAN Logging started: {candump_log_file}")
            
#             while True:
#                 try:
#                     # Get message from queue with timeout
#                     if not log_queue.empty():
#                         message = log_queue.get(timeout=1.0)
#                         if message == "__EXIT__":
#                             break
#                         # Log the message
#                         timestamp = datetime.now().isoformat()
#                         elapsed_time = time.time() - start_time
#                         writer.writerow([timestamp, f'{elapsed_time:.3f}', message])
#                         csv_file.flush()
#                 # except queue.empty as empty:
#                 #     print(f"CAN logging queue empty")
#                 except Exception as e:
#                     print(f"Error in CAN logging: {e}")
#                     continue
                    
#     except Exception as e:
#         print(f"Failed to initialize CAN logging: {e}")
    
#     print("CAN logging process terminated")

### ----------  PyQt5 GUI ---------- ###
class CANWindow(QWidget):
    def __init__(self, queue, temp_pipe, cmd_queue, response_queue, can_log_queue, joystick: pygame.joystick.JoystickType = None):
        super().__init__()
        self.queue = queue
        self.temp_pipe = temp_pipe
        self.cansend_queue = cmd_queue
        self.cansend_response_queue = response_queue
        self.can_log_queue = can_log_queue

        self.rudder_angle = 0 # degrees
        self.trimtab_angle = 0 # degrees
        self.last_temp_update = time.time()  # Track last temperature update

        self.setWindowTitle("Remote Node GUI - POLARIS")
        self.setGeometry(50, 30, cg.window_width, cg.window_height)
        self.setFocusPolicy(Qt.StrongFocus)

        self.time_start = time.time()
        self.time_history = []

        self.js = joystick # joystick
        self.js_prev_state = None # TODO: modify to be prev_pos instead
        self.js_prev_pos = 0
        self.js_enabled = False

        # Initialize logging
        self._init_logging()

        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(gui_update_freq) # Updates every update_freq milliseconds

    def _init_logging(self):
        """Initialize CSV logging files with timestamped names"""
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # Create timestamped filenames        
        # Values log file (CAN dump logging is now handled by separate process)
        self.values_log_file = os.path.join('logs', f'values_{timestamp}.csv')
        self.values_csv_file = open(self.values_log_file, 'w', newline='')
        self.values_writer = csv.writer(self.values_csv_file)

        # Header names
        values_header = [
            'Timestamp', 'Elapsed_Time_s'
        ]
        for obj in data_objs:
            values_header.append(obj.name)

        self.values_writer.writerow(values_header)
        self.values_csv_file.flush()  # Ensure header is written immediately
        
        print(f"Values logging initialized: {self.values_log_file}")

    # Makes given history the same length as time_history so it is plottable (note: this function works because lists are mutable and can be referenced through formal param)
    def update_history(self, history: list):
        while len(history) > len(self.time_history):
            history.pop(0)
        while len(history) < len(self.time_history):
            last_val = history[-1] if history else 0
            history.append(last_val)

    def _log_values(self):
        """Log current values to CSV file"""
        try:
            timestamp = datetime.now().isoformat()
            elapsed_time = time.time() - self.time_start
            values = [timestamp, f'{elapsed_time:.3f}']
            # print("line 222")
            for obj in data_objs:
                val = obj.get_current()[1]
                # print("line 225")
                if (val is not None):
                    values.append(str(val))
                else:
                    values.append("None")
                # print("line 230")
            # print("line 231")
            self.values_writer.writerow(values)
            # print("line 233")
            self.values_csv_file.flush()  # Flush immediately to prevent data loss
        except Exception as e:
            print(f"Error logging values: {e}")

    def closeEvent(self, event):
        """Handle window close event to ensure files are properly closed"""
        try:
            if hasattr(self, 'values_csv_file'):
                self.values_csv_file.close()
            print("Log files closed successfully")
        except Exception as e:
            print(f"Error closing log files: {e}")
        event.accept()

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

        self.instructions1_display = QLabel("For Rudder    (+/- 3 degrees): A / S / D  (Left / Center / Right)")
        self.instructions2_display = QLabel("For Trim Tab (+/- 3 degrees): Q / W / E (Left / Center / Right)")

        self.rudder_display = QLabel("Current Set Rudder Angle:  0 degrees")
        self.trimtab_display = QLabel("Current Trim Tab Angle:   0 degrees")

        self.desired_heading_input_layout = QVBoxLayout()
        self.desired_heading_input = QLineEdit()
        self.desired_heading_button = QPushButton("Set Desired Heading")
        self.desired_heading_label = QLabel("Heading Angle:")
        self.desired_heading_label.setStyleSheet(input_label_style)
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
        self.rudder_input_label.setStyleSheet(input_label_style)
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
        self.trim_input_label.setStyleSheet(input_label_style)
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

        # Separate terminal output display
        self.terminal_output_display = QTextEdit()
        self.terminal_output_display.setReadOnly(True)

        # Emergency controls section
        self.emergency_checkbox = QCheckBox("Enable Emergency Controls")
        self.emergency_checkbox.stateChanged.connect(self.toggle_emergency_buttons)

        # Power control buttons
        self.power_off_btn = QPushButton("Power Off Indefinitely")
        self.power_off_btn.setEnabled(False)
        self.power_off_btn.clicked.connect(self.send_power_off_indefinitely)

        self.restart_btn = QPushButton("Restart Power After 20s")
        self.restart_btn.setEnabled(False)
        self.restart_btn.clicked.connect(self.send_restart_power)

        emergency_controls_layout = QHBoxLayout()
        emergency_controls_layout.addWidget(self.power_off_btn)
        emergency_controls_layout.addWidget(self.restart_btn)

        # SSH Instructions for CAN and system control
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

        # Create a grid layout for command buttons
        self.commands_grid = QGridLayout()
        
        # Define commands with labels
        commands = [
            ("SSH Connect", "ssh sailbot@192.168.0.10"),
            ("CAN0 Down", "sudo ip link set can0 down"),
            ("CAN0 Up", "sudo ip link set can0 up type can bitrate 500000 dbitrate 1000000 fd on"),
            ("Check CAN Status", "ip link show can0"),
            ("View System Logs", "dmesg | tail"),
            ("System Info", "uname -a")
        ]
        
        # Create buttons for each command
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
            
            # Add to grid layout (2 columns)
            row = i // 2
            col = i % 2
            self.commands_grid.addWidget(btn, row, col)

        # Style for emergency buttons (power controls)
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
        left_layout.addSpacing(5)  # Add small spacing
        left_layout.addWidget(self.instructions1_display)
        left_layout.addWidget(self.instructions2_display)
        left_layout.addSpacing(5)  # Add small spacing
        left_layout.addWidget(self.rudder_display)
        left_layout.addWidget(self.trimtab_display)
        left_layout.addSpacing(5)  # Add small spacing
        input_layout = QGridLayout()
        input_layout.setSpacing(0)
        input_layout.addWidget(self.rudder_input_group, 0, 0)
        input_layout.addWidget(self.trim_input_group, 0, 1)
        input_layout.addWidget(self.desired_heading_input_group, 0, 0)
        left_layout.addLayout(input_layout)
        left_layout.addLayout(self.pid_layout)

        self.rudder_input_group.setVisible(False)

        left_layout.addSpacing(5)  # Add small spacing
        left_layout.addWidget(QLabel("Candump Output:"))
        left_layout.addWidget(self.output_display)
        left_layout.addSpacing(5)  # Add small spacing
        left_layout.addWidget(self.emergency_checkbox)
        left_layout.addSpacing(5)  # Add spacing before emergency buttons
        left_layout.addLayout(emergency_controls_layout)
        left_layout.addSpacing(5)  # Add spacing before SSH instructions
        left_layout.addWidget(self.ssh_instructions_label)
        left_layout.addSpacing(5)  # Small spacing before command buttons
        left_layout.addLayout(self.commands_grid)

        right_layout = QVBoxLayout()

        # right_labels_layout = QVBoxLayout()
        labels_layout = QVBoxLayout()
        labels_layout.setSpacing(0)

        for graph_obj in all_objs:
            if (graph_obj.label is not None):
                labels_layout.addWidget(graph_obj.label)
        
        labels_layout.addStretch(1)

        # Graph dropdowns (Top, Middle, Bottom)
        dropdown_layout = QHBoxLayout()
        d_top = QComboBox()
        d_mid = QComboBox()
        d_bot = QComboBox()
        dropdowns = [d_top, d_mid, d_bot]

        self.right_graphs_layout = QGridLayout() # create GridLayout for three graphs (0, 0), (1, 0), (2, 0)
        # Note: It is important that each distinct graph canvas is only added as a widget
        #       a single time, or else problems
        self.visibleGraphObjs = [] # list of GraphObjs with visible graphs, in order of position descending

        self.graph_titles = []
        for obj in all_objs:
            if ((obj.graph_obj is not None) and (obj.graph_obj.dropdown_label not in self.graph_titles)):
                self.graph_titles.append(obj.graph_obj.dropdown_label)

        for d in dropdowns:
            d.setFont(QFont(cg.d_font_type, cg.d_font_size))
            d.addItems(self.graph_titles)
            d.setVisible(False)
            dropdown_layout.addWidget(d)

        # show a maximum of three graphs initially 
        for i in range(0, 3):
            if (i < len(self.graph_titles)):
                graph_obj = self.getGraphObjFromXName(self.graph_titles[i])
                if (graph_obj not in self.visibleGraphObjs):
                    self.right_graphs_layout.addWidget(graph_obj.graph, i, 0)
                    self.visibleGraphObjs.append(graph_obj)
                    graph_obj.show()
                    dropdowns[i].setCurrentText(self.graph_titles[i])
                    dropdowns[i].setVisible(True)
            else: break

        d_top.currentTextChanged.connect(lambda text: self.setGraph(text, 0, dropdowns))
        d_mid.currentTextChanged.connect(lambda text: self.setGraph(text, 1, dropdowns))
        d_bot.currentTextChanged.connect(lambda text: self.setGraph(text, 2, dropdowns))
        
        right_layout.addLayout(dropdown_layout)
        right_layout.addLayout(self.right_graphs_layout)

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
        if self.js is not None: self.js_enabled = checked

    def toggle_emergency_buttons(self, state):
        enabled = state == Qt.Checked
        self.power_off_btn.setEnabled(enabled)
        self.restart_btn.setEnabled(enabled)

    def copy_to_clipboard(self, text):
        """Copy text to system clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        # Show a brief confirmation
        self.output_display.append(f"[COPIED] {text}")
            
    def getGraphObjFromXName(self, name):
        for obj in all_objs:
            if ((obj.graph_obj is not None) and (obj.graph_obj.dropdown_label == name)):
                return obj.graph_obj
            
    def getObjFromLabel(self, dropdown_label):
        for obj in all_objs:
            if ((obj.graph_obj is not None) and (obj.graph_obj.dropdown_label == dropdown_label)):
                return obj
            
    def setGraph(self, name, spot, dropdowns):
        '''
        Shows given graph at spot\n
        name = DataObj.graph_obj.dropdown_label\n
        spot = 0, 1, 2 (top, mid, bot)\n
        '''
        newObj = self.getObjFromLabel(name)
        # newGraphObj = self.getGraphObjFromXName(name) # get graph to put in spot
        newGraphObj = newObj.graph_obj

        if (newGraphObj.dropdown_label == self.visibleGraphObjs[spot].dropdown_label):
            return # do nothing
        if newGraphObj in self.visibleGraphObjs: # if graph to put in spot is already visible
            # don't allow the switch to happen - set dropdown text back to original and print error message
            print("[ERR] Graph is already visible")
            dropdowns[spot].setCurrentText(self.visibleGraphObjs[spot].dropdown_label) # switch text back to original
        else: 
            self.right_graphs_layout.removeWidget(self.visibleGraphObjs[spot].graph) # remove graph currently in spot
            self.visibleGraphObjs[spot].hide()
            self.right_graphs_layout.addWidget(newGraphObj.graph, spot, 0)
            newGraphObj.show()
            self.visibleGraphObjs[spot] = newGraphObj  
            newObj.update_line_data() 

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
        '''
        Helper function for sending CAN messages\n
        frame_id: full frame id of message as a string WITHOUT 0x prefix (eg. 001, 041)\n
        data: hex string of message in little endian (assumes valid data)\n
        display_msg: Message to be outputted on GUI CAN_DUMP display
        '''
        try:
            msg = "cansend " + can_line + " " + frame_id + "##0" + data
            self.cansend_queue.put(msg)
            self.output_display.append(f"[{display_msg}] {msg}")
        except Exception as e:
            print(f"ERROR - Command not sent: {str(e)}")

    def send_trim_tab(self, from_keyboard=False):
        try:
            angle = self.trimtab_angle if from_keyboard else int(self.trim_input.text())
            if not from_keyboard:
                self.trimtab_angle = angle
            if (angle < -90):
                raise ValueError("Invalid angle input for Trim Tab")
            value = convert_to_hex((angle+90) * 1000, 4)
            self.can_send("002", convert_to_little_endian(value), "TRIMTAB SENT")
            self.trimtab_display.setText(f"Current Trim Tab Angle: {self.trimtab_angle} degrees")
        except ValueError as e:
            print(f"ValueError: {e}")
            self.show_error(f"ValueError: {e}")

    def send_desired_heading(self):
        try:
            heading = float(self.desired_heading_input.text())
            data = convert_to_little_endian(convert_to_hex(int(heading * 1000), 4))
            status_byte = "00" # a = 0, b = 0, c = 0
            self.can_send("001", data + status_byte, "HEADING SENT")
            desired_heading_obj.add_datapoint(time.time() - self.time_start, heading)
            desired_heading_obj.update_label()
        except ValueError:
            self.show_error(f"Invalid angle input for desired heading: {e}")
        except Exception:
            print("Exception thrown from send_desired_heading")
            self.show_error("Exception thrown from send_desired_heading")

    def send_rudder(self, from_keyboard=False, set_angle: float = None):
        '''set_angle is a given angle'''
        try:
            if from_keyboard:
                # print(f"self.rudder_angle = {self.rudder_angle}")
                angle = self.rudder_angle
            elif set_angle is not None: 
                # print(f"set_angle = {round(set_angle, 3)}")
                angle = round(set_angle, 3)
            else: 
                # print(f"in else")
                angle = int(self.rudder_input.text())
            # angle = self.rudder_angle if from_keyboard else int(self.rudder_input.text())
            if not from_keyboard:
                self.rudder_angle = angle # TODO: Why is this here? Keep self.rudder_angle up-to-date?

            # print(f"from_keyboard = {from_keyboard}")
            # print(f"angle = {angle}")

            if (angle < -90):
                raise ValueError("ERR - Rudder Angle input < -90")
            
            # print("line 700")
            # step0 = round(angle)+90 * 1000
            # print("step0 = ", step0)
            # teststep = 90000
            # step1 = convert_to_hex(step0, 4)
            # print("line 701")

            data = convert_to_little_endian(convert_to_hex(round(angle)+90 * 1000, 4))
            
            # print("line 703")

            status_byte = "80" # a = 1, b = 0, c = 0
            self.can_send("001", data + status_byte, "RUDDER SENT")
            self.rudder_display.setText(f"Current Set Rudder Angle:  {self.rudder_angle} degrees")
            
            # print("line 709")

            set_rudder_obj.add_datapoint(time.time() - self.time_start, angle)
            set_rudder_obj.update_label()
            # print(f"at the end w/o error")

        except ValueError:
            self.show_error("Invalid angle input for Rudder")
        except Exception:
            print("Exception thrown from send_rudder")
            self.show_error("Exception thrown from send_rudder")

    def send_power_off_indefinitely(self):
        self.can_send("202", "0A", "POWER OFF")

    def send_restart_power(self):
        self.can_send("202", "14", "RESTART POWER")
        self.can_send("003", "0F", "")
    
    def send_pid(self):
        # check for valid p, i, d inputs
        try:
            p = convert_to_little_endian(convert_to_hex(int(float(self.p_input.text()) * 1000000), 4))
            i = convert_to_little_endian(convert_to_hex(int(float(self.i_input.text()) * 1000000), 4))
            d = convert_to_little_endian(convert_to_hex(int(float(self.d_input.text()) * 1000000), 4))
            can_data = p + i + d
            self.can_send("200", can_data, "SEND PID")

        except ValueError as v:
            self.show_error(f"Invalid input for p, i, or d: {v}")

        except Exception as e:
            print(f"Exception thrown from send_pid: {e}")
            self.show_error(f"Exception thrown from send_pid: {e}")

    # def get_current_time(self):
    #     return time.time() - self.time_start

    def update_status(self):
        # Update time independently of CAN messages
        current_time = time.time() - self.time_start
        
        # Process any new CAN messages
        while not self.queue.empty():
            line = self.queue.get()
            # self.output_display.append(line)

            new_msg_to_log = False
  
            # print(f"line parsed = {line}")

            # Send to separate logging process (non-blocking)
            # TODO: modify the nowait to ensure logging
            try:
                self.can_log_queue.put_nowait(line)
            except:
                print(f"line was not logged!")

            if line.startswith(can_line):
                new_msg_to_log = True
                parts = line.split()
                if len(parts) > 2:
                    frame_id = parts[1].lower()
                    self.time_history.append(current_time)
                    
                    # TODO: Use a dictionary with frame id:function - just runs the function associated with frame id?
                    # There's definitely some abstraction that can be done here
                    match frame_id:
                        case "041": # Data_Wind frame
                            try:
                                raw_data = line.split(']')[-1].strip().split()
                                parsed = parse_0x041_frame(''.join(raw_data))
                                for obj in data_wind_objs:
                                    obj.parse_frame(current_time, None, parsed)
                                    obj.update_label()
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x041] {str(e)}")
                        case "060": # AIS frame
                            try:
                                raw_data = line.split(']')[-1].strip().split()
                                parsed = parse_0x060_frame(''.join(raw_data))
                                # print("returned from parsed")
                                # print("sog: ", parsed[AIS_Attributes.SOG])
                                if parsed[AIS_Attributes.TOTAL] == 0: # if there are no ships
                                    # print("clear_data() called")
                                    ais_obj.clear_data()
                                    # TODO: log here?                                                                                           

                                ais_obj.add_frame(parsed[AIS_Attributes.LONGITUDE], parsed[AIS_Attributes.LATITUDE], parsed[AIS_Attributes.SID], parsed, AIS_Attributes.LONGITUDE) # TODO: This needs to change
                                # print("current data: ", ais_obj.data)
                                # print("parsed dict: ", parsed)
                                # print("index = ", parsed[AIS_Attributes.IDX])
                                # If this is the last frame in the batch
                                if parsed[AIS_Attributes.IDX] == (parsed[AIS_Attributes.TOTAL] - 1):
                                    ais_obj.log_data(datetime.now().isoformat(), time.time() - self.time_start)
                                    # print("total ships: ", len(ais_obj.data))
                                #     print("total ships (dataset len): ", len(ais_obj.dataset))

                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x060] {str(e)}")

                        case "070": # GPS frame
                                try:
                                    raw_data = line.split(']')[-1].strip().split()
                                    parsed = parse_0x070_frame(''.join(raw_data))
                                    for obj in gps_objs:
                                        obj.parse_frame(current_time, None, parsed)
                                        obj.update_label()

                                    if ais_obj.graph_obj.isVisible(): # graph POLARIS's current position if graph is visible
                                        ais_obj.update_polaris_pos(gps_lon_obj.get_current()[1], gps_lat_obj.get_current()[1])
                                
                                except Exception as e:
                                    self.output_display.append(f"[PARSE ERROR 0x070] {str(e)}")

                        case "100": # water_temp sensor frame
                            try:
                                temp_sensor_obj.parse_frame(current_time, line)
                                temp_sensor_obj.update_label()
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x100] {str(e)}")
                       
                        case "110": # pH sensor frame
                            try:               
                                pH_obj.parse_frame(current_time, line)
                                pH_obj.update_label()
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x110] {str(e)}")

                        case "120": # salinity sensor frame
                            try: 
                                sal_obj.parse_frame(current_time, line)
                                sal_obj.update_label()                                            
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x120] {str(e)}") 

                        case "204": # Handle 0x204 frame (actual rudder angle)

                            try:
                                raw_data = line.split(']')[-1].strip().split()
                                parsed = parse_0x204_frame(''.join(raw_data))
                                for obj in rudder_objs:
                                    obj.parse_frame(current_time, None, parsed)
                                    obj.update_label()
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x204] {str(e)}")
                           
                        case "206":
                            try:
                                raw_data = line.split(']')[-1].strip().split()
                                parsed = parse_0x206_frame(''.join(raw_data))
                                for obj in pdb_objs:
                                    obj.parse_frame(current_time, None, parsed)                           
                                    obj.update_label()
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x206] {str(e)}")
        
                        case _:
                            print(f"Frame id not recognized: {frame_id}")

                # Log current values
                if (new_msg_to_log and (len(self.time_history) > 0)):
                    # actual_rudder = self.actual_rudder_history[-1] if self.actual_rudder_history else None
                    self._log_values()

        # trim values no longer being graphed
        for obj in data_objs:
            obj.update_data(current_time, scroll_window)
                        
        # Always update plots every timer cycle (independent of CAN messages) # TODO: Modify this - batch plot updates?
        if len(self.time_history) > 0:
            self._update_plot_ranges(current_time)

        # Handle temperature updates with connection status tracking
        if self.temp_pipe.poll():
            connected, value = self.temp_pipe.recv()
            self.temp_label.setText(f"RPI Temp: {value}" if connected else "RPI Temp: --")
            self.status_label.setText("CONNECTED" if connected else "DISCONNECTED")
            self.status_label.setStyleSheet("color: green" if connected else "color: red")
            self.last_temp_update = time.time()
        else:
            # Check if we haven't received a temperature update in too long (connection lost)
            if time.time() - self.last_temp_update > 5.0:  # 5 second timeout
                self.temp_label.setText("RPI Temp: --")
                self.status_label.setText("DISCONNECTED")
                self.status_label.setStyleSheet("color: red")

        # Handle CAN send responses
        while not self.cansend_response_queue.empty():
            cmd, out, err = self.cansend_response_queue.get()
            if err:
                self.output_display.append(f"[ERR] {err.strip()}")
            elif out:
                self.output_display.append(f"[OUT] {out.strip()}")

        # Handle joystick updates
        pygame.event.pump() # Update joystick state
        # if self.js is not None and self.js_enabled:
        #     if (self.js.get_axis(3) > 0.9 or self.js.get_axis(0) > 0.9) and self.js_prev_state is not JS_DIRECTIONS.RIGHT:
        #         # print("A joystick is pointed to the right!")
        #         self.send_rudder(set_angle = cg.right_angle_change)
        #         self.js_prev_state = JS_DIRECTIONS.RIGHT
        #     elif(self.js.get_axis(3) < -0.9 or self.js.get_axis(0) < -0.9) and self.js_prev_state is not JS_DIRECTIONS.LEFT:
        #         # print("A joystick is pointed to the left!")
        #         self.send_rudder(set_angle = cg.left_angle_change)
        #         self.js_prev_state = JS_DIRECTIONS.LEFT
        #     elif (self.js.get_axis(3) == 0 and self.js.get_axis(0) == 0) and self.js_prev_state is not JS_DIRECTIONS.MIDDLE:
        #         # print("Both joysticks in the middle!")
        #         self.send_rudder(set_angle = cg.center_angle)
        #         self.js_prev_state = JS_DIRECTIONS.MIDDLE
    
        if self.js is not None and self.js_enabled:
            pos = round(self.js.get_axis(3), cg.movement_sensitivity)
            if (pos != round(self.js_prev_pos, cg.movement_sensitivity)):
                print(f"new angle = {pos * cg.max_angle}")
                self.send_rudder(set_angle = cg.max_angle * pos)
                self.js_prev_pos = pos

            # if (pos > 0.9) and self.js_prev_state is not JS_DIRECTIONS.RIGHT:
            #     self.send_rudder(set_angle = cg.right_angle_change * pos)
            #     self.js_prev_state = JS_DIRECTIONS.RIGHT
            # elif(pos < -0.9) and self.js_prev_state is not JS_DIRECTIONS.LEFT:
            #     self.send_rudder(set_angle = cg.left_angle_change * pos)
            #     self.js_prev_state = JS_DIRECTIONS.LEFT
            # elif (pos == 0) and self.js_prev_state is not JS_DIRECTIONS.MIDDLE:
            #     self.send_rudder(set_angle = cg.center_angle)
            #     self.js_prev_state = JS_DIRECTIONS.MIDDLE

    def _update_plot_ranges(self, current_time):
        # === Auto-scale and scroll X axis ===
        if len(self.time_history) > 1:
            for obj in data_objs:
                if (obj.graph_obj is not None):
                    obj.graph_obj.update_xlim(max(0, current_time - scroll_window), current_time)

    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

def key_interrupt_cleanup(a, b):
    sys.exit(app.exec_())
    cleanup()

def cleanup():
    print("Cleaning up...")
        
    # Close window and log files
    try:
        window.closeEvent(None)
    except:
        pass
    
    # Clean up processes
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

    # Optional but safe:
    queue.close()
    response_queue.close()
    cmd_queue.close()
    can_log_queue.close()
    
    print("Cleanup complete.")

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")

    # Multiprocess initialization
    queue = multiprocessing.Queue()
    parent_conn, child_conn = multiprocessing.Pipe()
    cmd_queue = multiprocessing.Queue()
    response_queue = multiprocessing.Queue()
    can_log_queue = multiprocessing.Queue()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    candump_proc = multiprocessing.Process(target=candump_process, args=(queue, False)) # Testing mode set to false when run from main
    temp_proc = multiprocessing.Process(target=temperature_reader, args=(child_conn,))
    cansend_proc = multiprocessing.Process(target=cansend_worker, args=(cmd_queue, response_queue, can_log_queue))
    can_logging_proc = multiprocessing.Process(target=can_logging_process, args=(queue, can_log_queue, timestamp))

    candump_proc.start()
    temp_proc.start()
    cansend_proc.start()
    can_logging_proc.start()

    # Cleanup (CTRL + C) initialization
    signal.signal(signal.SIGINT, key_interrupt_cleanup)

    # Joystick initialization
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No joystick detected.")
    try:
        js = pygame.joystick.Joystick(0)
        js.init()
        print(f"Connected to: {js.get_name()}")
    except Exception as e:
        js = None
        print(f"Joystick Connection Error: {e}")

    app = QApplication(sys.argv)
    for obj in all_objs:
        obj.initialize(timestamp) # create QWidgets
    window = CANWindow(queue, parent_conn, cmd_queue, response_queue, can_log_queue, joystick = js)
    window.show()

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt: # note: Ctrl+C doesn't work due to QT loop taking over
        print("\nKeyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        cleanup()
