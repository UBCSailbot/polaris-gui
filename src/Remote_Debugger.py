import sys
import signal
import multiprocessing
import time
import csv
import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QTextEdit, QHBoxLayout, QCheckBox, QGridLayout, QComboBox,
    QSizePolicy
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QFont

from DataObject import *
from utility import *

from CAN_processes import *
from PyQt_widgets import *

### ----------  PyQt5 GUI ---------- ###
class CANWindow(
    CANWindowLoggingMixin,
    CANWindowUpdateMixin,
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

    def init_ui(self):   
          
        top_bar_layout = init_top_bar(self)
        checkbox_layout = init_checkbox(self)

        # === Left Panel ===

        self.instructions1_display = QLabel("For Rudder    (+/- 3 degrees): A / S / D  (Left / Center / Right)")
        self.instructions2_display = QLabel("For Trim Tab (+/- 3 degrees): Q / W / E (Left / Center / Right)")

        self.rudder_display = QLabel("Current Set Rudder Angle:  0 degrees")
        self.trimtab_display = QLabel("Current Trim Tab Angle:   0 degrees")

        self.desired_heading_input_group = init_desired_heading_input_group(self)
        self.rudder_input_group = init_rudder_input_group(self)
        self.trim_input_group = init_trim_input_group(self)
        
        self.pid_layout = init_pid_layout(self)
        emergency_controls_layout = init_emergency_controls(self)

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setMinimumWidth(350)

        # Separate terminal output display
        self.terminal_output_display = QTextEdit()
        self.terminal_output_display.setReadOnly(True)

        # SSH Instructions for CAN and system control
        self.ssh_instructions_label = QLabel(
            "SSH Terminal Instructions:\n"
            "1. Open separate terminal/PowerShell\n"
            "2. ssh sailbot@192.168.0.10\n"
            "3. Password: sailbot\n"
            "\nUse buttons below to copy commands:"
        )
        self.ssh_instructions_label.setStyleSheet(styles.instructions_lable)

        # Define commands with labels
        commands = [
            ("SSH Connect", "ssh sailbot@192.168.0.10"),
            ("CAN0 Down", "sudo ip link set can0 down"),
            ("CAN0 Up", "sudo ip link set can0 up type can bitrate 500000 dbitrate 1000000 fd on"),
            ("Check CAN Status", "ip link show can0"),
            ("View System Logs", "dmesg | tail"),
            ("System Info", "uname -a")
        ]
        
        # Create a grid layout for command buttons
        self.commands_grid = init_commands_grid(self, commands)   
         
        input_layout = init_input_layout(self)
        left_layout = init_left_layout(self, top_bar_layout, checkbox_layout, input_layout, emergency_controls_layout)
        
        # === Right Panel ===
        labels_layout = init_labels_layout()
        right_layout = init_right_layout(self)

        # Combine everything        
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
        """Copy text to system clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        # Show a brief confirmation
        self.output_display.append(f"[COPIED] {text}")
            
    def getGraphObjFromXName(self, name):
        for obj in all_objs:
            if ((obj.graph_obj is not None) and (obj.graph_obj.dropdown_label == name)):
                return obj.graph_obj
            
    def setGraph(self, name, spot, dropdowns):
        '''
        Shows given graph at spot\n
        name = DataObj.graph_obj.dropdown_label\n
        spot = 0, 1, 2 (top, mid, bot)\n
        '''
        newGraphObj = self.getGraphObjFromXName(name) # get graph to put in spot
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

    # def setGraph(self, name, spot, dropdowns):
    #     '''
    #     Shows given graph at spot\n
    #     name = DataObj.graph_obj.x_name\n
    #     spot = 0, 1, 2 (top, mid, bot)\n
    #     '''
    #     newGraphObj = self.getGraphObjFromXName(name) # get graph to put in spot
    #     if (newGraphObj.x_name == self.visibleGraphObjs[spot].x_name):
    #         return # do nothing
    #     if newGraphObj in self.visibleGraphObjs: # if graph to put in spot is already visible
    #         # don't allow the switch to happen - set dropdown text back to original and print error message
    #         print("[ERR] Graph is already visible")
    #         dropdowns[spot].setCurrentText(self.visibleGraphObjs[spot].x_name) # switch text back to original
    #     else: 
    #         self.right_graphs_layout.removeWidget(self.visibleGraphObjs[spot].graph) # remove graph currently in spot
    #         self.visibleGraphObjs[spot].hide()
    #         self.right_graphs_layout.addWidget(newGraphObj.graph, spot, 0)
    #         newGraphObj.show()
    #         self.visibleGraphObjs[spot] = newGraphObj  

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
            print(f"ERROR - Command not logged: {str(e)}")

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

    def send_rudder(self, from_keyboard=False):
        try:
            angle = self.rudder_angle if from_keyboard else int(self.rudder_input.text())
            if not from_keyboard:
                self.rudder_angle = angle
            if (angle < -90):
                raise ValueError("Invalid angle input for Rudder")
            data = convert_to_little_endian(convert_to_hex((angle+90) * 1000, 4))
            status_byte = "80" # a = 1, b = 0, c = 0
            self.can_send("001", data + status_byte, "RUDDER SENT")
            self.rudder_display.setText(f"Current Set Rudder Angle:  {self.rudder_angle} degrees")
            
            set_rudder_obj.add_datapoint(time.time() - self.time_start, angle)
            set_rudder_obj.update_label()

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
