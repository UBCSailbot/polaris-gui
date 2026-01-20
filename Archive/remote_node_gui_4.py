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

        self.rudder_angle = 90
        self.trimtab_angle = 90

        self.setWindowTitle("Remote Node GUI - POLARIS")
        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(500)

        self.setGeometry(300, 300, 700, 500)

    def init_ui(self):
        self.logo_label = QLabel()
        pixmap = QPixmap("D:/OneDrive - UBC/Documents/Sailbot Docs/Remote_node_code/logo.png")
        pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo_label.setPixmap(pixmap)
        self.logo_label.setAlignment(Qt.AlignRight | Qt.AlignTop)

        self.keyboard_mode = QCheckBox("Keyboard Mode (A/D/S for Rudder, Q/E/W for Trim Tab)")
        self.keyboard_mode.stateChanged.connect(self.toggle_keyboard_mode)

        self.rudder_input = QLineEdit()
        self.rudder_button = QPushButton("Send Rudder")
        self.rudder_button.clicked.connect(self.send_rudder)

        self.trim_input = QLineEdit()
        self.trim_button = QPushButton("Send Trim Tab")
        self.trim_button.clicked.connect(self.send_trim_tab)

        self.rudder_label = QLabel("Current Rudder Angle: 90")
        self.trim_label = QLabel("Current Trim Tab Angle: 90")

        self.instructions = QLabel(
            "Key Bindings:\n"
            "A/D: Rudder -/+ 5\nS: Center Rudder\n"
            "Q/E: Trim Tab -/+ 5\nW: Center Trim Tab"
        )

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)

        self.temp_label = QLabel("RPI Temp: --")
        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setStyleSheet("color: red")

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.temp_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)

        layout = QVBoxLayout()
        layout.addLayout(header_layout)
        layout.addWidget(self.logo_label)
        layout.addWidget(self.keyboard_mode)
        layout.addWidget(self.rudder_label)
        layout.addWidget(self.trim_label)
        layout.addWidget(self.instructions)
        layout.addWidget(QLabel("Rudder Angle:"))
        layout.addWidget(self.rudder_input)
        layout.addWidget(self.rudder_button)
        layout.addWidget(QLabel("Trim Tab Angle:"))
        layout.addWidget(self.trim_input)
        layout.addWidget(self.trim_button)
        layout.addWidget(QLabel("Candump Output:"))
        layout.addWidget(self.output_display)

        self.setLayout(layout)

    def toggle_keyboard_mode(self):
        enabled = not self.keyboard_mode.isChecked()
        self.rudder_input.setEnabled(enabled)
        self.trim_input.setEnabled(enabled)
        self.rudder_button.setEnabled(enabled)
        self.trim_button.setEnabled(enabled)

    def keyPressEvent(self, event):
        if not self.keyboard_mode.isChecked():
            return

        key = event.key()
        if key == Qt.Key_A:
            self.rudder_angle = max(0, self.rudder_angle - 5)
        elif key == Qt.Key_D:
            self.rudder_angle = min(180, self.rudder_angle + 5)
        elif key == Qt.Key_S:
            self.rudder_angle = 90
        elif key == Qt.Key_Q:
            self.trimtab_angle = max(0, self.trimtab_angle - 5)
        elif key == Qt.Key_E:
            self.trimtab_angle = min(180, self.trimtab_angle + 5)
        elif key == Qt.Key_W:
            self.trimtab_angle = 90
        else:
            return

        self.update_angle_labels()
        self.send_angle("rudder", self.rudder_angle)
        self.send_angle("trimtab", self.trimtab_angle)

    def update_angle_labels(self):
        self.rudder_label.setText(f"Current Rudder Angle: {self.rudder_angle}")
        self.trim_label.setText(f"Current Trim Tab Angle: {self.trimtab_angle}")

    def send_trim_tab(self):
        try:
            angle = int(self.trim_input.text())
            self.trimtab_angle = angle
            self.update_angle_labels()
            self.send_angle("trimtab", angle)
        except ValueError:
            self.show_error("Invalid angle input for Trim Tab")

    def send_rudder(self):
        try:
            angle = int(self.rudder_input.text())
            self.rudder_angle = angle
            self.update_angle_labels()
            self.send_angle("rudder", angle)
        except ValueError:
            self.show_error("Invalid angle input for Rudder")

    def send_angle(self, actuator, angle):
        value = convert_to_hex(angle * 1000, 8)
        hex_val = convert_to_little_endian(value)
        msg = f"cansend can1 {'200' if actuator == 'rudder' else '002'}##0{hex_val}"
        self.cansend_queue.put(msg)
        self.output_display.append(f"[{actuator.upper()} SENT] {msg}")

    def update_status(self):
        while not self.queue.empty():
            self.output_display.append(self.queue.get())

        if self.temp_pipe.poll():
            connected, value = self.temp_pipe.recv()
            self.temp_label.setText(f"RPI Temp: {value}" if connected else "RPI Temp: --")
            self.status_label.setText("CONNECTED" if connected else "DISCONNECTED")
            self.status_label.setStyleSheet("color: green" if connected else "color: red")

        while not self.cansend_response_queue.empty():
            cmd, out, err = self.cansend_response_queue.get()
            if err:
                self.output_display.append(f"[ERR] {err.strip()}")
            elif out:
                self.output_display.append(f"[OUT] {out.strip()}")

    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

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