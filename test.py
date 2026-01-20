from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QCheckBox, QGridLayout, QComboBox
)

from PyQt5.QtCore import QSize

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.combo_box = QComboBox(self)
        # list_view = self.combo_box.view()
        # # Set a fixed minimum size for the dropdown menu
        # list_view.setMinimumSize(QSize(250, 150))
        font = self.combo_box.font()
        font.setPointSize(18)  # Set the desired font size
        font.setBold(True)
        self.combo_box.setFont(font)
        self.combo_box.addItems(["Option 1", "Option 2", "Option 3", "Option 4"])

        self.combo_2 = QComboBox(self)
        font = self.combo_box.font()
        font.setPointSize(20)  # Set the desired font size
        font.setBold(True)
        self.combo_2.setFont(font)
        self.combo_2.addItems(["Option 1", "Option 2", "Option 3", "Option 4"])

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.combo_box)
        self.combo_box.currentIndexChanged.connect(lambda idx: self.printOnClick(idx, 1))
        self.combo_2.currentIndexChanged.connect(lambda idx: self.printOnClick(idx, 2))
        main_layout.addWidget(self.combo_2)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget) 

    def printOnClick(self, idx, which):
        print(f"combo #{which} switched to index {idx}")

app = QtWidgets.QApplication([])
main = MainWindow()
main.show()
app.exec()

# ====== Testing PyQtgraph ======
# import pyqtgraph as pg
# from PyQt5 import QtWidgets

# from random import randint

# import pyqtgraph as pg
# from PyQt5 import QtCore, QtWidgets

# class MainWindow(QtWidgets.QMainWindow):
#     def __init__(self):
#         super().__init__()

#         # Temperature vs time dynamic plot
#         self.plot_graph = pg.PlotWidget() # create PlotWidget object
#         self.plot_graph.getPlotItem().getViewBox().setMouseEnabled(False, False) # disable graph interaction
#         self.setCentralWidget(self.plot_graph) # set plot_graph to be main widget of window
#         self.plot_graph.setBackground("w") # set background color to white
#         pen = pg.mkPen(color=(255, 0, 0)) # set line color (pen)
#         self.plot_graph.setTitle("Temperature vs Time", color="b", size="20pt") # set title of graph
#         styles = {"color": "red", "font-size": "18px"} # create a style sheet
#         self.plot_graph.setLabel("left", "Temperature (°C)", **styles) # create y-axis label, set its style
#         self.plot_graph.setLabel("bottom", "Time (min)", **styles) # create x-axis label, set its style
#         self.plot_graph.addLegend() # must be called before calling plot to add legend to graph
#         self.plot_graph.showGrid(x=True, y=True) # set grid on graph
#         self.plot_graph.setYRange(20, 40) # fix y-range on graph
#         self.time = list(range(10)) # create a list of times from 1-10 for time
#         self.temperature = [randint(20, 40) for _ in range(10)] # create a length 10 list of random data between 20-40 for temp
#         # Get a line reference
#         self.line = self.plot_graph.plot( # create a line for the plot; save reference to line in var self.line
#             self.time, # x-data
#             self.temperature, # y-data
#             name="Temperature Sensor", # data/line name
#             pen=pen, # brush/style used for this line
#             symbol="+", # datapoint markers
#             symbolSize=15, 
#             symbolBrush="b",
#         )

#         self.new_line = self.plot_graph.plot( # create a line for the plot; save reference to line in var self.line
#             # self.time, # x-data
#             self.temperature, # y-data
#             name="Second line", # data/line name
#             pen=pen, # brush/style used for this line
#             symbol="o", # datapoint markers
#             symbolSize=15, 
#             symbolBrush="g",
#         )
#         # Add a timer to simulate new temperature measurements
#         self.timer = QtCore.QTimer() # timer object
#         self.timer.setInterval(300) # set timer to timeout every 300 milliseconds
#         self.timer.timeout.connect(self.update_plot) # call update plot on timeout
#         self.timer.start() # start timer

#     def update_plot(self):
#         self.time = self.time[1:] # remove first element of self.time
#         self.time.append(self.time[-1] + 1) # add new time to the end of self.time
#         self.temperature = self.temperature[1:] # remove first element of self.temperature
#         self.temperature.append(randint(20, 40)) # add new random data point
#         self.line.setData(self.time, self.temperature) # graph the new data

# app = QtWidgets.QApplication([])
# main = MainWindow()
# main.show()
# app.exec()

# ==== Testing for setting can network up remotely ====

# import paramiko

# hostname = "192.168.0.10"
# username = "sailbot"
# password = "sailbot"
# can_line = "can0"

# if __name__ == "__main__":
#     client = paramiko.SSHClient()
#     client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     try:
#         client.connect(hostname, username=username, password=password)
#         print("Connected to host...")
#         transport = client.get_transport()
#         # session = transport.open_session()
#         # session.exec_command("bash sailbot_workspace/scripts/canup.sh -l")
#         session = transport.open_session()
#         print("Sesson opened")
#         session.exec_command(f"candump {can_line}")
#         print("Command executed")
#         if session.recv_ready():
#             line = session.recv(1024).decode()
#             print(f"line = {line}")
#         else:
#             print(f"session not recv_ready")
#             # print(f"stderr = {stderr}")
#         # print(f"stdin: {stdin.read().decode().strip()}")
#         # print(f"stoud: {stdout.read().decode().strip()}")
#         # print(f"stderr: {stderr.read().decode().strip()}")
#     except Exception as e:
#         print(f"Error: {e}")
#     finally:
#         client.close()


# === Multiprocessing Basics ===
#import multiprocessing
#
# def hello(name, date, location):
#     print("Hello, ", name, " at ", date, " in ", location)

# if __name__ == "__main__":
#     p = multiprocessing.Process(target=hello, args=("Breanne", "now", "Rome"))
#     p.start()
#     # p.join()
