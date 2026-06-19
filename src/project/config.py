# ==== General Setup ====
can_line = "can0"

# SSH Credentials
hostname = "192.168.0.10"
username = "sailbot"
password = "sailbot"

# ==== Window Size ====
window_height = 450
window_width = 1350

# update_freq = 100 # frequency at which CAN messages are collected & processed - TODO: implement separation of CAN msg processing and gui updating
gui_update_freq = 50 # frequency of UI update in millis

# ==== Live Values ====
value_label_min_width = 300
value_label_max_height = 200

value_style = """
            color: black;
            font-size: 18px;
            font-weight: bold;
            font-family: 'Courier New', monospace;
            padding: 2px;
            background-color: #f0f0f0;
            border: 2px solid #cccccc;
            border-radius: 3px;
            margin: 2px;
        """

# sets label background to orange: indicates that value is out of normal range
value_warning = """
            color: black;
            font-size: 18px;
            font-weight: bold;
            font-family: 'Courier New', monospace;
            padding: 2px;
            background-color: #ff7f00;
            border: 2px solid #cccccc;
            border-radius: 3px;
            margin: 2px;
        """

input_label_style = "font-weight: bold;"

# ==== Heartbeat UI Style ====
heartbeat_timeout = 10 # Timeout for CAN frame (in secs)
heartbeat_status_good_text = "ALIVE"
heartbeat_status_bad_text = "NOT RESPONDING"

heartbeat_label_style = """
            color: black;
            font-size: 16px;
            padding: 2px;
            margin: 2px;
        """

heartbeat_status_good_style = "color: green;"
heartbeat_status_bad_style = "color: red;"

# ==== Dropdown font ====
d_font_type = "Comic Sans" # hahaha
d_font_size = 14

# ==== Graph config ====
linewidth = 2
graph_bg = "w"
graph_title_style = ["black", "10pt"]
graph_label_style = {
    "color": "black",
    "font-size": "15px"
}

graph_y = "Time"
graph_y_units = "s"
graph_min_width = 250
graph_min_height = 300
scroll_window = 60 # in seconds

LAST_UPDATED = "time_since_last_update" # tracks amount of time since a datapoint was updated 
data_timeout = 5 * 60 # amt of time (in seconds) before data gets removed
plrs_path_data_timeout = 30 # 2 * 60 # amt of time (in seconds) before POLARIS path data is deleted (for PID tuning)

# Set range of ships centered around POLARIS +- <lat/lon>_range on AIS graph
latitude_range = 0.1 # in decimal degrees
longitude_range = 0.1 # in decimal degrees

# ==== Heading & PID Tuning ====
ARROW_TIME_SCALING_ENABLED = True # If True, how often heading arrows appear is time-based; if False, it is distance-based 
min_time_between_arrows = 1 # Minimum time between heading arrows appearance (in seconds)
min_dist_between_arrows = 15.0 # heading arrows only appear on points at least min_dist_between_arrows metres away from the last recorded point
# NOTE: below is NOT implemented in PIDObject.should_create_arrow
# max_time_between_arrows = 0.1 # if time since last arrow placed is more than this time, put an arrow no matter the distance

# Arrow Styles 
h_arrow_headLen = 20
h_arrow_tailLen = 40
h_arrow_tailWidth = 7
h_arrow_headWidth = 7
h_arrow_pen = {'color': 'black', 'width': 2}
h_arrow_desired_brush = 'blue'
h_arrow_actual_brush = 'red'

# Heading names for reference
desired_heading_arrow_name = "desired_heading_arrow"
actual_heading_arrow_name = "actual_heading_arrow"

# PID Tunable Parameters
pid_dropdown_font_type = "Sans serif"
pid_dropdown_font_size = 9

pid_params = [
    "STANDARD_KP",
    "STANDARD_KI",
    "STANDARD_KD",
    "STANDARD_INTEGRAL_MAX",
    "STANDARD_INTEGRAL_DECAY",
    "STANDARD_DERIVATIVE_FILTER",
    "STANDARD_ERROR_THRESHOLD",
    "STANDARD_HEADING_TOLERANCE",
    "STANDARD_ANG_VEL_TOLERANCE", # 9th element (index = 8)

    "TACKING_KP",
    "TACKING_KI",
    "TACKING_KD",
    "TACKING_INTEGRAL_MAX",
    "TACKING_INTEGRAL_DECAY",
    "TACKING_DERIVATIVE_FILTER",
    "TACKING_ERROR_THRESHOLD",
    "TACKING_HEADING_TOLERANCE",
    "TACKING_ANG_VEL_TOLERANCE", # 18th element

    "GYBING_KP",
    "GYBING_KI",
    "GYBING_KD",
    "GYBING_INTEGRAL_MAX",
    "GYBING_INTEGRAL_DECAY",
    "GYBING_DERIVATIVE_FILTER",
    "GYBING_ERROR_THRESHOLD",
    "GYBING_HEADING_TOLERANCE",
    "GYBING_ANG_VEL_TOLERANCE", # 27th element

    "LOW_WIND_KP",
    "LOW_WIND_KI",
    "LOW_WIND_KD",
    "LOW_WIND_INTEGRAL_MAX",
    "LOW_WIND_INTEGRAL_DECAY",
    "LOW_WIND_DERIVATIVE_FILTER",
    "LOW_WIND_ERROR_THRESHOLD",
    "LOW_WIND_HEADING_TOLERANCE",
    "LOW_WIND_ANG_VEL_TOLERANCE", # 36th element

    "VELOCITY_FACTOR",
    "HEEL_FACTOR",
    "TACK_TIME",
    "GYBE_TIME",
    "TACK_HEADING_PADDING",
    "GYBE_HEADING_PADDING",
    "AVERAGE_WINDOW_SIZE",

    "OUTPUT_MAX",
    "OUTPUT_MIN",
    "UPWIND_IRONS_ANGLE",
    "DOWNWIND_IRONS_ANGLE",
    "LOW_WIND_THRESHOLD",

    "STATE_LOW_WIND_THRESHOLD",
    "TACKING_LIN_THRESHOLD",
    "TACKING_ROT_THRESHOLD",
    "GYBING_LIN_THRESHOLD",
    "GYBING_ROT_THRESHOLD",
    "IRONS_SPEED",
    "STATE_IRONS_ROT",

    "PARAM_COUNT"
 ]

# NOTE: The tuples in the dict represent the starting (inclusive) and ending (exclusive) indexes
# of the params corresponding to that category
# NOTE: This method is used so that I can use the names in the dropdown, 
# assign them to a category, and use their index to pass to the CAN frame
pid_param_categories = {
    "STANDARD_COEFFS": (0, 9),
    "TACKING_COEFFS": (9, 18),
    "GYBING_COEFFS": (18, 27), 
    "LOW_WIND_COEFFS": (27, 36),
    "OTHER_COEFFS": (36, len(pid_params))
} 


# ==== CAN Frame offset parameters ====
integral_offset = 30000
derivative_offset = 30000

# ==== Joystick ====
movement_sensitivity = 1 # number of decimal point precision
max_rudder_angle = 20 # degrees
min_trimtab_angle = -12 # degrees
max_trimtab_angle = 3  # degrees

num_axes = 8 # number of possible switches/joystick axes for Radiomaster Boxer joystick
trimtab_axis = 0 # joystick axis used to move trimtab
trimtab_latch = 6 # latch axis number
rudder_axis = 3 # joystick axis used to move rudder
rudder_latch = 4 # latch axis number
LATCHED = 1 # latched == locked, unlatched == unlocked
UNLATCHED = -1
