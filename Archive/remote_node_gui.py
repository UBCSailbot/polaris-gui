import sys
import paramiko
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox, QTextEdit
)
from PyQt5.QtCore import QTimer
import multiprocessing
import time

# SSH Credentials
hostname = "raspberrypi.local"
username = "soft"
password = "sailbot"

# Helper Functions
def convert_to_hex(decimal, num_digits):
    return format(decimal, "X").zfill(num_digits)

def convert_to_little_endian(hex_str):
    raw = bytes.fromhex(hex_str)
    return raw[::-1].hex()

def send_command(cmd):
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

# 🧵 Background Candump Listener
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

# 🧠 PyQt5 GUI
class CANWindow(QWidget):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue
        self.setWindowTitle("CANSend + Candump Viewer")
        self.setGeometry(300, 300, 500, 400)
        self.init_ui()

        # Polling timer for candump updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_queue)
        self.timer.start(200)

    def init_ui(self):
        self.trim_input = QLineEdit()
        self.trim_button = QPushButton("Send Trim Tab")
        self.trim_button.clicked.connect(self.send_trim_tab)

        self.rudder_input = QLineEdit()
        self.rudder_button = QPushButton("Send Rudder")
        self.rudder_button.clicked.connect(self.send_rudder)

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)

        layout = QVBoxLayout()
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
            if err: self.output_display.append(f"[ERR] {err}")
        except ValueError:
            self.show_error("Invalid angle input for Trim Tab")

    def send_rudder(self):
        try:
            angle = int(self.rudder_input.text())
            value = convert_to_hex(angle * 1000, 8)
            msg = "cansend can1 200##0" + convert_to_little_endian(value)
            out, err = send_command(msg)
            self.output_display.append(f"[RUDDER SENT] {msg}")
            if err: self.output_display.append(f"[ERR] {err}")
        except ValueError:
            self.show_error("Invalid angle input for Rudder")

    def check_queue(self):
        while not self.queue.empty():
            line = self.queue.get()
            self.output_display.append(line)

    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

# 🎬 Entry Point
if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")  # For compatibility on Windows/macOS

    queue = multiprocessing.Queue()
    candump_proc = multiprocessing.Process(target=candump_process, args=(queue,))
    candump_proc.start()

    app = QApplication(sys.argv)
    window = CANWindow(queue)
    window.show()

    try:
        sys.exit(app.exec_())
    finally:
        candump_proc.terminate()
