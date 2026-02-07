from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QCheckBox, QGridLayout, QComboBox
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt

from config import *
from . import styles
from utility import *

# CONSTANTS
SMALL_SPACING = 2

# Functions to initialize all the ui elements

def init_top_bar(self):
    self.logo_label = QLabel()
    pixmap = QPixmap("src/logo.png")
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
    
    self.pid_layout = QVBoxLayout()
    self.pid_layout.addLayout(self.pid_input_layout)
    self.pid_layout.addWidget(self.pid_input_button)
    
    return self.pid_layout

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

def init_input_layout(self):
    input_layout = QGridLayout()
    input_layout.setSpacing(0)
    input_layout.addWidget(self.rudder_input_group, 0, 0)
    input_layout.addWidget(self.trim_input_group, 0, 1)
    input_layout.addWidget(self.desired_heading_input_group, 0, 0)
    
    return input_layout

def init_left_layout(self, top_bar_layout, checkbox_layout, input_layout, emergency_controls):    
    left_layout = QVBoxLayout()
    left_layout.addLayout(top_bar_layout)
    left_layout.addLayout(checkbox_layout)
    left_layout.addSpacing(5)  # Add small spacing
    left_layout.addWidget(self.instructions1_display)
    left_layout.addWidget(self.instructions2_display)
    left_layout.addSpacing(5)  # Add small spacing
    left_layout.addWidget(self.rudder_display)
    left_layout.addWidget(self.trimtab_display)
    left_layout.addSpacing(5)  # Add small spacing
    
    left_layout.addLayout(input_layout)
    left_layout.addLayout(self.pid_layout)
    
    left_layout.addSpacing(5)  # Add small spacing
    left_layout.addWidget(QLabel("Candump Output:"))
    left_layout.addWidget(self.output_display)
    left_layout.addSpacing(5)  # Add small spacing
    left_layout.addWidget(self.emergency_checkbox)
    left_layout.addSpacing(5)  # Add spacing before emergency buttons
    left_layout.addLayout(emergency_controls)
    left_layout.addSpacing(5)  # Add spacing before SSH instructions
    left_layout.addWidget(self.ssh_instructions_label)
    left_layout.addSpacing(5)  # Small spacing before command buttons
    left_layout.addLayout(self.commands_grid)
    
    return left_layout
    
def init_labels_layout():
    labels_layout = QVBoxLayout()
    labels_layout.setSpacing(0)

    for graph_obj in all_objs:
        if (graph_obj.label is not None):
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

    self.right_graphs_layout = QGridLayout() # create GridLayout for three graphs (0, 0), (1, 0), (2, 0)
    # Note: It is important that each distinct graph canvas is only added as a widget
    #       a single time, or else problems
    self.visibleGraphObjs = [] # list of GraphObjs with visible graphs, in order of position descending

    self.graph_titles = []
    for obj in all_objs:
        if ((obj.graph_obj is not None) and (obj.graph_obj.dropdown_label not in self.graph_titles)):
            self.graph_titles.append(obj.graph_obj.dropdown_label)

    for d in dropdowns:
        d.setFont(QFont(cg.d_font_type, cg.d_font_size))
        d.addItems(self.graph_titles)
        d.setVisible(False)
        dropdown_layout.addWidget(d)

    # show a maximum of three graphs initially 
    for i in range(0, 3):
        if (i < len(self.graph_titles)):
            graph_obj = self.getGraphObjFromXName(self.graph_titles[i])
            if (graph_obj not in self.visibleGraphObjs):
                self.right_graphs_layout.addWidget(graph_obj.graph, i, 0)
                self.visibleGraphObjs.append(graph_obj)
                graph_obj.show()
                dropdowns[i].setCurrentText(self.graph_titles[i])
                dropdowns[i].setVisible(True)
        else: break

    d_top.currentTextChanged.connect(lambda text: self.setGraph(text, 0, dropdowns))
    d_mid.currentTextChanged.connect(lambda text: self.setGraph(text, 1, dropdowns))
    d_bot.currentTextChanged.connect(lambda text: self.setGraph(text, 2, dropdowns))
    
    right_layout.addLayout(dropdown_layout)
    right_layout.addLayout(self.right_graphs_layout)
    
    return right_layout
