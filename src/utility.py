from enum import Enum
from DataObject import *
from config import *

# SSH Credentials
hostname = "192.168.0.10"
username = "sailbot"
password = "sailbot"

can_line = "can0"

### ----------  Structs/Enums ---------- ###
class AIS_Attributes(Enum):
    SID = "ship_id"
    LONGITUDE = "longitude"
    LATITUDE = "latitude"
    SOG = "speed_over_gnd"
    SOG_NA = 1023
    COG = "course_over_gnd"
    COG_NA = 3600
    HEADING = "true_heading"
    HEADING_NA = 511
    ROT = "rate_of_turn"
    ROT_NA = -128
    LENGTH = "ship_length"
    LENGTH_NA = 0
    WIDTH = "ship_width"
    WIDTH_NA = 0
    IDX = "index"
    TOTAL = "total_ships"

### ----------  Utility Functions ---------- ###
# Note that these functions are designed to work with positive numbers
def convert_to_hex(decimal, num_bytes):
    return format(decimal, "X").zfill(2 * num_bytes)

def convert_to_little_endian(hex_str):
    raw = bytes.fromhex(hex_str)
    return raw[::-1].hex()

def convert_from_little_endian_str(hex_str):
    raw = bytes.fromhex(hex_str)
    big_endian = raw[::-1].hex()
    return int(big_endian, 16)

def val(raw_bytes, s, e, div):
    return int.from_bytes(raw_bytes[s:e], 'little') / div


# NOTE: Currently returns True/False, but parsing functions don't do anything with this return value as of yet - it just prints it as a notice
# NOTE: May add functionality to also log if a given data point is out of range (ie. is sus)
def range_check(quantity, num, minn = None, maxn = None):
    '''Prints error and returns False if given num is not within [min, max] (inclusive); if None is given for either max or min, that boundary is not checked.'''
    if (maxn is not None and num > maxn): 
        print(f"ERROR - {quantity} {num} is higher than expected range")
        return False
    if (minn is not None and num < minn):
        print(f"ERROR - {quantity} {num} is lower than expected range")
        return False
    return True


### ----------  Parsing Data Frames  ---------- ###

def parse_0x206_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 24:
        raise ValueError("Incorrect data length (num bytes): ID 0x206")

    val = lambda s, e, div: int.from_bytes(raw_bytes[s:e], 'little') / div
    return {
        volt2_obj.name: val(0, 2, 1000.0),
        temp1_obj.name: val(2, 4, 100.0),
        volt3_obj.name: val(4, 6, 1000.0),
        temp2_obj.name: val(6, 8, 100.0),
        temp3_obj.name: val(8, 10, 100.0),
        volt4_obj.name: val(10, 12, 1000.0),
        volt1_obj.name: val(12, 14, 1000.0),
        mppt_hp_obj.name: val(14, 16, 1000.0),
        mppt_hs_obj.name: val(16, 18, 1000.0),
        mppt_sp_obj.name: val(18, 20, 1000.0),
        mppt_ss_obj.name: val(20, 22, 1000.0)
    }

def parse_0x204_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 16:
        raise ValueError("Incorrect data length (num bytes): ID 0x204")
    
    val = lambda s, e, div: int.from_bytes(raw_bytes[s:e], 'little') / div
    # print(f"derivative_obj: {(val(12, 14, 1.0) - 300) / 100.0}")
    # print(f"spd_over_gnd_obj: {val(14, 16, 100.0)}")
    return {
        actual_rudder_obj.name: val(0, 2, 100.0) - 90,
        imu_roll_obj.name: val(2, 4, 100.0) - 180,
        imu_pitch_obj.name: val(4, 6, 100.0) - 180,
        imu_heading_obj.name: val(6, 8, 100.0),
        set_rudder_obj.name: val(8, 10, 100.0) - 90,
        integral_obj.name: val(10, 12, 1.0) - 30000,
        derivative_obj.name: (val(12, 14, 1.0) - 300) / 100.0,
        spd_over_gnd_obj.name: val(14, 16, 1000.0)
    }
    

def actual_rudder_parsing_fn(parsed_dict):
    return parsed_dict[actual_rudder_obj.name]

def set_rudder_parsing_fn(parsed_dict):
    return parsed_dict[set_rudder_obj.name]

def parse_0x041_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 4:
        raise ValueError("Incorrect data length (num bytes): ID 0x041")
    
    val = lambda s, e, div: int.from_bytes(raw_bytes[s:e], 'little') / div
    return {
        data_wind_dir_obj.name: val(0, 2, 1.0),
        data_wind_spd_obj.name: val(2, 4, 10.0)
    }

# Salinity data frame
def parse_0x120_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 4:
        raise ValueError("Incorrect data length (num bytes): ID 0x120")
    
    # Conductivity in µS/cm * 1000
    # raw = int.from_bytes(raw_bytes, "little") # is raw_bytes[0:2] really necessary?
    raw = convert_from_little_endian_str(data_hex)
    actual = raw / (1000)

    if (actual < 1 and actual != 0 or actual > 550000):
        print(f"[ERROR]: sal data parsed as {actual}")    
        print(f"data_hex = {data_hex}")
        print(f"raw = {raw}")
        raise ValueError()
    
    if (actual < 100): actual = round(actual, 2)
    elif (actual < 1000): actual = round(actual, 1)
    elif (actual < 10000): actual = round(actual)
    elif (actual < 100000): actual = round(actual, -1)
    return {"sal": actual} 

# Salinity parsing function
def sal_parsing_fn(data_hex):
    '''
    Parses data for salinity 0x12X frame\n
    In particular, this function also calculates rounding since 
    accurate rounding depends on the magnitude of the value recorded
    '''
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 4:
        raise ValueError("Incorrect data length (num bytes): ID 0x120")
    
    # Conductivity in µS/cm * 1000
    raw = convert_from_little_endian_str(data_hex)
    actual = raw / (1000)

    if (actual < 1 and actual != 0 or actual > 550000):
        print(f"[ERROR]: sal data parsed as {actual}")    
        print(f"data_hex = {data_hex}")
        print(f"raw = {raw}")
        raise ValueError()
    
    if (actual < 100): actual = round(actual, 2)
    elif (actual < 1000): actual = round(actual, 1)
    elif (actual < 10000): actual = round(actual)
    elif (actual < 100000): actual = round(actual, -1)
    return actual

# pH data frame
def parse_0x110_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 2:
        raise ValueError(f"Incorrect data length (num bytes): ID 0x110\nExpecting: 2 bytes, Received: {len(raw_bytes)}")
    
    # pH is in format of pH * 1000
    raw = convert_from_little_endian_str(data_hex)
    actual = raw / 1000

    if (actual < 1 and actual != 0 or actual > 14):
        print(f"[ERROR]: pH data parsed as {actual}")  
        print(f"data_hex = {data_hex}")
        print(f"raw = {raw}")
        raise ValueError()  
    
    return {"pH": round(actual, 2)} 

def pH_parsing_fn(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 2:
        raise ValueError(f"Incorrect data length (num bytes): ID 0x110\nExpecting: 2 bytes, Received: {len(raw_bytes)}")
    
    # pH is in format of pH * 1000
    raw = convert_from_little_endian_str(data_hex)
    actual = raw / 1000

    if (actual < 1 and actual != 0 or actual > 14):
        print(f"[ERROR]: pH data parsed as {actual}")  
        print(f"data_hex = {data_hex}")
        print(f"raw = {raw}")
        raise ValueError()  
    
    return actual


# temp data frame
def parse_0x100_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 3:
        raise ValueError("Incorrect data length (num bytes): ID 0x100")
    
    # temp is in format of temp * 1000
    # raw = int.from_bytes(raw_bytes, "little") # is raw_bytes[0:2] really necessary?
    # actual = raw / 1000
    raw = convert_from_little_endian_str(data_hex)
    actual = (raw / 1000.0) - 273.15

    if (actual < -130 and actual != 0 or actual > 1350):
        print(f"[ERROR]: temp_sensor data parsed as {actual}")  
        print(f"data_hex = {data_hex}")
        print(f"raw = {raw}")
        raise ValueError()  
    
    return {"temp_sensor": round(actual, 3)}

def temp_sensor_parsing_fn(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 3:
        raise ValueError("Incorrect data length (num bytes): ID 0x100")
    
    # temp is in format of temp * 1000
    raw = convert_from_little_endian_str(data_hex)
    actual = (raw / 1000.0) - 273.15

    if (actual < -130 and actual != 0 or actual > 1350):
        print(f"[ERROR]: temp_sensor data parsed as {actual}")  
        print(f"data_hex = {data_hex}")
        print(f"raw = {raw}")
        raise ValueError()  
    
    return actual

def parse_0x070_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) != 20:
        raise ValueError("Incorrect data length (num bytes): ID 0x070")
    
    # temp is in format of temp * 1000
    val = lambda s, e, div: int.from_bytes(raw_bytes[s:e], 'little') / div

    parsed = {
        # actual_rudder_obj.name: val(0, 2, 100.0) - 90,
        gps_lat_obj.name: val(0, 4, 1000000) - 90,
        gps_lon_obj.name: val(4, 8, 1000000) - 90,
        spd_over_gnd_obj.name: val(16, 20, 1000)
    }

    range_check(parsed[gps_lat_obj.name], -90, 90)
    range_check(parsed[gps_lon_obj.name], -180, 180)
    range_check(parsed[spd_over_gnd_obj.name], 0)

    return parsed

def parse_0x060_frame(data_hex):
    raw_bytes = bytes.fromhex(data_hex)
    if len(raw_bytes) < 25: # candump pads the frame to make it 32 bytes
        print("number of raw_bytes = ", len(raw_bytes))
        raise ValueError("Incorrect data length (num bytes): ID 0x060")
    
    # temp is in format of temp * 1000

    parsed = {
        # actual_rudder_obj.name: val(0, 2, 100.0) - 90,
        AIS_Attributes.SID: val(raw_bytes, 0, 4, 1),
        AIS_Attributes.LATITUDE: val(raw_bytes, 4, 8, 1000000) - 90,
        AIS_Attributes.LONGITUDE: val(raw_bytes, 8, 12, 1000000) - 180,
        AIS_Attributes.SOG: val(raw_bytes, 12, 14, 10) if (val(raw_bytes, 12, 14, 10) != AIS_Attributes.SOG_NA) else None, 
        AIS_Attributes.COG: val(raw_bytes, 14, 16, 10) if (val(raw_bytes, 14, 16, 10) != AIS_Attributes.COG_NA) else None, 
        AIS_Attributes.HEADING: val(raw_bytes, 16, 18, 10) if (val(raw_bytes, 16, 18, 10) != AIS_Attributes.HEADING_NA) else None, 
        AIS_Attributes.ROT: (val(raw_bytes, 18, 19, 1) - 128) if ((val(raw_bytes, 18, 19, 1) - 128) != AIS_Attributes.ROT_NA) else None, 
        AIS_Attributes.LENGTH: val(raw_bytes, 19, 21, 1) if (val(raw_bytes, 19, 21, 1) != AIS_Attributes.LENGTH_NA) else None, 
        AIS_Attributes.WIDTH: val(raw_bytes, 21, 23, 1) if (val(raw_bytes, 21, 23, 1) != AIS_Attributes.WIDTH_NA) else None, 
        AIS_Attributes.IDX: val(raw_bytes, 23, 24, 1),
        AIS_Attributes.TOTAL: val(raw_bytes, 24, 25, 1)
    }

    range_check(AIS_Attributes.LATITUDE, parsed[AIS_Attributes.LATITUDE], -90, 90)
    range_check(AIS_Attributes.LONGITUDE, parsed[AIS_Attributes.LONGITUDE], -180, 180)
    range_check(AIS_Attributes.SOG, parsed[AIS_Attributes.SOG], 0)

    return parsed

def make_pretty(cmd):
    '''
    Helper function for putting cansend commands into the same format as candump received messages\n
    '''
    try:
        frame_id = cmd[12:15]
        data = cmd[18:]
        data_length = int(len(data) / 2)
        padding = "0" if (data_length < 10) else ""
        data_nice = ""
        for i in range(len(data)):
            data_nice += data[i]
            if ((i % 2) == 1):
                data_nice += " "
        msg = can_line + "  " + frame_id + "  [" + padding + str(data_length) + "]  " + data_nice
    except Exception as e:
        print(f"ERROR - Command not logged: {str(e)}")
    
    return msg

### ---------- Data Objects ---------- ###

# Battery Temps
pdb_temp_graph_obj = GraphObject("Temperature", cg.graph_y, "°C", cg.graph_y_units, 0, 127.0)
temp1_obj = DataObject("Temp1", 2, "°C", None, line_colour="r", graph=pdb_temp_graph_obj)
temp2_obj = DataObject("Temp2", 2, "°C", None, line_colour="g", graph=pdb_temp_graph_obj)
temp3_obj = DataObject("Temp3", 2, "°C", None, line_colour="y", graph=pdb_temp_graph_obj)

# Cell voltages
pdb_volt_graph_obj = GraphObject("Cell Voltages", cg.graph_y, "V", cg.graph_y_units, 0, 5)
volt1_obj = DataObject("Volt1", 2, "V", None, line_colour="b", graph=pdb_volt_graph_obj)
volt2_obj = DataObject("Volt2", 2, "V", None, line_colour="c", graph=pdb_volt_graph_obj)
volt3_obj = DataObject("Volt3", 2, "V", None, line_colour="m", graph=pdb_volt_graph_obj)
volt4_obj = DataObject("Volt4", 2, "V", None, line_colour="orange", graph=pdb_volt_graph_obj)

# MPPT currents
mppt_current_graph_obj = GraphObject("MPPT Current", cg.graph_y, "A", cg.graph_y_units, 0, 5)
mppt_hp_obj = DataObject("MPPT_curr_hull_port", 2, "A", None, line_colour="c", graph=mppt_current_graph_obj)
mppt_sp_obj = DataObject("MPPT_curr_hull_star", 2, "A", None, line_colour="purple", graph=mppt_current_graph_obj)
mppt_hs_obj = DataObject("MPPT_curr_sail_port", 2, "A", None, line_colour="g", graph=mppt_current_graph_obj)
mppt_ss_obj = DataObject("MPPT_curr_sail_star", 2, "A", None, line_colour="y", graph=mppt_current_graph_obj)

# Rudder angles (set & actual)
rudder_graph = GraphObject("Rudder Angles", cg.graph_y, "°", cg.graph_y_units, -90, 90)
actual_rudder_obj = DataObject("Actual_rdr_deg", 2, "°", None, line_colour="r", graph=rudder_graph) # NOTE: graph parsing function changed to None here - potential for bug/error
set_rudder_obj = DataObject("Set_rdr_deg", 2, "°", None, line_dashed=True, line_colour="b", graph=rudder_graph) # NOTE: graph parsing function changed to None here

# Speed over ground (from debug frame 0x204)
spd_over_gnd_graph_obj = GraphObject("Speed Over Ground", cg.graph_y, "km/h", cg.graph_y_units, 0, 20)
spd_over_gnd_obj = DataObject("Speed_over_gnd", 3, "km/h", None, line_colour='brown', graph=spd_over_gnd_graph_obj)

# Headings (IMU & Desired)
headings_graph_obj = GraphObject("IMU & Desired Headings", cg.graph_y, "°", cg.graph_y_units, 0, 360)
imu_heading_obj = DataObject("IMU_heading", 3, "°", None, line_colour="r", graph=headings_graph_obj)
desired_heading_obj = DataObject("Desired_heading", 3, "°", None, line_dashed=True, line_colour="b", graph=headings_graph_obj)

# IMU roll & pitch
imu_roll_pitch_graph_obj = GraphObject("IMU Roll & Pitch", cg.graph_y, "°", cg.graph_y_units, 0, 360)
imu_roll_obj = DataObject("IMU_roll", 2, "°", None, line_colour="g", graph=imu_roll_pitch_graph_obj)
imu_pitch_obj = DataObject("IMU_pitch", 2, "°", None, line_colour="brown", graph=imu_roll_pitch_graph_obj)

# Integral + Derivative
int_der_graph_obj = GraphObject("IMU Integral & Derivative", cg.graph_y, None, cg.graph_y_units, 0, 100)
integral_obj = DataObject("IMU_integral", 2, None, None, line_colour="m", graph=int_der_graph_obj)
derivative_obj = DataObject("IMU_derivative", 2, None, None, line_colour="pink", graph=int_der_graph_obj)

# Data Wind Sensor
data_wind_spd_graph_obj = GraphObject("Data_Wind Speed", cg.graph_y, "knots", cg.graph_y_units, 0, 20)
data_wind_spd_obj = DataObject("Data_Wind_spd", 0, "knots", None, line_colour="turquoise", graph=data_wind_spd_graph_obj)
data_wind_dir_graph_obj = GraphObject("Data_Wind Direction", cg.graph_y, "°", cg.graph_y_units, 0, 360)
data_wind_dir_obj = DataObject("Data_Wind_dir", 0, "°", None, line_colour="orange", graph=data_wind_dir_graph_obj)

data_wind_objs = [data_wind_spd_obj, data_wind_dir_obj]

# GPS
gps_lat_obj = DataObject("gps_lat", 4, "DD", None, graph=None)
gps_lon_obj = DataObject("gps_lon", 4, "DD", None, graph=None)

# AIS
# polaris_pen = pg.mkPen(color='r', width=5) # set point border color (red)
polaris_brush = pg.mkBrush(color='r')
# other_pen = pg.mkPen(color='b', width=1)
other_brush = pg.mkBrush(color='b')

position_graph_obj = GraphObject("Longitude", "Latitude", "DD", "DD", -90, 90, "Ship Positions") # note: this graph's x_range should definitely not be updated with the rest
ais_obj = AISObject("Ship Positions", 4, "DD", None, other_brush, [att.value for att in AIS_Attributes], polaris_brush = polaris_brush, graph = position_graph_obj)

# General sensors (pH, water temp, salinity)
pH_graph_obj = GraphObject("pH", cg.graph_y, None, cg.graph_y_units, 0, 14)
pH_obj = DataObject("pH", 1, None, pH_parsing_fn, line_colour="r", graph=pH_graph_obj)

temp_sensor_graph_obj = GraphObject("Water Temp", cg.graph_y, "°C", cg.graph_y_units, 0, 1400)
temp_sensor_obj = DataObject("Water_Temp", 3, "°C", temp_sensor_parsing_fn, line_colour="b", graph=temp_sensor_graph_obj)

sal_graph_obj = GraphObject("Salinity", cg.graph_y, "µS/cm", cg.graph_y_units, 0, 100000)
sal_obj = DataObject("Salinity", None, "µS/cm", sal_parsing_fn, line_colour='g', graph=sal_graph_obj)

# Lists (typically organized by frame)
pdb_objs = [temp1_obj, temp2_obj , temp3_obj, volt1_obj, volt2_obj, volt3_obj, volt4_obj, mppt_hp_obj, mppt_hs_obj, mppt_sp_obj, mppt_ss_obj]
rudder_objs = [actual_rudder_obj, set_rudder_obj, spd_over_gnd_obj, imu_roll_obj, imu_pitch_obj, integral_obj, derivative_obj, imu_heading_obj] # all objects with data from 0x204 frame (rudder -> mainframe)
data_objs = [pH_obj, temp_sensor_obj, sal_obj]
gps_objs = [gps_lon_obj, gps_lat_obj]
# Only data_objs are logged together in the values csv file; they are all graphed vs. Time and have their values trimmed accordingly over time
data_objs = gps_objs + data_objs + data_wind_objs + rudder_objs + pdb_objs 
all_objs = data_objs.copy()
all_objs.append(ais_obj) # ais is logged and updated differently since it is not a vs. Time graph

# Testing val
# if __name__ == "__main__":
#     lst = [0x12, 0x34, 0x56, 0x78, 0x90, 0xab]
#     arr = bytearray(lst)
#     print(hex(int(val(arr, 0, 2, 1))))
#     print(hex(int(val(arr, 2, 6, 1))))