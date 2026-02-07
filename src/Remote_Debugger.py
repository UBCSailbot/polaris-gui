import sys
import signal
import multiprocessing
import time
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QFont

from DataObject import *
from utility import *

from CAN_processes import (
    candump_process, can_logging_process, cansend_worker, temperature_reader
)
from PyQt_widgets import (
    CANWindowLoggingMixin, CANWindowUpdateMixin, 
    CANWindowControlsMixin, CANWindowUIMixin
)

### ----------  PyQt5 GUI ---------- ###
class CANWindow(
    CANWindowLoggingMixin,
    CANWindowUpdateMixin,
    CANWindowControlsMixin,
    CANWindowUIMixin,
    QWidget):
    
    def __init__(self, queue, temp_pipe, cmd_queue, response_queue, can_log_queue, timestamp):
        super().__init__()
        self.queue = queue
        self.temp_pipe = temp_pipe
        self.cansend_queue = cmd_queue
        self.cansend_response_queue = response_queue
        self.can_log_queue = can_log_queue
        self.timestamp = timestamp

        self.rudder_angle = 0 # degrees
        self.trimtab_angle = 0 # degrees
        self.last_temp_update = time.time()  # Track last temperature update

        self.setWindowTitle("Remote Node GUI - POLARIS")
        self.setGeometry(50, 30, cg.window_width, cg.window_height)
        self.setFocusPolicy(Qt.StrongFocus)

        self.time_start = time.time()
        self.time_history = []

        # Initialize logging
        self._init_logging()

        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(gui_update_freq) # Updates every update_freq milliseconds

    def closeEvent(self, event):
        """Handle window close event to ensure files are properly closed"""
        try:
            if hasattr(self, 'values_csv_file'):
                self.values_csv_file.close()
            print("Log files closed successfully")
        except Exception as e:
            print(f"Error closing log files: {e}")
        event.accept()

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
    
    # def get_current_time(self):
    #     return time.time() - self.time_start

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

    queue = multiprocessing.Queue()
    parent_conn, child_conn = multiprocessing.Pipe()
    cmd_queue = multiprocessing.Queue()
    response_queue = multiprocessing.Queue()
    can_log_queue = multiprocessing.Queue()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    candump_proc = multiprocessing.Process(target=candump_process, args=(queue, False))
    temp_proc = multiprocessing.Process(target=temperature_reader, args=(child_conn,))
    cansend_proc = multiprocessing.Process(target=cansend_worker, args=(cmd_queue, response_queue, can_log_queue))
    can_logging_proc = multiprocessing.Process(target=can_logging_process, args=(queue, can_log_queue, timestamp))

    candump_proc.start()
    temp_proc.start()
    cansend_proc.start()
    can_logging_proc.start()

    signal.signal(signal.SIGINT, key_interrupt_cleanup)

    app = QApplication(sys.argv)
    for obj in all_objs:
        obj.initialize() # create QWidgets
    window = CANWindow(queue, parent_conn, cmd_queue, response_queue, can_log_queue, timestamp)
    window.show()

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt: # note: Ctrl+C doesn't work due to QT loop taking over
        print("\nKeyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        cleanup()
