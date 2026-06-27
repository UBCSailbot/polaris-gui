from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTextEdit,
)

from data_object import DataObject, Docker_Commands
from utils import all_objs
from workers.docker_send_worker import (
    DockerWorkerThread,
    generate_docker_command,
    kill_software,
)

from . import elements as elemns
from . import styles as styles
from config import pid_param_categories, pid_params


# UI creation functions
class CANWindowUIMixin:
    def __init__(self, **kwargs):
       super().__init__(**kwargs)   
    
    def init_ui(self):
        top_bar_layout = elemns.init_top_bar(self)
        checkbox_layout = elemns.init_checkbox(self)

        # NOTE: Replaced by init_top_bar
        # # === Top Bar ===
        # self.logo_label = QLabel()
        # pixmap = QPixmap("logo.png")
        # pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # self.logo_label.setPixmap(pixmap)

        # self.temp_label = QLabel("RPI Temp: --")
        # self.status_label = QLabel("DISCONNECTED")
        # self.status_label.setStyleSheet("color: red")

        # top_bar_layout = QHBoxLayout()
        # top_bar_layout.addWidget(self.logo_label)
        # top_bar_layout.addSpacing(10)
        # top_bar_layout.addWidget(self.temp_label)
        # top_bar_layout.addSpacing(10)
        # top_bar_layout.addWidget(self.status_label)
        # top_bar_layout.addStretch()

        # === Left Panel ===

        # TODO: figure out how this is inputted
        small_spacing = 2

        # NOTE: replaced by init_checkbox
        # self.manual_steer_checkbox = QCheckBox("Manual Steering")
        # self.manual_steer_checkbox.toggled.connect(self.set_manual_steer)
        # self.keyboard_checkbox = QCheckBox("Keyboard Mode")
        # self.keyboard_checkbox.toggled.connect(self.toggle_keyboard_mode)

        # checkbox_layout = QHBoxLayout()
        # checkbox_layout.addWidget(self.manual_steer_checkbox)
        # checkbox_layout.addWidget(self.keyboard_checkbox)

        self.instructions1_display = QLabel("For Rudder    (+/- 3 degrees): A / S / D  (Left / Center / Right)")
        self.instructions2_display = QLabel("For Trim Tab (+/- 3 degrees): Q / W / E (Left / Center / Right)")

        self.rudder_display = QLabel("Current Set Rudder Angle:  0 degrees")
        self.trimtab_display = QLabel("Current Trim Tab Angle:   0 degrees")

        self.desired_heading_input_group = elemns.init_desired_heading_input_group(self)
        self.rudder_input_group = elemns.init_rudder_input_group(self)
        self.trim_input_group = elemns.init_trim_input_group(self)

        # NOTE: replaced by init_desired_heading_input_group
        # self.desired_heading_input_layout = QVBoxLayout()
        # self.desired_heading_input = QLineEdit()
        # self.desired_heading_button = QPushButton("Set Desired Heading")
        # self.desired_heading_label = QLabel("Heading Angle:")
        # self.desired_heading_label.setStyleSheet(input_label_style)
        # self.desired_heading_input_layout.addWidget(self.desired_heading_label)
        # self.desired_heading_input_layout.addSpacing(small_spacing)
        # self.desired_heading_input_layout.addWidget(self.desired_heading_input)
        # self.desired_heading_input_layout.addSpacing(small_spacing)
        # self.desired_heading_input_layout.addWidget(self.desired_heading_button)
        # self.desired_heading_button.clicked.connect(self.send_desired_heading)
        # self.desired_heading_input_group = QWidget()
        # self.desired_heading_input_group.setLayout(self.desired_heading_input_layout)

        # NOTE: replaced by init_rudder_input_group
        # self.rudder_input_layout = QVBoxLayout()
        # self.rudder_input = QLineEdit()
        # self.rudder_button = QPushButton("Send Rudder")
        # self.rudder_input_label = QLabel("Rudder Angle:")
        # self.rudder_input_label.setStyleSheet(input_label_style)
        # self.rudder_input_layout.addWidget(self.rudder_input_label)
        # self.rudder_input_layout.addSpacing(small_spacing)
        # self.rudder_input_layout.addWidget(self.rudder_input)
        # self.rudder_input_layout.addSpacing(small_spacing)
        # self.rudder_input_layout.addWidget(self.rudder_button)
        # self.rudder_button.clicked.connect(self.send_rudder)
        # self.rudder_input_group = QWidget()
        # self.rudder_input_group.setLayout(self.rudder_input_layout)
        
        # NOTE: replaced by init_trim_input_group
        # self.trim_input = QLineEdit()
        # self.trim_button = QPushButton("Send Trim Tab")
        # self.trim_button.clicked.connect(self.send_trim_tab)
        # self.trim_input_layout = QVBoxLayout()
        # self.trim_input_label = QLabel("Trim Tab Angle:")
        # self.trim_input_label.setStyleSheet(input_label_style)
        # self.trim_input_layout.addWidget(self.trim_input_label)
        # self.trim_input_layout.addSpacing(small_spacing)
        # self.trim_input_layout.addWidget(self.trim_input)
        # self.trim_input_layout.addSpacing(small_spacing)
        # self.trim_input_layout.addWidget(self.trim_button)
        # self.trim_input_group = QWidget()
        # self.trim_input_group.setLayout(self.trim_input_layout)

        self.pid_layout = elemns.init_pid_layout(self)

        # NOTE: replaced by init_pid_layout
        # self.p_input = QLineEdit()
        # self.p_input.setPlaceholderText("P")
        # self.i_input = QLineEdit()
        # self.i_input.setPlaceholderText("I")
        # self.d_input = QLineEdit()
        # self.d_input.setPlaceholderText("D")
        # self.pid_input_layout = QHBoxLayout()
        # self.pid_input_layout.addWidget(self.p_input)
        # self.pid_input_layout.addWidget(self.i_input)
        # self.pid_input_layout.addWidget(self.d_input)
        # self.pid_input_button = QPushButton("Send PID")
        # self.pid_clear_button = QPushButton("Clear PID Datapoints")
        # self.pid_input_button.clicked.connect(self.send_pid)
        # self.pid_clear_button.clicked.connect(pid_obj.clear)
        # self.pid_layout = QVBoxLayout()
        # self.pid_layout.addLayout(self.pid_input_layout)
        # self.pid_layout.addWidget(self.pid_input_button)
        # self.pid_layout.addWidget(self.pid_clear_button)

        # TODO: create a similar elemns function to abstract out creation of PID params 
        # UI elements

        self.pid_param_dropdown_layout = elemns.init_pid_dropdown_layout(self)
        self.pid_param_input_layout = elemns.init_pid_input_layout(self)

        # NOTE: replaced by above two init functions
        # # Category dropdown for PID params
        # self.pid_param_category_dropdown = QComboBox()
        # self.pid_param_category_dropdown.setFont(QFont(cg.pid_dropdown_font_type, cg.pid_dropdown_font_size))
        # self.pid_param_category_dropdown.addItems(list(cg.pid_param_categories.keys()))
        # self.pid_param_category_dropdown.currentTextChanged.connect(self.update_pid_param_dropdown)

        # # Secondary (detailed) dropdown for PID params
        # self.pid_param_dropdown = QComboBox()
        # self.pid_param_dropdown.setFont(QFont(cg.pid_dropdown_font_type, cg.pid_dropdown_font_size))
        # self.update_pid_param_dropdown(self.pid_param_category_dropdown.currentText())
        
        # # Input field for PID params
        # self.pid_param_input = QLineEdit(placeholderText = "Value")
        # self.pid_param_input.setFont(QFont(cg.pid_dropdown_font_type, cg.pid_dropdown_font_size))

        # # Layout setup for PID params
        # self.pid_param_dropdown_layout = QHBoxLayout()
        # self.pid_param_dropdown_layout.addWidget(self.pid_param_category_dropdown)
        # self.pid_param_dropdown_layout.addWidget(self.pid_param_dropdown)
        # self.pid_param_button = QPushButton("Set PID Parameter")
        # self.pid_param_button.clicked.connect(self.send_pid_param) # TODO: Do something (send CAN frame) on button click
        # self.pid_param_input_layout = QHBoxLayout()
        # self.pid_param_input_layout.addWidget(self.pid_param_input)
        # self.pid_param_input_layout.addWidget(self.pid_param_button)

        software_commands = [
            ("Start Software", Docker_Commands.START),
            ("Stop Software", Docker_Commands.STOP),
            ("Enable Wingsail Controller", Docker_Commands.START_WING),
            ("Disable Wingsail Controller", Docker_Commands.STOP_WING),
            ("Start w/ visualizer", Docker_Commands.START_VISUAL)
        ]
        software_controls_layout = elemns.init_software_controls(
            self, software_commands
        )

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setMinimumWidth(350)

        # Separate terminal output display
        self.terminal_output_display = QTextEdit()
        self.terminal_output_display.setReadOnly(True)

        emergency_controls_layout = elemns.init_emergency_controls(self)

        # NOTE: replaced by init_emergency_controls
        # # Emergency controls section
        # self.emergency_checkbox = QCheckBox("Enable Emergency Controls")
        # self.emergency_checkbox.stateChanged.connect(self.toggle_emergency_buttons)

        # # Power control buttons
        # self.power_off_btn = QPushButton("Power Off Indefinitely")
        # self.power_off_btn.setEnabled(False)
        # self.power_off_btn.clicked.connect(self.send_power_off_indefinitely)

        # self.restart_btn = QPushButton("Restart Power After 20s")
        # self.restart_btn.setEnabled(False)
        # self.restart_btn.clicked.connect(self.send_restart_power)

        # emergency_controls_layout = QHBoxLayout()
        # emergency_controls_layout.addWidget(self.power_off_btn)
        # emergency_controls_layout.addWidget(self.restart_btn)

        # SSH Instructions for CAN and system control
        self.ssh_instructions_label = QLabel(
            "SSH Terminal Instructions:\n"
            "1. Open separate terminal/PowerShell\n"
            "2. ssh sailbot@192.168.0.10\n"
            "3. Password: sailbot\n"
            "Use buttons below to copy commands:"
        )

        self.ssh_instructions_label.setStyleSheet(styles.instructions_label)
        # NOTE: replaced by above
        # self.ssh_instructions_label.setStyleSheet("""
        #     QLabel {
        #         color: blue;
        #         font-size: 11px;
        #         font-weight: bold;
        #         padding: 4px;
        #         background-color: #e6f3ff;
        #         border: 2px solid #4d94ff;
        #         border-radius: 3px;
        #         margin: 2px;
        #     }
        # """)
        
        # Define commands with labels
        commands = [
            ("SSH Connect", "ssh sailbot@192.168.0.10"),
            ("CAN0 Down", "sudo ip link set can0 down"),
            ("CAN0 Up", "sudo ip link set can0 up type can bitrate 500000 dbitrate 1000000 fd on")
           # ("Check CAN Status", "ip link show can0"),
           # ("View System Logs", "dmesg | tail"),
           # ("System Info", "uname -a")
        ]

        self.commands_grid = elemns.init_commands_grid(self, commands)
        
        # NOTE: replaced by init_commands_grid
        # # Create a grid layout for command buttons
        # self.commands_grid = QGridLayout()
        #
        # # Create buttons for each command
        # self.command_buttons = []
        # for i, (label, command) in enumerate(commands):
        #     btn = QPushButton(f"Copy: {label}")
        #     btn.setStyleSheet("""
        #         QPushButton {
        #             background-color: #4d94ff;
        #             color: white;
        #             border: none;
        #             padding: 2px 4px;
        #             border-radius: 3px;
        #             font-size: 10px;
        #             font-weight: bold;
        #         }
        #         QPushButton:hover {
        #             background-color: #0066cc;
        #         }
        #         QPushButton:pressed {
        #             background-color: #003d7a;
        #         }
        #     """)
        #     btn.clicked.connect(lambda checked, cmd=command: self.copy_to_clipboard(cmd))
        #     self.command_buttons.append(btn)
            
        #     # Add to grid layout (2 columns)
        #     row = i // 2
        #     col = i % 2
        #     self.commands_grid.addWidget(btn, row, col)

        # NOTE: in styles.py
        # # Style for emergency buttons (power controls)
        # red_button_style = """
        #         QPushButton {
        #             background-color: red;
        #             color: white;
        #             border: none;
        #             padding: 3px 6px;
        #             border-radius: 4px;
        #             font-weight: bold;
        #         }
        #         QPushButton:hover:enabled {
        #             background-color: yellow;
        #             color: black;
        #         }
        #         QPushButton:disabled {
        #             background-color: yellow;
        #             color: black;
        #         }
        #     """
        
        # NOTE: replaced by init_emergency_controls
        # self.power_off_btn.setStyleSheet(red_button_style)
        # self.restart_btn.setStyleSheet(red_button_style)

        input_layout = elemns.init_input_layout(self)
        # NOTE: replaced by init_input_layout
        # input_layout = QGridLayout()
        # input_layout.setSpacing(0)
        # input_layout.addWidget(self.rudder_input_group, 0, 0)
        # input_layout.addWidget(self.trim_input_group, 0, 1)
        # input_layout.addWidget(self.desired_heading_input_group, 0, 0)

        left_layout = elemns.init_left_layout(
            self,
            top_bar_layout,
            checkbox_layout,
            input_layout,
            emergency_controls_layout,
            software_controls_layout,
        )

        # NOTE: replaced by init_left_layout
        # left_layout = QVBoxLayout()
        # left_layout.addLayout(top_bar_layout)
        # left_layout.addLayout(checkbox_layout)
        # left_layout.addSpacing(5)  # Add small spacing
        # left_layout.addWidget(self.instructions1_display)
        # left_layout.addWidget(self.instructions2_display)
        # left_layout.addSpacing(5)  # Add small spacing
        # left_layout.addWidget(self.rudder_display)
        # left_layout.addWidget(self.trimtab_display)
        # left_layout.addSpacing(5)  # Add small spacing

        # # Add UI elements for PID tuning
        # left_layout.addLayout(input_layout)
        # left_layout.addLayout(self.pid_layout)
        
        # # Add UI elements for PID parameter tuning
        # left_layout.addLayout(self.pid_param_dropdown_layout)
        # # left_layout.addWidget(self.pid_param_button)
        # left_layout.addLayout(self.pid_param_input_layout)

        # self.rudder_input_group.setVisible(False)

        # left_layout.addSpacing(5)  # Add small spacing
        # left_layout.addWidget(QLabel("Candump Output:"))
        # left_layout.addWidget(self.output_display)
        # left_layout.addSpacing(5)  # Add small spacing

        # # Add UI elements for heartbeat displays 
        # for mod in heartbeat_modules:
        #     mod.init_label()
        #     left_layout.addWidget(mod.label)
        # left_layout.addSpacing(5)  # Add small spacing
        # left_layout.addWidget(self.emergency_checkbox)
        # left_layout.addSpacing(5)  # Add spacing before emergency buttons
        # left_layout.addLayout(emergency_controls_layout)
        # left_layout.addSpacing(5)  # Add spacing before SSH instructions
        # left_layout.addWidget(self.ssh_instructions_label)
        # left_layout.addSpacing(5)  # Small spacing before command buttons
        # left_layout.addLayout(self.commands_grid)

        # === Right Panel ===
        labels_layout = elemns.init_labels_layout()
        # NOTE: replaced by init_labels_layout
        # labels_layout = QVBoxLayout()
        # labels_layout.setSpacing(0)

        # for graph_obj in all_objs:
        #     if (graph_obj.label is not None):
        #         labels_layout.addWidget(graph_obj.label)
        
        # labels_layout.addStretch(1)

        right_layout = elemns.init_right_layout(self)

        # NOTE: replaced by init_right_layout
        # right_layout = QVBoxLayout()
        # # Graph dropdowns (Top, Middle, Bottom)
        # dropdown_layout = QHBoxLayout()
        # d_top = QComboBox()
        # d_mid = QComboBox()
        # d_bot = QComboBox()
        # dropdowns = [d_top, d_mid, d_bot]

        # self.right_graphs_layout = QGridLayout() # create GridLayout for three graphs (0, 0), (1, 0), (2, 0)
        # # Note: It is important that each distinct graph canvas is only added as a widget
        # #       a single time, or else problems
        # self.visibleGraphObjs = [] # list of GraphObjs with visible graphs, in order of position descending

        # for d in dropdowns:
        #     d.setFont(QFont(cg.d_font_type, cg.d_font_size))
        #     # d.addItems(self.graph_titles)
        #     # NOTE: This replaces the above line to get titles
        #     d.addItems([graph_obj.dropdown_label for graph_obj in graph_objs])
        #     d.setVisible(False)
        #     dropdown_layout.addWidget(d)

        # # show a maximum of three graphs initially 
        # for i in range(0, 3):
        #     if (i < len(graph_objs)):
        #         self.right_graphs_layout.addWidget(graph_objs[i].graph, i, 0)
        #         self.visibleGraphObjs.append(graph_objs[i])
        #         graph_objs[i].show()
        #         dropdowns[i].setCurrentText(graph_objs[i].dropdown_label)
        #         dropdowns[i].setVisible(True)
        #     else: break

        # d_top.currentTextChanged.connect(lambda text: self.setGraph(text, 0, dropdowns))
        # d_mid.currentTextChanged.connect(lambda text: self.setGraph(text, 1, dropdowns))
        # d_bot.currentTextChanged.connect(lambda text: self.setGraph(text, 2, dropdowns))
        
        # right_layout.addLayout(dropdown_layout)
        # right_layout.addLayout(self.right_graphs_layout)

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
        self.set_joystick_enabled(checked)

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

    def update_pid_param_dropdown(self, text: str) -> None:
        '''Updates the PID param dropdown based on the category selected'''
        first, last = pid_param_categories[text]
        self.pid_param_dropdown.clear()
        self.pid_param_dropdown.addItems(pid_params[first:last])
        return

    # NOTE: Commented out this function as I don't need it
    # def getGraphObjFromXName(self, name):
    #     for obj in all_objs:
    #         if ((obj.graph_obj is not None) and (obj.graph_obj.dropdown_label == name)):
    #             return obj.graph_obj

    def getObjFromLabel(self, dropdown_label) -> DataObject:
        for obj in all_objs:
            if (obj.graph_obj is not None) and (
                obj.graph_obj.dropdown_label == dropdown_label
            ):
                return obj

    def setGraph(self, name: str, spot: int, dropdowns: list[QComboBox]) -> None:
        """
        Shows given graph at spot\n
        name = DataObj.graph_obj.dropdown_label\n
        spot = 0, 1, 2 (top, mid, bot)\n
        """
        newObj = self.getObjFromLabel(name)
        # newGraphObj = self.getGraphObjFromXName(name) # get graph to put in spot
        newGraphObj = newObj.graph_obj

        if newGraphObj.dropdown_label == self.visibleGraphObjs[spot].dropdown_label:
            return  # do nothing
        if (
            newGraphObj in self.visibleGraphObjs
        ):  # if graph to put in spot is already visible
            # don't allow the switch to happen - set dropdown text back to original and print error message
            print("[ERR] Graph is already visible")
            dropdowns[spot].setCurrentText(
                self.visibleGraphObjs[spot].dropdown_label
            )  # switch text back to original
        else:
            self.right_graphs_layout.removeWidget(
                self.visibleGraphObjs[spot].graph
            )  # remove graph currently in spot
            self.visibleGraphObjs[spot].hide()
            self.right_graphs_layout.addWidget(newGraphObj.graph, spot, 0)
            newGraphObj.show()
            self.visibleGraphObjs[spot] = newGraphObj
            newObj.update_line_data()

        dropdowns[spot].clearFocus()

    def run_docker_command(self, action: Docker_Commands):
        container_name = self.container_text_box.text().strip()

        if not container_name:
            self.show_error("Enter a Docker container name.")
            return

        try:
            command = generate_docker_command(action, container_name)
        except RuntimeError as e:
            self.show_error(str(e))
            return

        self.docker_thread = DockerWorkerThread(command, action)
        self.docker_thread.success.connect(self._on_docker_success)
        self.docker_thread.error.connect(self.show_error)

        self.docker_thread.started.connect(lambda: self.enable_software_controls(False))
        self.docker_thread.finished.connect(lambda: self.enable_software_controls(True))

        self.docker_thread.start()

    # TODO change this from a pop up to some sort of status indicator
    def _on_docker_success(self, action):
        container_name = self.container_text_box.text().strip()
        QMessageBox.information(
            self, "Success", f"Successfully {action.name.lower()}ed container:\n{container_name}"
        )

    def enable_software_controls(self, enabled: bool):
        for button in self.software_control_buttons:
            button.setEnabled(enabled)

    def call_software_emergency_kill(self):
        try:
            kill_software()
        except RuntimeError as e:
            self.show_error(str(e))
