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

# ==== Joystick ====
movement_sensitivity = 1 # number of decimal point precision
max_angle = 20 # degrees
