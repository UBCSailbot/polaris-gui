import time

from utils import *


# Window update functions
class CANWindowUpdateMixin:
    def update_status(self):
        # Update time independently of CAN messages
        current_time = time.time() - self.time_start

        # Process any new CAN messages
        while not self.queue.empty():
            line = self.queue.get()
            # self.output_display.append(line)

            new_msg_to_log = False

            # print(f"line parsed = {line}")

            # Send to separate logging process (non-blocking)
            # TODO: modify the nowait to ensure logging
            try:
                self.can_log_queue.put_nowait(line)
            except:
                print(f"line was not logged!")

            if line.startswith(can_line):
                new_msg_to_log = True
                parts = line.split()
                if len(parts) > 2:
                    frame_id = parts[1].lower()
                    self.time_history.append(current_time)

                    # TODO: Use a dictionary with frame id:function - just runs the function associated with frame id?
                    # There's definitely some abstraction that can be done here
                    match frame_id:
                        case "041":  # Data_Wind frame
                            try:
                                raw_data = line.split("]")[-1].strip().split()
                                parsed = parse_0x041_frame("".join(raw_data))
                                for obj in data_wind_objs:
                                    obj.parse_frame(current_time, None, parsed)
                                    obj.update_label()
                            except Exception as e:
                                self.output_display.append(
                                    f"[PARSE ERROR 0x041] {str(e)}"
                                )
                        case "060":  # AIS frame
                            try:
                                raw_data = line.split("]")[-1].strip().split()
                                parsed = parse_0x060_frame("".join(raw_data))
                                ais_obj.add_frame(
                                    parsed[AIS_Attributes.LONGITUDE],
                                    parsed[AIS_Attributes.LATITUDE],
                                    parsed,
                                )
                                # If this is the last frame in the batch
                                if (
                                    parsed[AIS_Attributes.IDX]
                                    == parsed[AIS_Attributes.TOTAL]
                                ):
                                    ais_obj.log_data()
                                    # if graph is visible
                                    if ais_obj.graph_obj.isVisible():
                                        ais_obj.update_line_data()
                                    ais_obj.switch_current()

                            except Exception as e:
                                self.output_display.append(
                                    f"[PARSE ERROR 0x060] {str(e)}"
                                )
                        case "070":  # GPS frame
                            try:
                                raw_data = line.split("]")[-1].strip().split()
                                parsed = parse_0x070_frame("".join(raw_data))
                                for obj in gps_objs:
                                    obj.parse_frame(current_time, None, parsed)
                                    obj.update_label()
                            except Exception as e:
                                self.output_display.append(
                                    f"[PARSE ERROR 0x070] {str(e)}"
                                )

                        case "100":  # water_temp sensor frame
                            try:
                                temp_sensor_obj.parse_frame(current_time, line)
                                temp_sensor_obj.update_label()
                            except Exception as e:
                                self.output_display.append(
                                    f"[PARSE ERROR 0x100] {str(e)}"
                                )

                        case "110":  # pH sensor frame
                            try:
                                pH_obj.parse_frame(current_time, line)
                                pH_obj.update_label()
                            except Exception as e:
                                self.output_display.append(
                                    f"[PARSE ERROR 0x110] {str(e)}"
                                )

                        case "120":  # salinity sensor frame
                            try:
                                sal_obj.parse_frame(current_time, line)
                                sal_obj.update_label()
                            except Exception as e:
                                self.output_display.append(
                                    f"[PARSE ERROR 0x120] {str(e)}"
                                )

                        case "204":  # Handle 0x204 frame (actual rudder angle)

                            try:
                                raw_data = line.split("]")[-1].strip().split()
                                parsed = parse_0x204_frame("".join(raw_data))
                                for obj in rudder_objs:
                                    obj.parse_frame(current_time, None, parsed)
                                    obj.update_label()
                            except Exception as e:
                                self.output_display.append(
                                    f"[PARSE ERROR 0x204] {str(e)}"
                                )

                        case "206":
                            try:
                                raw_data = line.split("]")[-1].strip().split()
                                parsed = parse_0x206_frame("".join(raw_data))
                                for obj in pdb_objs:
                                    obj.parse_frame(current_time, None, parsed)
                                    obj.update_label()
                            except Exception as e:
                                self.output_display.append(
                                    f"[PARSE ERROR 0x206] {str(e)}"
                                )

                        case _:
                            print(f"Frame id not recognized: {frame_id}")

                # Log current values
                if new_msg_to_log and (len(self.time_history) > 0):
                    # actual_rudder = self.actual_rudder_history[-1] if self.actual_rudder_history else None
                    self._log_values()

        # trim values no longer being graphed
        for obj in data_objs:
            obj.update_data(current_time, scroll_window)

        # Always update plots every timer cycle (independent of CAN messages) # TODO: Modify this - batch plot updates?
        if len(self.time_history) > 0:
            self._update_plot_ranges(current_time)

        # Add new data point to desired_heading graph every 5 secs - since it's not regularly updated with CAN messages
        # current_dheading = desired_heading_obj.get_current()
        # if (current_dheading[1] is not None and ((current_time - current_dheading[0]) > 5)): # if not graphed since 5 seconds ago
        #     desired_heading_obj.add_datapoint(current_time, current_dheading[1])

        # Handle temperature updates with connection status tracking
        if self.temp_pipe.poll():
            connected, value = self.temp_pipe.recv()
            self.temp_label.setText(
                f"RPI Temp: {value}" if connected else "RPI Temp: --"
            )
            self.status_label.setText("CONNECTED" if connected else "DISCONNECTED")
            self.status_label.setStyleSheet(
                "color: green" if connected else "color: red"
            )
            self.last_temp_update = time.time()
        else:
            # Check if we haven't received a temperature update in too long (connection lost)
            if time.time() - self.last_temp_update > 5.0:  # 5 second timeout
                self.temp_label.setText("RPI Temp: --")
                self.status_label.setText("DISCONNECTED")
                self.status_label.setStyleSheet("color: red")

        # Handle CAN send responses
        while not self.cansend_response_queue.empty():
            cmd, out, err = self.cansend_response_queue.get()
            if err:
                self.output_display.append(f"[ERR] {err.strip()}")
            elif out:
                self.output_display.append(f"[OUT] {out.strip()}")

    def _update_plot_ranges(self, current_time):
        # === Auto-scale and scroll X axis ===
        if len(self.time_history) > 1:
            for obj in data_objs:
                if obj.graph_obj is not None:
                    obj.graph_obj.update_xlim(
                        max(0, current_time - scroll_window), current_time
                    )
