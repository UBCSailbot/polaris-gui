import project.config as cg
from PyQt5.QtWidgets import QLabel

def create_hb_label(text, style_sheet) -> QLabel:
    label = QLabel(text=text)
    label.setStyleSheet(style_sheet)
    return label

class HeartbeatModule():
    def __init__(self, title_text):
        self.title_text = title_text
        self.label = None
        self.time_of_last = None # time of last received heartbeat frame

    def init_label(self):
        self.label = create_hb_label(self.title_text + f"<font style=\"{cg.heartbeat_status_bad_style}\">{cg.heartbeat_status_bad_text}</font>", 
                                     cg.heartbeat_label_style)

    def init_time(self, time):
        self.time_of_last = time - cg.heartbeat_timeout

    def initialized(self) -> bool:
        return self.label is not None and self.time_of_last is not None

    def set_not_responding(self):
        self.label.setText(self.title_text + f"<font style=\"{cg.heartbeat_status_bad_style}\">{cg.heartbeat_status_bad_text}</font>")

    def set_alive(self, time):
        self.label.setText(self.title_text + f"<font style=\"{cg.heartbeat_status_good_style}\">{cg.heartbeat_status_good_text}</font>")
        self.time_of_last = time