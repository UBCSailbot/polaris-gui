import time
from datetime import datetime

from config import (
    latitude_range,
    longitude_range,
    max_rudder_angle,
    max_trimtab_angle,
    min_trimtab_angle,
    rudder_axis,
    rudder_latch,
    scroll_window,
    trimtab_axis,
    trimtab_latch,
)
from utils import (
    AIS_Attributes,
    ais_obj,
    all_objs,
    can_line,
    data_objs,
    data_wind_objs,
    desired_heading_obj,
    gps_lat_obj,
    gps_lon_obj,
    gps_objs,
    heartbeat_modules,
    manual_input_objs,
    parse_0x001_frame,
    parse_0x060_frame,
    parse_0x070_frame,
    parse_0x204_frame,
    parse_0x206_frame,
    parse_sail_wind_sensor_frame,
    parse_wind_sensor_frame,
    pdb_hb_module,
    pdb_objs,
    pH_obj,
    rudder_objs,
    rudr_hb_module,
    sail_hb_module,
    sail_wind_objs,
    sal_obj,
    sense_hb_module,
    set_rudder_obj,
    temp_sensor_obj    
)


# Window update functions
class CANWindowUpdateMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
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
                    # TODO: Also probably raw_data can be taken outside of the cases for deduplication
                    match frame_id:
                        case "001": # Sent frame to rudder
                            # print("main_heading 001 frame received!")
                            raw_data = line.split(']')[-1].strip().split()
                            parsed = parse_0x001_frame(''.join(raw_data))
                            if parsed['steering_selection_bit']:
                                set_rudder_obj.parse_frame(current_time, None, parsed)
                            else: 
                                desired_heading_obj.parse_frame(current_time, None, parsed)
                            pass

                        case "002": # Sent frame to trim tab
                            pass
                        case "040": # Sail_Wind frame
                            try:
                                raw_data = line.split(']')[-1].strip().split()
                                parsed = parse_sail_wind_sensor_frame(''.join(raw_data))
                                for obj in sail_wind_objs:
                                    obj.parse_frame(current_time, None, parsed)
                                    obj.update_label()
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x040] {str(e)}")
                        case "041": # Data_Wind frame
                            try:
                                raw_data = line.split(']')[-1].strip().split()
                                parsed = parse_wind_sensor_frame(''.join(raw_data))
                                for obj in data_wind_objs:
                                    obj.parse_frame(current_time, None, parsed)
                                    obj.update_label()
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x041] {str(e)}")
                        case "060": # AIS frame
                            try:
                                raw_data = line.split(']')[-1].strip().split()
                                parsed = parse_0x060_frame(''.join(raw_data), current_time)
                                if parsed[AIS_Attributes.TOTAL] != 0: # if ship frame is valid
                                    ais_obj.add_frame(parsed[AIS_Attributes.LONGITUDE], parsed[AIS_Attributes.LATITUDE], parsed[AIS_Attributes.SID], parsed, AIS_Attributes.LONGITUDE)
                                    if parsed[AIS_Attributes.IDX] == (parsed[AIS_Attributes.TOTAL] - 1):
                                        ais_obj.log_data(datetime.now().isoformat(), time.time() - self.time_start)
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x060] {str(e)}")

                        case "070": # GPS frame
                                try:
                                    raw_data = line.split(']')[-1].strip().split()
                                    parsed = parse_0x070_frame(''.join(raw_data))
                                    for obj in gps_objs:
                                        obj.parse_frame(current_time, None, parsed)
                                        obj.update_label()

                                    if ais_obj.graph_obj.isVisible(): # graph POLARIS's current position if graph is visible
                                        lon = gps_lon_obj.get_current()[1]
                                        lat = gps_lat_obj.get_current()[1]
                                        ais_obj.update_polaris_pos(lon, lat)
                                        ais_obj.update_range(lon - longitude_range, lon + longitude_range, lat - latitude_range, lat + latitude_range)
                                        
                                
                                except Exception as e:
                                    self.output_display.append(f"[PARSE ERROR 0x070] {str(e)}")

                        case "100": # water_temp sensor frame
                            try:
                                temp_sensor_obj.parse_frame(current_time, line)
                                temp_sensor_obj.update_label()
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x100] {str(e)}")
                       
                        case "110": # pH sensor frame
                            try:               
                                pH_obj.parse_frame(current_time, line)
                                pH_obj.update_label()
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x110] {str(e)}")

                        case "120": # salinity sensor frame
                            try: 
                                sal_obj.parse_frame(current_time, line)
                                sal_obj.update_label()                                            
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x120] {str(e)}") 

                        case "130": # PDB Heartbeat frame
                            pdb_hb_module.set_alive(current_time)
                        case "131":
                            rudr_hb_module.set_alive(current_time)
                        case "132": # SAIL Heartbeat frame
                            sail_hb_module.set_alive(current_time)
                        case "133":
                            sense_hb_module.set_alive(current_time)

                        case "204": # Handle 0x204 frame (actual rudder angle)

                            try:
                                raw_data = line.split(']')[-1].strip().split()
                                parsed = parse_0x204_frame(''.join(raw_data))
                                for obj in rudder_objs:
                                    obj.parse_frame(current_time, None, parsed)
                                    obj.update_label()
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x204] {str(e)}")
                           
                        case "206":
                            try:
                                raw_data = line.split(']')[-1].strip().split()
                                parsed = parse_0x206_frame(''.join(raw_data))
                                for obj in pdb_objs:
                                    obj.parse_frame(current_time, None, parsed)                           
                                    obj.update_label()
                            except Exception as e:
                                self.output_display.append(f"[PARSE ERROR 0x206] {str(e)}")
        
                        case _:
                            print(f"Frame id not recognized: {frame_id}")

                # Log current values
                if (new_msg_to_log and (len(self.time_history) > 0)):
                    # actual_rudder = self.actual_rudder_history[-1] if self.actual_rudder_history else None
                    self._log_values()

        # trim values no longer being graphed
        for obj in all_objs:
            obj.update_data(current_time, scroll_window)

        # Update heartbeat displays
        for mod in heartbeat_modules:
            mod.update_status(current_time)
                        
        # Always update plots and continuously graphed objs (those allowing manual input) every timer cycle (independent of CAN messages) # TODO: Modify this - batch plot updates?
        if len(self.time_history) > 0:
            for obj in manual_input_objs:
                if obj.needs_update(current_time): 
                    obj.add_datapoint(current_time, obj.get_current()[1])
            self._update_plot_ranges(current_time)

        # Handle temperature updates with connection status tracking
        if self.temp_pipe.poll():
            connected, value = self.temp_pipe.recv()
            self.temp_label.setText(f"RPI Temp: {value}" if connected else "RPI Temp: --")
            self.status_label.setText("CONNECTED" if connected else "DISCONNECTED")
            self.status_label.setStyleSheet("color: green" if connected else "color: red")
            self.last_temp_update = time.time()
        else:
            # Check if we haven't received a temperature update in too long (connection lost)
            if time.time() - self.last_temp_update > 5.0:  # 5 second timeout
                self.temp_label.setText("RPI Temp: --")
                self.status_label.setText("DISCONNECTED")
                self.status_label.setStyleSheet("color: red")

        # Handle CAN send responses
        while not self.cansend_response_queue.empty():
            print()
            cmd, out, err = self.cansend_response_queue.get()
            if err:
                self.output_display.append(f"[ERR] {err.strip()}")
            elif out:
                self.output_display.append(f"[OUT] {out.strip()}")

        # Handle joystick updates 
        if (self.get_joystick_enabled()):
            moved, pos = self.joystick_moved(rudder_axis, rudder_latch)
            if moved: self.send_rudder(set_angle = max_rudder_angle * pos)
            moved, pos = self.joystick_moved(trimtab_axis, trimtab_latch)
            if moved:
                trimtab_angle = (
                    max_trimtab_angle * pos if pos >= 0
                    else abs(min_trimtab_angle) * pos
                )
                self.send_trim_tab(set_angle=trimtab_angle)

    def _update_plot_ranges(self, current_time):
        # === Auto-scale and scroll X axis ===
        if len(self.time_history) > 1:
            for obj in data_objs:
                if obj.graph_obj is not None:
                    obj.graph_obj.update_xlim(
                        max(0, current_time - scroll_window), current_time
                    )
