import time

from utility import *


class CANWindowControlsMixin:
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
        except ValueError as e:
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
