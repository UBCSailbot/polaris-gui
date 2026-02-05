from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QTextEdit, QHBoxLayout, QCheckBox, QGridLayout, QComboBox,
    QSizePolicy
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import QTimer, Qt

from config import *
import styles

# constants
small_spacing = 2

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
    
def init_desired_heading_input_group(self):
    self.desired_heading_input_layout = QVBoxLayout()
    self.desired_heading_input = QLineEdit()
    self.desired_heading_button = QPushButton("Set Desired Heading")
    self.desired_heading_label = QLabel("Heading Angle:")
    self.desired_heading_label.setStyleSheet(input_label_style)
    self.desired_heading_input_layout.addWidget(self.desired_heading_label)
    self.desired_heading_input_layout.addSpacing(small_spacing)
    self.desired_heading_input_layout.addWidget(self.desired_heading_input)
    self.desired_heading_input_layout.addSpacing(small_spacing)
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
    self.rudder_input_layout.addSpacing(small_spacing)
    self.rudder_input_layout.addWidget(self.rudder_input)
    self.rudder_input_layout.addSpacing(small_spacing)
    self.rudder_input_layout.addWidget(self.rudder_button)
    self.rudder_button.clicked.connect(self.send_rudder)
    self.rudder_input_group = QWidget()
    self.rudder_input_group.setLayout(self.rudder_input_layout)
    
    return self.rudder_input_group

def init_trim_input_group(self):
    self.trim_input = QLineEdit()
    self.trim_button = QPushButton("Send Trim Tab")
    self.trim_button.clicked.connect(self.send_trim_tab)
    self.trim_input_layout = QVBoxLayout()
    self.trim_input_label = QLabel("Trim Tab Angle:")
    self.trim_input_label.setStyleSheet(input_label_style)
    self.trim_input_layout.addWidget(self.trim_input_label)
    self.trim_input_layout.addSpacing(small_spacing)
    self.trim_input_layout.addWidget(self.trim_input)
    self.trim_input_layout.addSpacing(small_spacing)
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

def init_emergency_controls_layout(self):
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
        btn.setStyleSheet(styles.command_button_style)
        btn.clicked.connect(lambda checked, cmd=command: self.copy_to_clipboard(cmd))
        self.command_buttons.append(btn)
        
        # Add to grid layout (2 columns)
        row = i // 2
        col = i % 2
        self.commands_grid.addWidget(btn, row, col)
        
        return self.commands_grid
    
def init_left_bar(self):
    return 
