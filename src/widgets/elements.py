from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import config as cg
from config import input_label_style
from data_object import Docker_Command, Docker_Command_Type
from utils import all_objs, graph_objs, heartbeat_modules, pid_obj

from . import styles

# CONSTANTS
SMALL_SPACING = 2

# Functions to initialize all the ui elements


def init_top_bar(self):
    self.logo_label = QLabel()
    pixmap = QPixmap("logo.png")
    pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    self.logo_label.setPixmap(pixmap)

    self.temp_label = QLabel("RPI Temp: --")
    self.status_label = QLabel("DISCONNECTED")
    self.status_label.setStyleSheet("color: red")

    top_bar_layout = QHBoxLayout()
    top_bar_layout.addWidget(self.logo_label)
    top_bar_layout.addSpacing(10)
    top_bar_layout.addWidget(self.temp_label)
    top_bar_layout.addSpacing(10)
    top_bar_layout.addWidget(self.status_label)
    top_bar_layout.addStretch()
    return top_bar_layout


def init_checkbox(self):
    self.manual_steer_checkbox = QCheckBox("Manual Steering")
    self.manual_steer_checkbox.toggled.connect(self.set_manual_steer)
    self.keyboard_checkbox = QCheckBox("Keyboard Mode")
    self.keyboard_checkbox.toggled.connect(self.toggle_keyboard_mode)

    checkbox_layout = QHBoxLayout()
    checkbox_layout.addWidget(self.manual_steer_checkbox)
    checkbox_layout.addWidget(self.keyboard_checkbox)

    return checkbox_layout


def init_ssh_dropdown(self):
    self.SSH_dropdown = QComboBox()
    self.SSH_dropdown.addItems(
        ["Wifi/deployment", "Wifi/test-bench", "remote/deployment", "remote/test-bench"]
    )
    self.SSH_dropdown.setCurrentText(cg.profile)
    self.SSH_dropdown.currentTextChanged.connect(self.change_SSH_profile)

    ssh_layout = QHBoxLayout()
    ssh_layout.setSpacing(5)
    ssh_label = QLabel("RPI Selector:")
    ssh_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
    ssh_layout.addWidget(ssh_label)
    ssh_layout.addWidget(self.SSH_dropdown)

    return ssh_layout


def init_desired_heading_input_group(self):
    self.desired_heading_input_layout = QVBoxLayout()
    self.desired_heading_input = QLineEdit()
    self.desired_heading_button = QPushButton("Set Desired Heading")
    self.desired_heading_label = QLabel("Heading Angle:")
    self.desired_heading_label.setStyleSheet(input_label_style)
    self.desired_heading_input_layout.addWidget(self.desired_heading_label)
    self.desired_heading_input_layout.addSpacing(SMALL_SPACING)
    self.desired_heading_input_layout.addWidget(self.desired_heading_input)
    self.desired_heading_input_layout.addSpacing(SMALL_SPACING)
    self.desired_heading_input_layout.addWidget(self.desired_heading_button)
    self.desired_heading_button.clicked.connect(self.send_desired_heading)
    self.desired_heading_input_group = QWidget()
    self.desired_heading_input_group.setLayout(self.desired_heading_input_layout)

    return self.desired_heading_input_group


def init_rudder_input_group(self):
    self.rudder_input = QLineEdit()
    self.rudder_input_layout = QVBoxLayout()
    self.rudder_button = QPushButton("Send Rudder")
    self.rudder_input_label = QLabel("Rudder Angle:")
    self.rudder_input_label.setStyleSheet(input_label_style)
    self.rudder_input_layout.addWidget(self.rudder_input_label)
    self.rudder_input_layout.addSpacing(SMALL_SPACING)
    self.rudder_input_layout.addWidget(self.rudder_input)
    self.rudder_input_layout.addSpacing(SMALL_SPACING)
    self.rudder_input_layout.addWidget(self.rudder_button)
    self.rudder_button.clicked.connect(self.send_rudder)
    self.rudder_input_group = QWidget()
    self.rudder_input_group.setLayout(self.rudder_input_layout)
    self.rudder_input_group.setVisible(False)

    return self.rudder_input_group


def init_trim_input_group(self):
    self.trim_input = QLineEdit()
    self.trim_button = QPushButton("Send Trim Tab")
    self.trim_button.clicked.connect(self.send_trim_tab)
    self.trim_input_layout = QVBoxLayout()
    self.trim_input_label = QLabel("Trim Tab Angle:")
    self.trim_input_label.setStyleSheet(input_label_style)
    self.trim_input_layout.addWidget(self.trim_input_label)
    self.trim_input_layout.addSpacing(SMALL_SPACING)
    self.trim_input_layout.addWidget(self.trim_input)
    self.trim_input_layout.addSpacing(SMALL_SPACING)
    self.trim_input_layout.addWidget(self.trim_button)
    self.trim_input_group = QWidget()
    self.trim_input_group.setLayout(self.trim_input_layout)

    return self.trim_input_group


def init_pid_layout(self):
    self.p_input = QLineEdit()
    self.p_input.setPlaceholderText("P")
    self.i_input = QLineEdit()
    self.i_input.setPlaceholderText("I")
    self.d_input = QLineEdit()
    self.d_input.setPlaceholderText("D")

    self.pid_input_layout = QHBoxLayout()
    self.pid_input_layout.addWidget(self.p_input)
    self.pid_input_layout.addWidget(self.i_input)
    self.pid_input_layout.addWidget(self.d_input)
    self.pid_input_button = QPushButton("Send PID")
    self.pid_input_button.clicked.connect(self.send_pid)
    self.pid_clear_button = QPushButton("Clear PID Datapoints")
    self.pid_clear_button.clicked.connect(pid_obj.clear)

    self.pid_layout = QVBoxLayout()
    self.pid_layout.addLayout(self.pid_input_layout)
    self.pid_layout.addWidget(self.pid_input_button)
    self.pid_layout.addWidget(self.pid_clear_button)

    return self.pid_layout


def init_pid_dropdown_layout(self):
    # Category dropdown for PID params
    self.pid_param_category_dropdown = QComboBox()
    self.pid_param_category_dropdown.setFont(
        QFont(cg.pid_dropdown_font_type, cg.pid_dropdown_font_size)
    )
    self.pid_param_category_dropdown.addItems(list(cg.pid_param_categories.keys()))
    self.pid_param_category_dropdown.currentTextChanged.connect(
        self.update_pid_param_dropdown
    )

    # Secondary (detailed) dropdown for PID params
    self.pid_param_dropdown = QComboBox()
    self.pid_param_dropdown.setFont(
        QFont(cg.pid_dropdown_font_type, cg.pid_dropdown_font_size)
    )
    self.update_pid_param_dropdown(self.pid_param_category_dropdown.currentText())

    # Layout setup for PID params
    self.pid_param_dropdown_layout = QHBoxLayout()
    self.pid_param_dropdown_layout.addWidget(self.pid_param_category_dropdown)
    self.pid_param_dropdown_layout.addWidget(self.pid_param_dropdown)

    return self.pid_param_dropdown_layout


def init_pid_input_layout(self):
    # Input field for PID params
    self.pid_param_input = QLineEdit(placeholderText="Value")
    self.pid_param_input.setFont(
        QFont(cg.pid_dropdown_font_type, cg.pid_dropdown_font_size)
    )

    # Send button for PID param
    self.pid_param_button = QPushButton("Set PID Parameter")
    self.pid_param_button.clicked.connect(
        self.send_pid_param
    )  # TODO: Do something (send CAN frame) on button click

    # Layout setup
    self.pid_param_input_layout = QHBoxLayout()
    self.pid_param_input_layout.addWidget(self.pid_param_input)
    self.pid_param_input_layout.addWidget(self.pid_param_button)

    return self.pid_param_input_layout


def init_emergency_controls(self):
    self.emergency_checkbox = QCheckBox("Enable Emergency Controls")
    self.emergency_checkbox.stateChanged.connect(self.toggle_emergency_buttons)

    # Power control buttons
    self.power_off_btn = QPushButton("Power Off Indefinitely")
    self.power_off_btn.setEnabled(False)
    self.power_off_btn.clicked.connect(self.send_power_off_indefinitely)

    self.restart_btn = QPushButton("Restart Power After 20s")
    self.restart_btn.setEnabled(False)
    self.restart_btn.clicked.connect(self.send_restart_power)

    self.power_off_btn.setStyleSheet(styles.red_button)
    self.restart_btn.setStyleSheet(styles.red_button)

    emergency_controls_layout = QHBoxLayout()
    emergency_controls_layout.addWidget(self.power_off_btn)
    emergency_controls_layout.addWidget(self.restart_btn)

    return emergency_controls_layout


def init_commands_grid(self, commands):
    # Create a grid layout for command buttons
    self.commands_grid = QGridLayout()

    # Create buttons for each command
    self.command_buttons = []
    for i, (label, command) in enumerate(commands):
        btn = QPushButton(f"Copy: {label}")
        btn.setStyleSheet(styles.command_button)
        btn.clicked.connect(lambda checked, cmd=command: self.copy_to_clipboard(cmd))
        self.command_buttons.append(btn)

        # Add to grid layout (2 columns)
        row = i // 2
        col = i % 2
        self.commands_grid.addWidget(btn, row, col)

    return self.commands_grid


def init_software_controls(self, commands):
    soft_controls = QVBoxLayout()
    self.container_text_box = QLineEdit()
    self.container_text_box.setPlaceholderText(
        "Enter docker container name (e.g. example-name)"
    )

    soft_controls.addWidget(QLabel("Software Controls:"))
    soft_controls.addWidget(self.container_text_box)

    self.software_control_buttons = []
    soft_buttons = QGridLayout()

    for i, (label, cmd) in enumerate(commands):
        btn = QPushButton(label)
        btn.clicked.connect(lambda checked=False, cmd=cmd: self.run_docker_command(cmd))
        self.software_control_buttons.append(btn)

        # Add to grid layout (2 columns)
        row = i // 2
        col = i % 2
        soft_buttons.addWidget(btn, row, col)

    kill_button = QPushButton("Kill Software")
    kill_button.clicked.connect(self.call_software_emergency_kill)
    kill_button.setStyleSheet(styles.red_button)

    soft_controls.addLayout(soft_buttons)
    soft_controls.addWidget(kill_button)

    return soft_controls


def init_advanced_soft_panel(self):
    panel = QWidget()
    panel.setMinimumSize(cg.graph_min_width, cg.graph_min_height)

    panel_layout = QVBoxLayout()
    panel.setLayout(panel_layout)

    title_label = QLabel("Advanced Software Controls")
    title_label.setStyleSheet("font-weight: bold;")
    panel_layout.addWidget(title_label)

    config_grid = QGridLayout()
    grid_widget = QWidget()
    grid_widget.setLayout(config_grid)
    grid_widget.setMaximumWidth(500)
    config_grid.setContentsMargins(0, 0, 0, 0)

    # dropdowns
    launch_mode_dropdown = QComboBox()
    launch_mode_dropdown.addItems(["development", "production", "sim"])
    launch_mode_dropdown.setFixedWidth(150)

    self.launch_mode_dropdown = launch_mode_dropdown

    launch_mode_layout = QHBoxLayout()
    launch_mode_layout.addWidget(QLabel("Launch mode:"))
    launch_mode_layout.addWidget(self.launch_mode_dropdown)
    launch_mode_layout.setSpacing(4)

    config_file_dropdown = QComboBox()
    config_file_dropdown.addItems(
        ["globals.yaml", "on_water_globals.yaml", "launch_globals.yaml"]
    )
    config_file_dropdown.setFixedWidth(150)
    self.config_file_dropdown = config_file_dropdown

    config_file_layout = QHBoxLayout()
    config_file_layout.addWidget(QLabel("Config file:"))
    config_file_layout.addWidget(self.config_file_dropdown)
    config_file_layout.setSpacing(25)

    # checkboxes
    self.mock_ais_checkbox = QCheckBox("Enable mock AIS data?")
    self.visualizer_mode_checkbox = QCheckBox("Enable pathfinding visualizer?")

    config_grid.addLayout(launch_mode_layout, 0, 0, alignment=Qt.AlignLeft)
    config_grid.addLayout(config_file_layout, 1, 0, alignment=Qt.AlignLeft)
    config_grid.addWidget(self.mock_ais_checkbox, 0, 1)
    config_grid.addWidget(self.visualizer_mode_checkbox, 1, 1)

    config_grid.setColumnStretch(0, 0)
    config_grid.setColumnStretch(1, 0)

    # launch custom config button
    custom_launch_btn = QPushButton("Custom Launch")
    custom_launch_btn.clicked.connect(
        lambda _: self.run_docker_command(
            Docker_Command(
                Docker_Command_Type.START_CUSTOM,
                launch_mode=self.launch_mode_dropdown.currentText(),
                config_file=self.config_file_dropdown.currentText(),
                mock_ais=str(self.mock_ais_checkbox.isChecked()).lower(),
                visualizer_mode=str(self.visualizer_mode_checkbox.isChecked()).lower(),
            )
        )
    )
    custom_launch_btn.setMaximumWidth(150)

    # Add to this control group that gets disabled when any other button is pressed.
    self.software_control_buttons.append(custom_launch_btn)

    self.docker_log_display = QTextEdit()
    self.docker_log_display.setReadOnly(True)
    self.docker_log_display.setPlaceholderText("Docker action logs will appear here.")
    self.docker_log_display.setMinimumHeight(110)
    self.docker_log_display.setMaximumHeight(180)

    panel_layout.addWidget(grid_widget)
    panel_layout.addWidget(custom_launch_btn)
    panel_layout.addWidget(QLabel("Docker Message Log:"))
    panel_layout.addWidget(self.docker_log_display)

    panel_layout.addStretch(1)

    return panel


def init_input_layout(self):
    input_layout = QGridLayout()
    input_layout.setSpacing(0)
    input_layout.addWidget(self.rudder_input_group, 0, 0)
    input_layout.addWidget(self.trim_input_group, 0, 1)
    input_layout.addWidget(self.desired_heading_input_group, 0, 0)

    return input_layout


def init_left_layout(
    self,
    top_bar_layout,
    ssh_layout,
    checkbox_layout,
    input_layout,
    emergency_controls,
    software_controls,
):
    left_layout = QVBoxLayout()
    left_layout.addLayout(top_bar_layout)
    left_layout.addLayout(ssh_layout)
    left_layout.addLayout(checkbox_layout)
    left_layout.addSpacing(5)  # Add small spacing
    left_layout.addWidget(self.instructions1_display)
    left_layout.addWidget(self.instructions2_display)
    left_layout.addSpacing(5)  # Add small spacing
    left_layout.addWidget(self.rudder_display)
    left_layout.addWidget(self.trimtab_display)
    left_layout.addSpacing(5)  # Add small spacing

    # Add UI elements for PID tuning
    left_layout.addLayout(input_layout)
    left_layout.addLayout(self.pid_layout)

    # Add UI elements for PID parameter tuning
    left_layout.addLayout(self.pid_param_dropdown_layout)
    # left_layout.addWidget(self.pid_param_button)
    left_layout.addLayout(self.pid_param_input_layout)

    # self.rudder_input_group.setVisible(False) # NOTE: This is in init_rudder_input...() function

    left_layout.addSpacing(5)  # Add small spacing
    left_layout.addWidget(QLabel("Candump Output:"))
    left_layout.addWidget(self.output_display)
    left_layout.addSpacing(5)  # Add small spacing

    for mod in heartbeat_modules:
        mod.init_label()
        left_layout.addWidget(mod.label)

    left_layout.addSpacing(5)  # Add small spacing
    left_layout.addWidget(self.emergency_checkbox)
    left_layout.addSpacing(5)  # Add spacing before emergency buttons
    left_layout.addLayout(emergency_controls)
    left_layout.addSpacing(5)  # Add spacing before software controls
    left_layout.addLayout(software_controls)
    left_layout.addSpacing(5)  # Add spacing before SSH instructions
    left_layout.addWidget(self.ssh_instructions_label)
    left_layout.addSpacing(5)  # Small spacing before command buttons
    left_layout.addLayout(self.commands_grid)

    return left_layout


def init_labels_layout():
    labels_layout = QVBoxLayout()
    labels_layout.setSpacing(0)

    for graph_obj in all_objs:
        if graph_obj.label is not None:
            labels_layout.addWidget(graph_obj.label)

    labels_layout.addStretch(1)
    return labels_layout


def init_right_layout(self):
    right_layout = QVBoxLayout()
    # Graph dropdowns (Top, Middle, Bottom)
    dropdown_layout = QHBoxLayout()
    d_top = QComboBox()
    d_mid = QComboBox()
    d_bot = QComboBox()
    dropdowns = [d_top, d_mid, d_bot]

    self.right_graphs_layout = (
        QGridLayout()
    )  # create GridLayout for three graphs (0, 0), (1, 0), (2, 0)
    # Note: It is important that each distinct graph canvas is only added as a widget
    #       a single time, or else problems

    # list of GraphObjs with visible graphs, in order of position descending
    self.visibleGraphObjs = []

    self.graph_titles = []
    for obj in all_objs:
        if (obj.graph_obj is not None) and (
            obj.graph_obj.dropdown_label not in self.graph_titles
        ):
            self.graph_titles.append(obj.graph_obj.dropdown_label)

    if hasattr(self, "advanced_soft_panel_label"):
        self.graph_titles.append(self.advanced_soft_panel_label)

    for d in dropdowns:
        d.setFont(QFont(cg.d_font_type, cg.d_font_size))
        d.addItems(self.graph_titles)
        d.setVisible(False)
        dropdown_layout.addWidget(d)

    # show a maximum of three graphs initially
    for i in range(0, 3):
        if i < len(graph_objs):
            self.right_graphs_layout.addWidget(graph_objs[i].graph, i, 0)
            self.visibleGraphObjs.append(graph_objs[i])
            graph_objs[i].show()
            dropdowns[i].setCurrentText(graph_objs[i].dropdown_label)
            dropdowns[i].setVisible(True)
        else:
            break

    d_top.currentTextChanged.connect(lambda text: self.setGraph(text, 0, dropdowns))
    d_mid.currentTextChanged.connect(lambda text: self.setGraph(text, 1, dropdowns))
    d_bot.currentTextChanged.connect(lambda text: self.setGraph(text, 2, dropdowns))

    right_layout.addLayout(dropdown_layout)
    right_layout.addLayout(self.right_graphs_layout)

    return right_layout
