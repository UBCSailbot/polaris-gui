import sys
import paramiko
import multiprocessing
import time

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QTextEdit, QHBoxLayout
)
from PyQt5.QtCore import QTimer, Qt

# SSH Credentials
hostname = "raspberrypi.local"
username = "soft"
password = "sailbot"

### ---------- 🔧 Utility Functions ---------- ###
def convert_to_hex(decimal, num_digits):
    return format(decimal, "X").zfill(num_digits)

def convert_to_little_endian(hex_str):
    raw = bytes.fromhex(hex_str)
    return raw[::-1].hex()

def send_command(cmd):
    print(f"Sending command: {cmd}") 
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname, username=username, password=password)
        stdin, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode()
        err = stderr.read().decode()
    except Exception as e:
        output = ""
        err = str(e)
    client.close()
    return output, err

### ---------- 🧵 Background CAN Dump Process ---------- ###
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

### ---------- 🌡 Background Temp Reader Process ---------- ###
def temperature_reader(pipe):
    while True:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, username=username, password=password)

            while True:
                stdin, stdout, stderr = ssh.exec_command("cat /sys/class/thermal/thermal_zone0/temp")
                raw = stdout.read().decode().strip()
                if raw:
                    temp = float(raw) / 1000
                    pipe.send((True, f"{temp:.1f}°C"))
                else:
                    pipe.send((False, "ERROR"))
                time.sleep(1)

        except Exception as e:
            pipe.send((False, "DISCONNECTED"))
            time.sleep(1)

### ---------- 🧠 PyQt5 GUI ---------- ###
class CANWindow(QWidget):
    def __init__(self, queue, temp_pipe):
        super().__init__()
        self.queue = queue
        self.temp_pipe = temp_pipe

        self.setWindowTitle("CANSend + Candump Viewer")
        self.setGeometry(300, 300, 600, 450)
        self.init_ui()

        # Timer to poll both candump and temperature pipe
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(500)

    def init_ui(self):
        # Temperature and connection status
        self.temp_label = QLabel("Temp: --")
        self.temp_label.setAlignment(Qt.AlignCenter)
        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setStyleSheet("color: red")
        self.status_label.setAlignment(Qt.AlignRight)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.temp_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)

        # Input/output widgets
        self.trim_input = QLineEdit()
        self.trim_button = QPushButton("Send Trim Tab")
        self.trim_button.clicked.connect(self.send_trim_tab)

        self.rudder_input = QLineEdit()
        self.rudder_button = QPushButton("Send Rudder")
        self.rudder_button.clicked.connect(self.send_rudder)

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addLayout(header_layout)
        layout.addWidget(QLabel("Trim Tab Angle:"))
        layout.addWidget(self.trim_input)
        layout.addWidget(self.trim_button)

        layout.addWidget(QLabel("Rudder Angle:"))
        layout.addWidget(self.rudder_input)
        layout.addWidget(self.rudder_button)

        layout.addWidget(QLabel("Candump Output:"))
        layout.addWidget(self.output_display)

        self.setLayout(layout)

    def send_trim_tab(self):
        try:
            angle = int(self.trim_input.text())
            value = convert_to_hex(angle * 1000, 8)
            msg = "cansend can1 002##0" + convert_to_little_endian(value)
            out, err = send_command(msg)
            self.output_display.append(f"[TRIM SENT] {msg}")
            if err:
                self.output_display.append(f"[ERR] {err}")
        except ValueError:
            self.show_error("Invalid angle input for Trim Tab")

    def send_rudder(self):
        try:
            angle = int(self.rudder_input.text())
            value = convert_to_hex(angle * 1000, 8)
            msg = "cansend can1 200##0" + convert_to_little_endian(value)
            out, err = send_command(msg)
            self.output_display.append(f"[RUDDER SENT] {msg}")
            if err:
                self.output_display.append(f"[ERR] {err}")
        except ValueError:
            self.show_error("Invalid angle input for Rudder")

    def update_status(self):
        # Check candump messages
        while not self.queue.empty():
            line = self.queue.get()
            self.output_display.append(line)

        # Check temp pipe
        if self.temp_pipe.poll():
            connected, value = self.temp_pipe.recv()
            if connected:
                self.temp_label.setText(f"Temp: {value}")
                self.status_label.setText("CONNECTED")
                self.status_label.setStyleSheet("color: green")
            else:
                self.temp_label.setText("Temp: --")
                self.status_label.setText("DISCONNECTED")
                self.status_label.setStyleSheet("color: red")

    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

### ---------- 🎬 Entry Point ---------- ###
if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")  # for compatibility

    queue = multiprocessing.Queue()
    parent_conn, child_conn = multiprocessing.Pipe()

    # Start background processes
    candump_proc = multiprocessing.Process(target=candump_process, args=(queue,))
    temp_proc = multiprocessing.Process(target=temperature_reader, args=(child_conn,))

    candump_proc.start()
    temp_proc.start()

    app = QApplication(sys.argv)
    window = CANWindow(queue, parent_conn)
    window.show()

    try:
        sys.exit(app.exec_())
    finally:
        candump_proc.terminate()
        temp_proc.terminate()
