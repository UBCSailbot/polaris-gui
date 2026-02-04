from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QTextEdit, QHBoxLayout, QCheckBox, QGridLayout, QComboBox,
    QSizePolicy
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import QTimer, Qt

from config import *

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


def init_left_bar(self):
    return 
