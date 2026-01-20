import sys
import paramiko
import multiprocessing
import time

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QTextEdit, QHBoxLayout, QCheckBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QFont

# SSH Credentials
hostname = "raspberrypi.local"
username = "soft"
password = "sailbot"

### ----------  Utility Functions ---------- ###
def convert_to_hex(decimal, num_digits):
    return format(decimal, "X").zfill(num_digits)

def convert_to_little_endian(hex_str):
    raw = bytes.fromhex(hex_str)
    return raw[::-1].hex()

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
            except Exception as e:
                pipe.send((False, "ERROR"))
            time.sleep(1)
    except Exception as e:
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

### ----------  PyQt5 GUI ---------- ###
class CANWindow(QWidget):
    def __init__(self, queue, temp_pipe, cmd_queue, response_queue):
        super().__init__()
        self.queue = queue
        self.temp_pipe = temp_pipe
        self.cansend_queue = cmd_queue
        self.cansend_response_queue = response_queue

        self.rudder_angle = 0 #degrees
        self.trimtab_angle = 0 #degrees

        self.setWindowTitle("Remote Node GUI - POLARIS")
        self.setGeometry(300, 300, 600, 450)
        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(500)

        self.setGeometry(300, 300, 1200, 600)
        self.setFocusPolicy(Qt.StrongFocus)
    
    
    def init_ui(self):
        # === Top Bar ===
        self.logo_label = QLabel()
        pixmap = QPixmap("D:\OneDrive - UBC\Documents\Sailbot Docs\Remote_node_code\logo.png") # Adjust the path to your logo image"
        pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo_label.setPixmap(pixmap)

        self.temp_label = QLabel("RPI Temp: --")
        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setStyleSheet("color: red")

        top_bar_layout = QHBoxLayout()
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.logo_label)
        top_bar_layout.addSpacing(10)
        top_bar_layout.addWidget(self.temp_label)
        top_bar_layout.addSpacing(10)
        top_bar_layout.addWidget(self.status_label)
        top_bar_layout.addStretch()

        # === Widgets ===
        self.keyboard_checkbox = QCheckBox("Keyboard Mode")
        self.keyboard_checkbox.toggled.connect(self.toggle_keyboard_mode)

        self.instructions1_display = QLabel("For Rudder    (+/- 3 degrees): A / S / D (Left / Center / Right)")
        self.instructions2_display = QLabel("For Trim Tab (+/- 3 degrees): Q / E / W (Left / Center / Right)")

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

        # === Power Control Section ===
        self.power_checkbox = QCheckBox("Enable Power Control")
        self.power_checkbox.stateChanged.connect(self.toggle_power_buttons)

        self.power_off_btn = QPushButton("Power Off Indefinitely")
        self.power_off_btn.setEnabled(False)
        self.power_off_btn.clicked.connect(self.send_power_off_indefinitely)

        self.restart_btn = QPushButton("Restart Power After 20s")
        self.restart_btn.setEnabled(False)
        self.restart_btn.clicked.connect(self.send_restart_power)
        
        red_button_style = """
                QPushButton {
                    background-color: red;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover:enabled {
                    background-color: yellow;
                    color: black;
                }
                QPushButton:disabled {
                    background-color: yellow;  /* dark red when disabled */
                    color: black;
                }
            """
        
        self.power_off_btn.setStyleSheet(red_button_style)
        self.restart_btn.setStyleSheet(red_button_style)

        # === Left Layout (Control Panel) ===
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(10, 10, 10, 10)
        # Remove top_bar_main from here because it's moved above
        left_layout.addWidget(self.keyboard_checkbox)
        left_layout.addSpacing(10)
        left_layout.addWidget(self.instructions1_display)
        left_layout.addWidget(self.instructions2_display)
        left_layout.addSpacing(10)
        left_layout.addWidget(self.rudder_display)
        left_layout.addWidget(self.trimtab_display)
        left_layout.addSpacing(10)
        left_layout.addWidget(QLabel("Rudder Angle:"))
        left_layout.addWidget(self.rudder_input)
        left_layout.addWidget(self.rudder_button)
        left_layout.addWidget(QLabel("Trim Tab Angle:"))
        left_layout.addWidget(self.trim_input)
        left_layout.addWidget(self.trim_button)
        left_layout.addSpacing(10)
        left_layout.addWidget(QLabel("Candump Output:"))
        left_layout.addWidget(self.output_display)

        # === Power control widgets ===
        left_layout.addWidget(self.power_checkbox)
        left_layout.addWidget(self.power_off_btn)
        left_layout.addWidget(self.restart_btn)
        left_layout.addSpacing(10)

        # === Right Placeholder Layout ===
        right_layout = QVBoxLayout()
        right_layout.addStretch()

        # === Bottom Layout: left and right side by side ===
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.addLayout(left_layout, 3)
        bottom_layout.addLayout(right_layout, 2)

        # === Main Layout: vertical, top bar on top, then bottom layout ===
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        main_layout.addLayout(top_bar_layout)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

    def toggle_keyboard_mode(self, checked):
        self.rudder_input.setDisabled(checked)
        self.rudder_button.setDisabled(checked)
        self.trim_input.setDisabled(checked)
        self.trim_button.setDisabled(checked)

    def toggle_power_buttons(self, state):
        enabled = state == Qt.Checked
        self.power_off_btn.setEnabled(enabled)
        self.restart_btn.setEnabled(enabled)

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

    def send_trim_tab(self, from_keyboard=False):
        try:
            angle = self.trimtab_angle if from_keyboard else int(self.trim_input.text())
            if not from_keyboard:
                self.trimtab_angle = angle
            value = convert_to_hex((angle+90) * 1000, 8)

            msg = "cansend can1 002##0" + convert_to_little_endian(value)
            self.cansend_queue.put(msg)
            self.output_display.append(f"[TRIMTAB SENT] {msg}")
            self.trimtab_display.setText(f"Current Trim Tab Angle:    {self.trimtab_angle} degrees")
        except ValueError:
            self.show_error("Invalid angle input for Trim Tab")

    def send_rudder(self, from_keyboard=False):
        try:
            angle = self.rudder_angle if from_keyboard else int(self.rudder_input.text())
            if not from_keyboard:
                self.rudder_angle = angle
            value = convert_to_hex((angle+90) * 1000, 8)
            msg = "cansend can1 200##0" + convert_to_little_endian(value)
            self.cansend_queue.put(msg)
            self.output_display.append(f"[RUDDER SENT] {msg}")
            self.rudder_display.setText(f"Current Rudder Angle:     {self.rudder_angle} degrees")
        except ValueError:
            self.show_error("Invalid angle input for Rudder")
    
    def send_power_off_indefinitely(self):
        msg = "cansend can1 202##00A"
        self.cansend_queue.put(msg)
        self.output_display.append(f"[POWER OFF] {msg}")

    def send_restart_power(self):
        msg = "cansend can1 202##014"
        self.cansend_queue.put(msg)
        self.output_display.append(f"[RESTART POWER] {msg}")
    
    def update_status(self):
        while not self.queue.empty():
            line = self.queue.get()
            self.output_display.append(line)

        if self.temp_pipe.poll():
            connected, value = self.temp_pipe.recv()
            if connected:
                self.temp_label.setText(f"RPI Temp: {value}")
                self.status_label.setText("CONNECTED")
                self.status_label.setStyleSheet("color: green")
            else:
                self.temp_label.setText("RPI Temp: --")
                self.status_label.setText("DISCONNECTED")
                self.status_label.setStyleSheet("color: red")

        while not self.cansend_response_queue.empty():
            cmd, out, err = self.cansend_response_queue.get()
            if err:
                self.output_display.append(f"[ERR] {err.strip()}")
            elif out:
                self.output_display.append(f"[OUT] {out.strip()}")

    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

### ---------- Entry Point ---------- ###
if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")

    queue = multiprocessing.Queue()
    parent_conn, child_conn = multiprocessing.Pipe()
    cmd_queue = multiprocessing.Queue()
    response_queue = multiprocessing.Queue()

    candump_proc = multiprocessing.Process(target=candump_process, args=(queue,))
    temp_proc = multiprocessing.Process(target=temperature_reader, args=(child_conn,))
    cansend_proc = multiprocessing.Process(target=cansend_worker, args=(cmd_queue, response_queue))

    candump_proc.start()
    temp_proc.start()
    cansend_proc.start()

    app = QApplication(sys.argv)
    window = CANWindow(queue, parent_conn, cmd_queue, response_queue)
    window.show()

    try:
        sys.exit(app.exec_())
    finally:
        cmd_queue.put("__EXIT__")
        candump_proc.terminate()
        temp_proc.terminate()
        cansend_proc.terminate()
