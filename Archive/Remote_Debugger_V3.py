import sys
import paramiko
import multiprocessing
import time
import csv
import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QTextEdit, QHBoxLayout, QCheckBox, QGridLayout
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
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

def parse_0x206_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) < 14:
        raise ValueError("Insufficient data length")

    val = lambda s, e, div: int.from_bytes(raw_bytes[s:e], 'little') / div
    return {
        "volt_2": val(0, 2, 1000.0),
        "temp_1": val(2, 4, 100.0),
        "volt_3": val(4, 6, 1000.0),
        "temp_2": val(6, 8, 100.0),
        "temp_3": val(8, 10, 100.0),
        "volt_4": val(10, 12, 1000.0),
        "volt_1": val(12, 14, 1000.0)
    }

def parse_0x204_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) < 4:
        raise ValueError("Insufficient data length for 0x204 frame")
    
    # According to the image: Actual Rudder Angle is sent as (Rudder Angle + 90) * 1000
    actual_rudder_raw = int.from_bytes(raw_bytes[0:4], 'little')
    actual_rudder_angle = (actual_rudder_raw / 1000.0) - 90
    
    # Ignore angles outside reasonable range (-180° to +180°)
    if actual_rudder_angle < -180.0 or actual_rudder_angle > 180.0:
        print(f"DEBUG 0x204: WARNING - Angle {actual_rudder_angle}° outside valid range (-180° to +180°), ignoring")
        return None
    
    return {
        "actual_rudder_angle": actual_rudder_angle
    }

### ----------  Background CAN Dump Process ---------- ###
def candump_process(queue: multiprocessing.Queue):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname, username=username, password=password)
        transport = client.get_transport()
        session = transport.open_session()
        session.exec_command("candump can1")
        while True:
            if session.recv_ready():
                line = session.recv(1024).decode()
                queue.put(line.strip())
            time.sleep(0.1)
    except Exception as e:
        queue.put(f"[ERROR] {str(e)}")
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
def cansend_worker(cmd_queue: multiprocessing.Queue, response_queue: multiprocessing.Queue):
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
            except Exception as e:
                response_queue.put((cmd, "", f"Exec error: {str(e)}"))
    except Exception as e:
        response_queue.put(("ERROR", "", f"SSH error: {str(e)}"))
    finally:
        client.close()

### ---------- Background CAN Logging Process ---------- ###
def can_logging_process(queue: multiprocessing.Queue, log_queue: multiprocessing.Queue):
    """Dedicated process for logging CAN messages without blocking graphics"""
    try:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # Create timestamped filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        candump_log_file = os.path.join('logs', f'candump_{timestamp}.csv')
        
        with open(candump_log_file, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['Timestamp', 'Elapsed_Time_s', 'CAN_Message'])
            csv_file.flush()
            
            start_time = time.time()
            print(f"CAN Logging started: {candump_log_file}")
            
            while True:
                try:
                    # Get message from queue with timeout
                    message = log_queue.get(timeout=1.0)
                    if message == "__EXIT__":
                        break
                    
                    # Log the message
                    timestamp = datetime.now().isoformat()
                    elapsed_time = time.time() - start_time
                    writer.writerow([timestamp, f'{elapsed_time:.3f}', message])
                    csv_file.flush()
                    
                except Exception as e:
                    print(f"Error in CAN logging: {e}")
                    continue
                    
    except Exception as e:
        print(f"Failed to initialize CAN logging: {e}")
    
    print("CAN logging process terminated")

### ----------  PyQt5 GUI ---------- ###
class CANWindow(QWidget):
    def __init__(self, queue, temp_pipe, cmd_queue, response_queue, can_log_queue):
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
        self.setGeometry(300, 300, 1200, 600)
        self.setFocusPolicy(Qt.StrongFocus)

        # Set global font style for all widgets
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.setFont(font)

        self.time_start = time.time()
        self.time_history = []
        self.temp1_history = []
        self.temp2_history = []
        self.temp3_history = []
        self.volt1_history = []
        self.volt2_history = []
        self.volt3_history = []
        self.volt4_history = []
        self.actual_rudder_history = []
        self.set_rudder_history = []

        # Initialize logging
        self._init_logging()

        self.init_ui()

        # Change timer to 100ms for faster updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(100)  # Changed from 500ms to 100ms

    def _init_logging(self):
        """Initialize CSV logging files with timestamped names"""
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # Create timestamped filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Values log file (CAN dump logging is now handled by separate process)
        self.values_log_file = os.path.join('logs', f'values_{timestamp}.csv')
        self.values_csv_file = open(self.values_log_file, 'w', newline='')
        self.values_writer = csv.writer(self.values_csv_file)
        self.values_writer.writerow([
            'Timestamp', 'Elapsed_Time_s', 
            'Temp1_C', 'Temp2_C', 'Temp3_C',
            'Volt1_V', 'Volt2_V', 'Volt3_V', 'Volt4_V',
            'Set_Rudder_deg', 'Actual_Rudder_deg'
        ])
        self.values_csv_file.flush()  # Ensure header is written immediately
        
        print(f"Values logging initialized: {self.values_log_file}")

    def _log_values(self, temp1, temp2, temp3, volt1, volt2, volt3, volt4, set_rudder, actual_rudder):
        """Log current values to CSV file"""
        try:
            timestamp = datetime.now().isoformat()
            elapsed_time = time.time() - self.time_start
            self.values_writer.writerow([
                timestamp, f'{elapsed_time:.3f}',
                f'{temp1:.2f}', f'{temp2:.2f}', f'{temp3:.2f}',
                f'{volt1:.2f}', f'{volt2:.2f}', f'{volt3:.2f}', f'{volt4:.2f}',
                f'{set_rudder:.0f}', f'{actual_rudder:.1f}' if actual_rudder is not None else ''
            ])
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
        self.temp_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setStyleSheet("color: red; font-size: 16px; font-weight: bold;")

        top_bar_layout = QHBoxLayout()
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.logo_label)
        top_bar_layout.addSpacing(10)
        top_bar_layout.addWidget(self.temp_label)
        top_bar_layout.addSpacing(10)
        top_bar_layout.addWidget(self.status_label)
        top_bar_layout.addStretch()

        # === Live Value Display ===
        value_style = """
            color: black;
            font-size: 14px;
            font-weight: bold;
            padding: 6px;
            background-color: #f0f0f0;
            border: 2px solid #cccccc;
            border-radius: 6px;
            margin: 1px;
        """
        
        self.temp_values_label = QLabel("Temperature Values: --")
        self.temp_values_label.setAlignment(Qt.AlignLeft)
        self.temp_values_label.setStyleSheet(value_style)
        
        self.volt_values_label = QLabel("Voltage Values: --")
        self.volt_values_label.setAlignment(Qt.AlignLeft)
        self.volt_values_label.setStyleSheet(value_style)
        
        self.rudder_values_label = QLabel("Rudder Angles:        Set:    0°       Actual:    --")
        self.rudder_values_label.setAlignment(Qt.AlignLeft)
        self.rudder_values_label.setStyleSheet(value_style)

        
        # === Temperature Plot ===
        self.temp_figure = Figure(figsize=(8, 4), tight_layout=True)
        self.temp_canvas = FigureCanvas(self.temp_figure)
        self.temp_ax = self.temp_figure.add_subplot(111)
        self.temp_ax.set_title("Temperatures vs Time", fontsize=16, fontweight='bold')
        self.temp_ax.set_xlabel("Time (s)", fontsize=14, fontweight='bold')
        self.temp_ax.set_ylabel("Temp (°C)", fontsize=14, fontweight='bold')
        self.temp_ax.tick_params(axis='both', which='major', labelsize=12)
        self.temp_ax.set_xlim(0, 60)  # Set initial X range to 0-60 seconds
        self.temp_ax.set_ylim(0, 100)
        self.temp_ax.grid(True, alpha=0.3)
        
        # Initialize empty lines for temperature data
        self.temp1_line, = self.temp_ax.plot([], [], 'r-', label='Temp Battery Pack 2 (Port)', linewidth=2)
        self.temp2_line, = self.temp_ax.plot([], [], 'g-', label='Temp Buck Boost (PDB)', linewidth=2)
        self.temp3_line, = self.temp_ax.plot([], [], 'y-', label='Temp Battery Pack 1 (Starboard)', linewidth=2)
        legend = self.temp_ax.legend()
        legend.set_title("Temperature Sensors", prop={'size': 12, 'weight': 'bold'})
        for text in legend.get_texts():
            text.set_fontsize(11)
            text.set_fontweight('bold')

        # === Voltage Plot ===
        self.volt_figure = Figure(figsize=(8, 4), tight_layout=True)
        self.volt_canvas = FigureCanvas(self.volt_figure)
        self.volt_ax = self.volt_figure.add_subplot(111)
        self.volt_ax.set_title("Cell Voltages vs Time", fontsize=16, fontweight='bold')
        self.volt_ax.set_xlabel("Time (s)", fontsize=14, fontweight='bold')
        self.volt_ax.set_ylabel("Voltage (V)", fontsize=14, fontweight='bold')
        self.volt_ax.tick_params(axis='both', which='major', labelsize=12)
        self.volt_ax.set_xlim(0, 60)  # Set initial X range to 0-60 seconds
        self.volt_ax.set_ylim(0, 5)
        self.volt_ax.grid(True, alpha=0.3)
        
        # Initialize empty lines for voltage data
        self.volt1_line, = self.volt_ax.plot([], [], 'b-', label='Volt 1', linewidth=2)
        self.volt2_line, = self.volt_ax.plot([], [], 'c-', label='Volt 2', linewidth=2)
        self.volt3_line, = self.volt_ax.plot([], [], 'm-', label='Volt 3', linewidth=2)
        self.volt4_line, = self.volt_ax.plot([], [], 'orange', label='Volt 4', linewidth=2)
        legend = self.volt_ax.legend()
        legend.set_title("Voltage Channels", prop={'size': 12, 'weight': 'bold'})
        for text in legend.get_texts():
            text.set_fontsize(11)
            text.set_fontweight('bold')

        # === Rudder Angle Plot ===
        self.rudder_figure = Figure(figsize=(8, 4), tight_layout=True)
        self.rudder_canvas = FigureCanvas(self.rudder_figure)
        self.rudder_ax = self.rudder_figure.add_subplot(111)
        self.rudder_ax.set_title("Rudder Angle Comparison vs Time", fontsize=16, fontweight='bold')
        self.rudder_ax.set_xlabel("Time (s)", fontsize=14, fontweight='bold')
        self.rudder_ax.set_ylabel("Angle (degrees)", fontsize=14, fontweight='bold')
        self.rudder_ax.tick_params(axis='both', which='major', labelsize=12)
        self.rudder_ax.set_xlim(0, 60)  # Set initial X range to 0-60 seconds
        self.rudder_ax.set_ylim(-50, 50)  # Rudder range is typically -45 to +45 degrees
        self.rudder_ax.grid(True, alpha=0.3)
        
        # Initialize empty lines for rudder data
        self.actual_rudder_line, = self.rudder_ax.plot([], [], 'r-', linewidth=3, label='Actual Rudder')
        self.set_rudder_line, = self.rudder_ax.plot([], [], 'b--', linewidth=3, label='Set Rudder')
        legend = self.rudder_ax.legend()
        legend.set_title("Rudder Control", prop={'size': 12, 'weight': 'bold'})
        for text in legend.get_texts():
            text.set_fontsize(11)
            text.set_fontweight('bold')

        # Auto-scaling enabled for proper initial display

        # === Left Panel ===
        self.keyboard_checkbox = QCheckBox("Keyboard Mode")
        self.keyboard_checkbox.toggled.connect(self.toggle_keyboard_mode)

        self.instructions1_display = QLabel("For Rudder    (+/- 3 degrees): A / S / D  (Left / Center / Right)")
        self.instructions2_display = QLabel("For Trim Tab (+/- 3 degrees): Q / W / E (Left / Center / Right)")

        self.rudder_display = QLabel("Current Rudder Angle:      0 degrees")
        self.trimtab_display = QLabel("Current Trim Tab Angle:   0 degrees")

        self.rudder_input = QLineEdit()
        self.rudder_button = QPushButton("Send Rudder")
        self.rudder_button.clicked.connect(self.send_rudder)

        self.trim_input = QLineEdit()
        self.trim_button = QPushButton("Send Trim Tab")
        self.trim_button.clicked.connect(self.send_trim_tab)

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setMaximumHeight(200)  # Limit height for candump
        self.output_display.setStyleSheet("""
            QTextEdit {
                font-weight: normal;
                font-size: 14px;
                font-family: 'Courier New', monospace;
            }
        """)

        # Separate terminal output display
        self.terminal_output_display = QTextEdit()
        self.terminal_output_display.setReadOnly(True)
        self.terminal_output_display.setMaximumHeight(150)  # Smaller for terminal commands

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

        # SSH Instructions for CAN and system control
        self.ssh_instructions_widget = QWidget()
        self.ssh_instructions_widget.setStyleSheet("""
            QWidget {
                background-color: #e6f3ff;
                border: 2px solid #4d94ff;
                border-radius: 6px;
                margin: 2px;
                padding: 5px;
            }
        """)
        
        ssh_layout = QVBoxLayout(self.ssh_instructions_widget)
        ssh_layout.setSpacing(2)
        ssh_layout.setContentsMargins(8, 8, 8, 8)
        
        # Define commands with shorter labels for inline display
        commands = [
            ("ssh sailbot@192.168.0.10", "SSH Connect"),
            ("sudo ip link set can1 down", "CAN Down"),
            ("sudo ip link set can1 up type can bitrate 500000 dbitrate 1000000 fd on", "CAN Up"),
            ("sudo rmmod spi_bcm2835aux", "Remove SPI"),
            ("sudo modprobe spi_bcm2835aux", "Load SPI")
        ]
        
        # Create horizontal layouts for each command with inline copy button
        self.command_copy_buttons = []
        for command, label in commands:
            cmd_layout = QHBoxLayout()
            cmd_layout.setContentsMargins(0, 0, 0, 0)
            cmd_layout.setSpacing(5)
            
            # Command text
            cmd_label = QLabel(f"• {command}")
            cmd_label.setStyleSheet("""
                QLabel {
                    color: blue;
                    font-size: 11px;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }
            """)
            
            # Small copy button
            copy_btn = QPushButton(f"Copy")
            copy_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4d94ff;
                    color: white;
                    border: none;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                    min-height: 18px;
                    max-height: 18px;
                    min-width: 35px;
                    max-width: 35px;
                }
                QPushButton:hover {
                    background-color: #0066cc;
                }
                QPushButton:pressed {
                    background-color: #003d7a;
                }
            """)
            copy_btn.clicked.connect(lambda checked, cmd=command: self.copy_to_clipboard(cmd))
            self.command_copy_buttons.append(copy_btn)
            
            cmd_layout.addWidget(cmd_label)
            cmd_layout.addStretch()
            cmd_layout.addWidget(copy_btn)
            
            ssh_layout.addLayout(cmd_layout)
        
        # Add disclaimer
        disclaimer_text = QLabel("\nDISCLAIMER: If CAN HAT doesn't work, try the SPI commands above")
        disclaimer_text.setStyleSheet("""
            QLabel {
                color: blue;
                font-size: 11px;
                font-weight: bold;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        ssh_layout.addWidget(disclaimer_text)

        # Style for emergency buttons (power controls)
        red_button_style = """
                QPushButton {
                    background-color: red;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 16px;
                    min-height: 35px;
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
        left_layout.addWidget(self.keyboard_checkbox)
        left_layout.addSpacing(20)  # Add small spacing
        left_layout.addWidget(self.instructions1_display)
        left_layout.addWidget(self.instructions2_display)
        left_layout.addSpacing(20)  # Add small spacing
        left_layout.addWidget(self.rudder_display)
        left_layout.addWidget(self.trimtab_display)
        left_layout.addSpacing(20)  # Add small spacing
        left_layout.addWidget(QLabel("Rudder Angle:"))
        left_layout.addWidget(self.rudder_input)
        left_layout.addWidget(self.rudder_button)
        left_layout.addSpacing(20)  # Add small spacing
        left_layout.addWidget(QLabel("Trim Tab Angle:"))
        left_layout.addWidget(self.trim_input)
        left_layout.addWidget(self.trim_button)
        left_layout.addSpacing(20)  # Add small spacing
        left_layout.addWidget(QLabel("Candump Output:"))
        left_layout.addWidget(self.output_display)
        left_layout.addSpacing(8)  # Add small spacing
        left_layout.addWidget(self.emergency_checkbox)
        left_layout.addSpacing(10)  # Add spacing before emergency buttons
        left_layout.addWidget(self.power_off_btn)
        left_layout.addWidget(self.restart_btn)
        left_layout.addSpacing(10)  # Add spacing before SSH instructions
        left_layout.addWidget(self.ssh_instructions_widget)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(0)  # Remove spacing between widgets
        right_layout.addWidget(self.temp_values_label)
        right_layout.addWidget(self.volt_values_label)
        right_layout.addWidget(self.rudder_values_label)
        right_layout.addSpacing(5)  # Add small spacing before plots
        right_layout.addWidget(self.temp_canvas)
        right_layout.addWidget(self.volt_canvas)
        right_layout.addWidget(self.rudder_canvas)

        bottom_layout = QHBoxLayout()
        bottom_layout.addLayout(left_layout, 2)
        bottom_layout.addLayout(right_layout, 3)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_bar_layout)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

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
        """Copy text to system clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        # Show a brief confirmation
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
            self.trimtab_angle = max(self.trimtab_angle - 3, -90)
            self.send_trim_tab(from_keyboard=True)
        elif key == Qt.Key_E:
            self.trimtab_angle = min(self.trimtab_angle + 3, 90)
            self.send_trim_tab(from_keyboard=True)
        elif key == Qt.Key_W:
            self.trimtab_angle = 0
            self.send_trim_tab(from_keyboard=True)

    def send_trim_tab(self, from_keyboard=False):
        try:
            angle = self.trimtab_angle if from_keyboard else int(self.trim_input.text())
            if not from_keyboard:
                self.trimtab_angle = angle
            value = convert_to_hex((angle+90) * 1000, 8)
            msg = "cansend can1 002##1" + convert_to_little_endian(value)
            self.cansend_queue.put(msg)
            self.output_display.append(f"[TRIMTAB SENT] {msg}")
            self.trimtab_display.setText(f"Current Trim Tab Angle:   {self.trimtab_angle} degrees")
        except ValueError:
            self.show_error("Invalid angle input for Trim Tab")

    def send_rudder(self, from_keyboard=False):
        try:
            angle = self.rudder_angle if from_keyboard else int(self.rudder_input.text())
            if not from_keyboard:
                self.rudder_angle = angle
            value = convert_to_hex((angle+90) * 1000, 8)
            msg = "cansend can1 001##1" + convert_to_little_endian(value) + "80"
            self.cansend_queue.put(msg)
            self.output_display.append(f"[RUDDER SENT] {msg}")
            self.rudder_display.setText(f"Current Rudder Angle:      {self.rudder_angle} degrees")
            
            # Update rudder values display
            current_actual = "---"
            if self.actual_rudder_history:
                current_actual = f"{self.actual_rudder_history[-1]:6.1f}°"
            else:
                current_actual = "    --"
            self.rudder_values_label.setText(
                f"Rudder Angles:      Set: {self.rudder_angle:4.0f}°       Actual: {current_actual}"
            )
        except ValueError:
            self.show_error("Invalid angle input for Rudder")

    def send_power_off_indefinitely(self):
        msg = "cansend can1 202##10A"
        self.cansend_queue.put(msg)
        self.output_display.append(f"[POWER OFF] {msg}")

    def send_restart_power(self):
        msg = "cansend can1 202##114"
        self.cansend_queue.put(msg)
        self.output_display.append(f"[RESTART POWER] {msg}")

    def update_status(self):
        # Update time independently of CAN messages
        current_time = time.time() - self.time_start
        
        # Process any new CAN messages
        while not self.queue.empty():
            line = self.queue.get()
            self.output_display.append(line)
            
            # Send to separate logging process (non-blocking)
            try:
                self.can_log_queue.put_nowait(line)
            except:
                pass  # Queue full, skip logging this message to avoid blocking

            if line.startswith("can1"):
                parts = line.split()
                if len(parts) > 2:
                    frame_id = parts[1].lower()
                    
                    # Handle 0x206 frame (temperature and voltage data)
                    if frame_id == "206":
                        try:
                            raw_data = line.split(']')[-1].strip().split()
                            parsed = parse_0x206_frame(''.join(raw_data))
                            self.temp_values_label.setText(
                                f"Temperature Values: "
                                f"Temp Battery Pack 2 (Port): {parsed['temp_1']:6.2f}°C   "
                                f"Temp Buck Boost (PDB): {parsed['temp_2']:6.2f}°C   "
                                f"Temp Battery Pack 1 (Starboard): {parsed['temp_3']:6.2f}°C"
                            )
                            self.volt_values_label.setText(
                                f"Voltage Values:     "
                                f"Volt 1: {parsed['volt_1']:5.2f}V   "
                                f"Volt 2: {parsed['volt_2']:5.2f}V   "
                                f"Volt 3: {parsed['volt_3']:5.2f}V   "
                                f"Volt 4: {parsed['volt_4']:5.2f}V"
                            )

                            # Add new data point with current time
                            self.time_history.append(current_time)
                            self.temp1_history.append(parsed['temp_1'])
                            self.temp2_history.append(parsed['temp_2'])
                            self.temp3_history.append(parsed['temp_3'])
                            self.volt1_history.append(parsed['volt_1'])
                            self.volt2_history.append(parsed['volt_2'])
                            self.volt3_history.append(parsed['volt_3'])
                            self.volt4_history.append(parsed['volt_4'])
                            self.set_rudder_history.append(self.rudder_angle)
                            
                            # Fill in missing actual rudder data if needed
                            while len(self.actual_rudder_history) < len(self.time_history):
                                # Use last known value or 0 if no data yet
                                last_rudder = self.actual_rudder_history[-1] if self.actual_rudder_history else 0
                                self.actual_rudder_history.append(last_rudder)

                            # Log current values
                            actual_rudder = self.actual_rudder_history[-1] if self.actual_rudder_history else None
                            self._log_values(
                                parsed['temp_1'], parsed['temp_2'], parsed['temp_3'],
                                parsed['volt_1'], parsed['volt_2'], parsed['volt_3'], parsed['volt_4'],
                                self.rudder_angle, actual_rudder
                            )

                        except Exception as e:
                            self.output_display.append(f"[PARSE ERROR 0x206] {str(e)}")
                    
                    # Handle 0x204 frame (actual rudder angle)
                    elif frame_id == "204":
                        try:
                            raw_data = line.split(']')[-1].strip().split()
                            parsed = parse_0x204_frame(''.join(raw_data))
                            
                            # Update the most recent actual rudder value
                            if self.actual_rudder_history:
                                self.actual_rudder_history[-1] = parsed['actual_rudder_angle']
                            else:
                                # If no history yet, add initial value
                                self.actual_rudder_history.append(parsed['actual_rudder_angle'])
                            
                            # Update rudder display
                            actual_angle = parsed['actual_rudder_angle']
                            self.rudder_values_label.setText(
                                f"Rudder Angles:      Set: {self.rudder_angle:4.0f}°       Actual: {actual_angle:6.1f}°"
                            )

                        except Exception as e:
                            self.output_display.append(f"[PARSE ERROR 0x204] {str(e)}")
        
        # Always update plots every timer cycle (independent of CAN messages)
        if len(self.time_history) > 0:
            # Update all plot data
            self.temp1_line.set_data(self.time_history, self.temp1_history)
            self.temp2_line.set_data(self.time_history, self.temp2_history)
            self.temp3_line.set_data(self.time_history, self.temp3_history)
            
            self.volt1_line.set_data(self.time_history, self.volt1_history)
            self.volt2_line.set_data(self.time_history, self.volt2_history)
            self.volt3_line.set_data(self.time_history, self.volt3_history)
            self.volt4_line.set_data(self.time_history, self.volt4_history)
            
            self.actual_rudder_line.set_data(self.time_history, self.actual_rudder_history)
            self.set_rudder_line.set_data(self.time_history, self.set_rudder_history)
            
            self._update_plot_ranges(current_time)
        else:
            # Even with no data, update the time axis to show progression
            self._update_plot_ranges(current_time)

        # Handle temperature updates with connection status tracking
        if self.temp_pipe.poll():
            connected, value = self.temp_pipe.recv()
            self.temp_label.setText(f"RPI Temp: {value}" if connected else "RPI Temp: --")
            self.status_label.setText("CONNECTED" if connected else "DISCONNECTED")
            self.status_label.setStyleSheet("color: green; font-size: 16px; font-weight: bold;" if connected else "color: red; font-size: 16px; font-weight: bold;")
            self.last_temp_update = time.time()
        else:
            # Check if we haven't received a temperature update in too long (connection lost)
            if time.time() - self.last_temp_update > 5.0:  # 5 second timeout
                self.temp_label.setText("RPI Temp: --")
                self.status_label.setText("DISCONNECTED")
                self.status_label.setStyleSheet("color: red; font-size: 16px; font-weight: bold;")

        # Handle CAN send responses
        while not self.cansend_response_queue.empty():
            cmd, out, err = self.cansend_response_queue.get()
            if err:
                self.output_display.append(f"[ERR] {err.strip()}")
            elif out:
                self.output_display.append(f"[OUT] {out.strip()}")

    def _update_plot_ranges(self, current_time):
        # === Auto-scale and scroll X axis ===
        scroll_window = 60
        if len(self.time_history) > 1:
            # Automatically scroll X axis to show latest data
            self.temp_ax.set_xlim(max(0, current_time - scroll_window), current_time)
            self.volt_ax.set_xlim(max(0, current_time - scroll_window), current_time)
            self.rudder_ax.set_xlim(max(0, current_time - scroll_window), current_time)
        else:
            # For initial data points, auto-scale
            self.temp_ax.relim()
            self.temp_ax.autoscale_view()
            self.volt_ax.relim()
            self.volt_ax.autoscale_view()
            self.rudder_ax.relim()
            self.rudder_ax.autoscale_view()

        # === Auto Y adjustment (Temp) ===
        if self.temp1_history and self.temp2_history and self.temp3_history:
            temp_max = max(self.temp1_history + self.temp2_history + self.temp3_history)
            temp_min = min(self.temp1_history + self.temp2_history + self.temp3_history)
            if temp_max > 75 or temp_min < 10:
                self.temp_ax.set_ylim(min(temp_min - 2, 10), max(temp_max + 2, 75))
            else:
                self.temp_ax.set_ylim(10, 75)

        # === Auto Y adjustment (Volt) ===
        if self.volt1_history and self.volt2_history and self.volt3_history and self.volt4_history:
            volt_max = max(self.volt1_history + self.volt2_history + self.volt3_history + self.volt4_history)
            volt_min = min(self.volt1_history + self.volt2_history + self.volt3_history + self.volt4_history)
            if volt_max > 4 or volt_min < 2.5:
                self.volt_ax.set_ylim(min(volt_min - 0.1, 2.5), max(volt_max + 0.1, 4))
            else:
                self.volt_ax.set_ylim(2.5, 4)

        # === Auto Y adjustment (Rudder) ===
        if self.actual_rudder_history or self.set_rudder_history:
            all_rudder_angles = self.actual_rudder_history + self.set_rudder_history
            if all_rudder_angles:
                rudder_max = max(all_rudder_angles)
                rudder_min = min(all_rudder_angles)
                # Keep some margin around the data
                margin = 5
                self.rudder_ax.set_ylim(max(-50, rudder_min - margin), min(50, rudder_max + margin))

        # Update the canvas to reflect changes
        self.temp_canvas.draw()
        self.volt_canvas.draw()
        self.rudder_canvas.draw()


    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")

    queue = multiprocessing.Queue()
    parent_conn, child_conn = multiprocessing.Pipe()
    cmd_queue = multiprocessing.Queue()
    response_queue = multiprocessing.Queue()
    can_log_queue = multiprocessing.Queue()

    candump_proc = multiprocessing.Process(target=candump_process, args=(queue,))
    temp_proc = multiprocessing.Process(target=temperature_reader, args=(child_conn,))
    cansend_proc = multiprocessing.Process(target=cansend_worker, args=(cmd_queue, response_queue))
    can_logging_proc = multiprocessing.Process(target=can_logging_process, args=(queue, can_log_queue))

    candump_proc.start()
    temp_proc.start()
    cansend_proc.start()
    can_logging_proc.start()

    app = QApplication(sys.argv)
    window = CANWindow(queue, parent_conn, cmd_queue, response_queue, can_log_queue)
    window.show()

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
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