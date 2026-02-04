from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QTextEdit, QHBoxLayout, QCheckBox, QGridLayout, QComboBox,
    QSizePolicy
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import QTimer, Qt




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

def init_left_bar(self):
    return 
