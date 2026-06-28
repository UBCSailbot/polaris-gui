import multiprocessing
import os
import signal
import sys
import time
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox

from config import (
    gui_update_freq,
    max_trimtab_angle,
    min_trimtab_angle,
    window_height,
    window_width,
)
from utils import all_objs, heartbeat_modules
from widgets import (
    CANWindowControlsMixin,
    CANWindowLoggingMixin,
    CANWindowUIMixin,
    CANWindowUpdateMixin,
    JoystickMixin,
)
from workers import (
    can_logging_process,
    candump_process,
    cansend_worker,
    temperature_reader,
)

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def _bootstrap_qt_runtime():
    if os.environ.get("POLARIS_QT_BOOTSTRAPPED") == "1":
        return

    qt_lib_dir = os.path.join(
        sys.prefix,
        "lib",
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        "site-packages",
        "PyQt5",
        "Qt5",
        "lib",
    )
    if not os.path.isdir(qt_lib_dir):
        return

    current = os.environ.get("LD_LIBRARY_PATH", "")
    paths = current.split(":") if current else []
    if qt_lib_dir in paths:
        return

    env = os.environ.copy()
    env["POLARIS_QT_BOOTSTRAPPED"] = "1"
    env["LD_LIBRARY_PATH"] = f"{qt_lib_dir}:{current}" if current else qt_lib_dir
    os.execvpe(sys.executable, [sys.executable, *sys.argv], env)


_bootstrap_qt_runtime()


### ----------  PyQt5 GUI ---------- ###
class CANWindow(
    CANWindowLoggingMixin,
    CANWindowUpdateMixin,
    CANWindowControlsMixin,
    CANWindowUIMixin,
    JoystickMixin,
    QWidget,
):
    def __init__(
        self, queue, temp_pipe, cmd_queue, response_queue, can_log_queue, timestamp
    ):
        super().__init__()
        self.queue = queue
        self.temp_pipe = temp_pipe
        self.cansend_queue = cmd_queue
        self.cansend_response_queue = response_queue
        self.can_log_queue = can_log_queue

        self.rudder_angle = 0  # degrees
        self.trimtab_angle = 0  # degrees
        self.last_temp_update = time.time()  # Track last temperature update

        self.setWindowTitle("Remote Node GUI - POLARIS")
        self.setGeometry(50, 30, window_width, window_height)
        self.setFocusPolicy(Qt.StrongFocus)

        self.time_start = time.time()
        self.time_history = []

        # Initialize logging
        self._init_logging(timestamp)

        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(gui_update_freq)  # Updates every update_freq milliseconds

    # NOTE: Below functions are all in CANWindowLoggingMixin
    # def _init_logging(self, timestamp):
    # def _log_values(self):

    def closeEvent(self, event):
        """Handle window close event to ensure files are properly closed"""
        try:
            if hasattr(self, "values_csv_file"):
                self.values_csv_file.close()
            print("Log files closed successfully")
        except Exception as e:
            print(f"Error closing log files: {e}")
        event.accept()

    # NOTE: Functions moved to CAN_window_UI.py:
    # def init_ui()
    # def set_manual_steer(self, checked):
    # def toggle_keyboard_mode(self, checked):
    # def toggle_emergency_buttons(self, state):
    # def copy_to_clipboard(self, text):
    # def update_pid_param_dropdown(self, text: str) -> None: # NOTE: This is new
    # def getObjFromLabel(self, dropdown_label) -> DataObject:
    # def setGraph(self, name: str, spot: int, dropdowns: list[QComboBox]) -> None:

    def keyPressEvent(self, event):
        if not self.keyboard_checkbox.isChecked():
            return

        key = event.key()
        if key == Qt.Key_A:
            self.rudder_angle = min(self.rudder_angle + 3, 45)
            self.send_rudder(from_keyboard=True)
            # NOTE: now that send_rudder() takes a set_angle,
            # can probably use that instead of
            # setting self.rudder_angle and from_keyboard=True
        elif key == Qt.Key_D:
            self.rudder_angle = max(self.rudder_angle - 3, -45)
            self.send_rudder(from_keyboard=True)
        elif key == Qt.Key_S:
            self.rudder_angle = 0
            self.send_rudder(from_keyboard=True)
        elif key == Qt.Key_Q:
            self.trimtab_angle = max(self.trimtab_angle - 3, min_trimtab_angle)
            self.send_trim_tab(from_keyboard=True)
        elif key == Qt.Key_E:
            self.trimtab_angle = min(self.trimtab_angle + 3, max_trimtab_angle)
            self.send_trim_tab(from_keyboard=True)
        elif key == Qt.Key_W:
            self.trimtab_angle = 0
            self.send_trim_tab(from_keyboard=True)

    # NOTE: Functions moved to CAN_window_controls.py
    # def can_send(self, frame_id, data, display_msg):
    # def send_trim_tab(self, from_keyboard: bool = False, set_angle: float = None):
    # def send_desired_heading(self):
    # def send_rudder(self, from_keyboard=False, set_angle: float = None):
    # def send_power_off_indefinitely(self):
    # def send_restart_power(self):
    # def send_pid(self):
    # def send_pid_param(self):

    # NOTE: moved to CAN_window_update.py
    # def update_status(self):
    # def _update_plot_ranges(self, current_time):

    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)
        print(f"Error: {msg}")


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
    current_time = datetime.now()
    timestamp = current_time.strftime("%Y%m%d_%H%M%S")
    current_time = current_time.timestamp()  # convert to seconds since epoch

    candump_proc = multiprocessing.Process(
        target=candump_process, args=(queue, False)
    )  # Testing mode set to false when run from main
    temp_proc = multiprocessing.Process(target=temperature_reader, args=(child_conn,))
    cansend_proc = multiprocessing.Process(
        target=cansend_worker, args=(cmd_queue, response_queue, can_log_queue)
    )
    can_logging_proc = multiprocessing.Process(
        target=can_logging_process, args=(queue, can_log_queue, timestamp)
    )

    candump_proc.start()
    temp_proc.start()
    cansend_proc.start()
    can_logging_proc.start()

    # Cleanup (CTRL + C) initialization
    signal.signal(signal.SIGINT, key_interrupt_cleanup)

    app = QApplication(sys.argv)
    for obj in all_objs:
        obj.initialize(timestamp)  # create QWidgets
    for mod in heartbeat_modules:
        mod.init_time(current_time)
    window = CANWindow(
        queue, parent_conn, cmd_queue, response_queue, can_log_queue, timestamp
    )
    window.initialize_joystick()  # Joystick initialization
    window.show()

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:  # note: Ctrl+C doesn't work due to QT loop taking over
        print("\nKeyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        cleanup()
