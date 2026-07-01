import time

from config import can_line, max_trimtab_angle, min_trimtab_angle, pid_params
from utils import (
    convert_float_to_binary32hex,
    convert_to_hex,
    convert_to_little_endian,
    set_rudder_obj,
)


# CAN send functions
class CANWindowControlsMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def can_send(self, frame_id, data, display_msg):
        """
        Helper function for sending CAN messages\n
        frame_id: full frame id of message as a string WITHOUT 0x prefix (eg. 001, 041)\n
        data: hex string of message in little endian (assumes valid data)\n
        display_msg: Message to be outputted on GUI CAN_DUMP display
        """
        try:
            # TODO: is it "##0" or "##1"?
            msg = "cansend " + can_line + " " + frame_id + "##0" + data
            self.cansend_queue.put(msg)
            self.output_display.append(f"[{display_msg}] {msg}")
        except Exception as e:
            print(f"ERROR - Command not sent: {str(e)}")

    def send_trim_tab(self, from_keyboard: bool = False, set_angle: float = None):
        try:
            # angle = self.trimtab_angle if from_keyboard else int(self.trim_input.text())
            # if not from_keyboard:
            #     self.trimtab_angle = angle

            if from_keyboard:
                angle = self.trimtab_angle
            else:
                angle = (
                    round(set_angle, 3)
                    if set_angle is not None
                    else round(float(self.trim_input.text()), 3)
                )
                self.trimtab_angle = angle

            if angle < min_trimtab_angle or angle > max_trimtab_angle:
                raise ValueError(
                    f"Invalid angle input for Trim Tab: must be between {min_trimtab_angle} and {max_trimtab_angle} degrees"
                )

            value = convert_to_hex(int((angle + 90) * 1000), 4)
            self.can_send("002", convert_to_little_endian(value), "TRIMTAB SENT")
            self.trimtab_display.setText(
                f"Current Trim Tab Angle: {self.trimtab_angle} degrees"
            )
        except ValueError as e:
            print(f"ValueError: {e}")
            self.show_error(f"ValueError: {e}")

    def send_desired_heading(self):
        try:
            heading = float(self.desired_heading_input.text())
            if (heading < 0) or (heading > 360):
                raise ValueError
            # Note: We lose precision of decimal places if too many are entered: only keeps 3 dp
            data = convert_to_little_endian(convert_to_hex(int(heading * 1000), 4))
            status_byte = "00"  # a = 0, b = 0
            self.can_send("001", data + status_byte, "HEADING SENT")
            # TODO: Note that the below should only be necessary if no CAN frames are sent
            # desired_heading_obj.add_datapoint(time.time() - self.time_start, heading)
            # desired_heading_obj.update_label() # No explicit label with the other objects for this item; already have Heading Set Angle
        except ValueError as e:
            self.show_error(f"Invalid angle input for desired heading: {e}")
        except Exception as exp:
            print(f"Exception thrown from send_desired_heading: {exp}")
            self.show_error(f"Exception thrown from send_desired_heading: {exp}")

    def send_rudder(self, from_keyboard=False, set_angle: float = None):
        """set_angle is a given angle"""
        try:
            if from_keyboard:
                angle = self.rudder_angle
            elif set_angle is not None:
                angle = round(set_angle, 3)
            else:
                angle = int(self.rudder_input.text())

            if not from_keyboard:
                self.rudder_angle = (
                    angle  # TODO: Why is this here? Keep self.rudder_angle up-to-date?
                )

            if angle < -90:
                raise ValueError("ERR - Rudder Angle input < -90")

            data = convert_to_little_endian(convert_to_hex(int((angle + 90) * 1000), 4))

            status_byte = "80"  # a = 1, b = 0, c = 0
            self.can_send("001", data + status_byte, "RUDDER SENT")
            self.rudder_display.setText(
                f"Current Set Rudder Angle:  {self.rudder_angle} degrees"
            )

            # print("line 709")

            # TODO: similar to desired_heading, the below should only be necessary if we're not parsing the corresponding sent CAN frame
            #       which I think I'm not doing right now and should definitely do at some point
            set_rudder_obj.add_datapoint(time.time() - self.time_start, angle)
            set_rudder_obj.update_label()
            # print("Set rudder current = ", set_rudder_obj.get_current()[1])
            # print(f"at the end w/o error")

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
            p = convert_to_little_endian(
                convert_to_hex(int(float(self.p_input.text()) * 1000000), 4)
            )
            i = convert_to_little_endian(
                convert_to_hex(int(float(self.i_input.text()) * 1000000), 4)
            )
            d = convert_to_little_endian(
                convert_to_hex(int(float(self.d_input.text()) * 1000000), 4)
            )
            can_data = p + i + d
            self.can_send("200", can_data, "SEND PID")

        except ValueError as v:
            self.show_error(f"Invalid input for p, i, or d: {v}")

        except Exception as e:
            print(f"Exception thrown from send_pid: {e}")
            self.show_error(f"Exception thrown from send_pid: {e}")

    def send_pid_param(self):
        try:
            status_byte = "00"
            param_index = convert_to_hex(
                pid_params.index(self.pid_param_dropdown.currentText()), 1
            )
            value = convert_to_little_endian(
                convert_float_to_binary32hex(float(self.pid_param_input.text()))
            )
            can_data = status_byte + param_index + value
            self.can_send("210", can_data, "SEND PID PARAM")
        except ValueError as v:
            self.show_error(f"Invalid input for PID parameter value: {v}")

        except Exception as e:
            self.show_error(f"Exception thrown from send_pid_param: {e}")

        return


# TODO: these send can messages don't need to be part of the class at all really - refactor them out into their own class (like a SendCanFrameObject?)
