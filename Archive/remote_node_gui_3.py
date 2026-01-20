import sys
import paramiko
import multiprocessing
import time

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QTextEdit, QHBoxLayout, QCheckBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap

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

        self.setWindowTitle("Remote Node GUI - POLARIS")
        self.init_ui()

        # Timer to poll candump, temperature, and cansend responses
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(500)

        # Show fullscreen
        # self.showFullScreen()
        self.setGeometry(300, 300, 600, 450)

    

    def init_ui(self):
        
        # Create the logo label
        self.logo_label = QLabel()
        pixmap = QPixmap("D:\OneDrive - UBC\Documents\Sailbot Docs\Remote_node_code\logo.png")
        pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo_label.setPixmap(pixmap)
        self.logo_label.setAlignment(Qt.AlignRight | Qt.AlignTop)  # Align top-right
        
        self.trim_input = QLineEdit()
        self.trim_button = QPushButton("Send Trim Tab")
        self.trim_button.clicked.connect(self.send_trim_tab)

        self.rudder_input = QLineEdit()
        self.rudder_button = QPushButton("Send Rudder")
        self.rudder_button.clicked.connect(self.send_rudder)

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)

        # Temperature and connection status (same as before)
        self.temp_label = QLabel("RPI Temp: --")
        self.temp_label.setAlignment(Qt.AlignCenter)
        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setStyleSheet("color: red")
        self.status_label.setAlignment(Qt.AlignRight)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.temp_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)

        # Left side layout (all your existing widgets)
        left_layout = QVBoxLayout()
        left_layout.addLayout(header_layout)
        left_layout.addWidget(QLabel("Trim Tab Angle:"))
        left_layout.addWidget(self.trim_input)
        left_layout.addWidget(self.trim_button)

        left_layout.addWidget(QLabel("Rudder Angle:"))
        left_layout.addWidget(self.rudder_input)
        left_layout.addWidget(self.rudder_button)

        left_layout.addWidget(QLabel("Candump Output:"))
        left_layout.addWidget(self.output_display)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        # Right layout with logo aligned top-right
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.logo_label)
        right_layout.addStretch()  # Push everything else down

        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        # Main layout: split horizontally
        main_layout = QHBoxLayout()
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 1)

        self.setLayout(main_layout)



    ### ---------- CANFRAMES Sending Functions (ADD MORE HERE) ---------- ###
    def send_trim_tab(self):
        try:
            angle = int(self.trim_input.text())
            value = convert_to_hex(angle * 1000, 8)
            msg = "cansend can1 002##0" + convert_to_little_endian(value)
            self.cansend_queue.put(msg)
            self.output_display.append(f"[TRIM SENT] {msg}")
        except ValueError:
            self.show_error("Invalid angle input for Trim Tab")

    def send_rudder(self):
        try:
            angle = int(self.rudder_input.text())
            value = convert_to_hex(angle * 1000, 8)
            msg = "cansend can1 200##0" + convert_to_little_endian(value)
            self.cansend_queue.put(msg)
            self.output_display.append(f"[RUDDER SENT] {msg}")
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
                self.temp_label.setText(f"RPI Temp: {value}")
                self.status_label.setText("CONNECTED")
                self.status_label.setStyleSheet("color: green")
            else:
                self.temp_label.setText("RPI Temp: --")
                self.status_label.setText("DISCONNECTED")
                self.status_label.setStyleSheet("color: red")

        # Check cansend responses
        while not self.cansend_response_queue.empty():
            cmd, out, err = self.cansend_response_queue.get()
            if err:
                self.output_display.append(f"[ERR] {err.strip()}")
            elif out:
                self.output_display.append(f"[OUT] {out.strip()}")

    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

### ---------- 🎬 Entry Point ---------- ###
if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")  # for compatibility

    queue = multiprocessing.Queue()
    parent_conn, child_conn = multiprocessing.Pipe()
    cmd_queue = multiprocessing.Queue()
    response_queue = multiprocessing.Queue()

    # Start background processes
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
        # Graceful shutdown
        cmd_queue.put("__EXIT__")
        candump_proc.terminate()
        temp_proc.terminate()
        cansend_proc.terminate()
