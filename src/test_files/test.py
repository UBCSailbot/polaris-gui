# ===== Example AIS Graph (Basic) ===== 
# ===== Testing ScatterPlot =====
from random import randint, uniform

import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets, QtGui

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.time = list(range(10)) # create a list of times from 1-10 for time
        x_data = [uniform(-180, 180) for i in range(10)] 
        y_data = [uniform(-90, 90) for j in range(10)] # randint(1, 9) for i in range(0, 10)]
        print("longitude: ", x_data)
        print("latitude: ", y_data)

        polaris_pen = pg.mkPen(color='r', width=5) # set point border color (red)
        polaris_brush = pg.mkBrush(color='r')
        other_pen = pg.mkPen(color='b', width=1)
        other_brush = pg.mkBrush(color='b')

        '''
        Optional list of dicts. Each dict specifies parameters for a single spot: {‘pos’: (x,y), ‘size’, ‘pen’, ‘brush’, ‘symbol’}. 
        This is just an alternate method of passing in data for the corresponding arguments.
        '''
        spots = []
        for pt in self.time:
            if (pt == 5):
                spots.append({'pos': (x_data[pt - 1], y_data[pt - 1]), 'size':10, 'pen': polaris_pen, 'brush': polaris_brush, 'symbol': 'x'}) # Each point can have its own brush, pen, symbol
            else:
                spots.append({'pos': (x_data[pt - 1], y_data[pt - 1]), 'size':10, 'pen': other_pen, 'brush': other_brush, 'symbol': 'o'})

        # Graph using PlotWidget
        self.plot_widget = pg.PlotWidget()

        # setup - all from create_graph function
        self.plot_widget.setBackground("w")
        self.plot_widget.getPlotItem().getViewBox().setMouseEnabled(False, False)
        self.plot_widget.setTitle("Ship Positions", color='black')
        self.plot_widget.setLabel("left", "Latitude")
        self.plot_widget.setLabel("bottom", "Longitude")
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True)

        # create line objects for polaris & for other ships; add data
        # TODO: copy necessary bits from create_line here
        other_line = self.plot_widget.plot(
            x_data, 
            y_data,
            name="other ships",
            pen=None,
            symbolBrush=other_brush,
            symbol = "o"
        )

        polaris_line = self.plot_widget.plot(
            name="Polaris",
            pen=None,
            symbolBrush=polaris_brush,
            symbol="x"
        )

        polaris_line.setData([0], [0])

        
        # Graph using ScatterPLotItem
        # self.plot_widget = pg.PlotWidget()
        # self.plot_widget.getPlotItem().getViewBox().setMouseEnabled(False, False) # disable graph interaction
        # self.plot_widget.setBackground("w") # set background color to white
        # self.plot_widget.setTitle("Longitude vs. Latitude", color="b", size="20pt") # set title of graph
        # styles = {"color": "red", "font-size": "18px"} # create a style sheet
        # self.plot_widget.setLabel("left", "Latitude (DD)", **styles) # create y-axis label, set its style
        # self.plot_widget.setLabel("bottom", "Longitude (DD)", **styles) # create x-axis label, set its style
        # self.plot_widget.addLegend() # must be called before calling plot to add legend to graph
        # self.plot_widget.showGrid(x=True, y=True) # set grid on graph

        # self.plot_graph = pg.ScatterPlotItem(spots) # create ScatterPlot object
        # self.plot_widget.addItem(self.plot_graph)
        
        self.setCentralWidget(self.plot_widget) 

app = QtWidgets.QApplication([])
main = MainWindow()
main.show()
app.exec()

# # ===== Testing ScatterPlot =====
# from random import randint

# import pyqtgraph as pg
# from PyQt5 import QtCore, QtWidgets, QtGui

# class MainWindow(QtWidgets.QMainWindow):
#     def __init__(self):
#         super().__init__()

#         self.time = list(range(10)) # create a list of times from 1-10 for time
#         y_data = [2, 3, 3, 2, 1, 7, 9, 9, 9, 6] # randint(1, 9) for i in range(0, 10)]
#         print(y_data)

#         polaris_pen = pg.mkPen(color='r', width=5) # set point border color (red)
#         polaris_brush = pg.mkBrush(color='r')
#         other_pen = pg.mkPen(color='b', width=1)
#         other_brush = pg.mkBrush(color='b')

#         # Arrow - note that it is kinda pointing wrong; the arrow points to the point, not away from the point
#         vector = pg.makeArrowPath(headLen=0.07, headWidth=0.04, tailLen=0.2, tailWidth=0.01)


#         '''
#         Optional list of dicts. Each dict specifies parameters for a single spot: {‘pos’: (x,y), ‘size’, ‘pen’, ‘brush’, ‘symbol’}. 
#         This is just an alternate method of passing in data for the corresponding arguments.
#         '''
#         spots = []
#         for pt in self.time:
#             if (pt == 5):
#                 spots.append({'pos': (pt - 2, y_data[pt - 1]), 'size':300, 'pen': polaris_pen, 'brush': polaris_brush, 'symbol': vector}) # Each point can have its own brush, pen, symbol
#             else:
#                 spots.append({'pos': ((pt % 5), y_data[pt - 1]), 'size':8, 'pen': other_pen, 'brush': other_brush, 'symbol': 'o'})

#         # Graph
#         self.plot_widget = pg.PlotWidget()
#         self.plot_widget.getPlotItem().getViewBox().setMouseEnabled(False, False) # disable graph interaction
#         self.plot_widget.setBackground("w") # set background color to white
#         self.plot_widget.setTitle("Test Data vs Time", color="b", size="20pt") # set title of graph
#         styles = {"color": "red", "font-size": "18px"} # create a style sheet
#         self.plot_widget.setLabel("left", "Temperature (°C)", **styles) # create y-axis label, set its style
#         self.plot_widget.setLabel("bottom", "Time (min)", **styles) # create x-axis label, set its style
#         self.plot_widget.addLegend() # must be called before calling plot to add legend to graph
#         self.plot_widget.showGrid(x=True, y=True) # set grid on graph
#         self.plot_widget.setYRange(0, 10) # fix y-range on graph


#         self.plot_graph = pg.ScatterPlotItem(spots) # create ScatterPlot object
#         self.plot_widget.addItem(self.plot_graph)
        
#         self.setCentralWidget(self.plot_widget) 
        
#         # Add a timer to simulate new temperature measurements
#         self.timer = QtCore.QTimer() # timer object
#         self.timer.setInterval(300) # set timer to timeout every 300 milliseconds
#         self.timer.timeout.connect(self.update_plot) # call update plot on timeout
#         self.timer.start() # start timer

#     def update_plot(self):
#         pass
#         # self.time = self.time[1:] # remove first element of self.time
#         # self.time.append(self.time[-1] + 1) # add new time to the end of self.time
#         # self.temperature = self.temperature[1:] # remove first element of self.temperature
#         # self.temperature.append(randint(20, 40)) # add new random data point
#         # self.line.setData(self.time, self.y_data) # graph the new data

# app = QtWidgets.QApplication([])
# main = MainWindow()
# main.show()
# app.exec()


# ====== Testing Dropdowns (QComboBox) =======
# from PyQt5 import QtWidgets
# from PyQt5.QtWidgets import (
#     QWidget, QLabel, QVBoxLayout, QHBoxLayout, QCheckBox, QGridLayout, QComboBox
# )

# from PyQt5.QtCore import QSize

# class MainWindow(QtWidgets.QMainWindow):
#     def __init__(self):
#         super().__init__()

#         self.combo_box = QComboBox(self)
#         # list_view = self.combo_box.view()
#         # # Set a fixed minimum size for the dropdown menu
#         # list_view.setMinimumSize(QSize(250, 150))
#         font = self.combo_box.font()
#         font.setPointSize(18)  # Set the desired font size
#         font.setBold(True)
#         self.combo_box.setFont(font)
#         self.combo_box.addItems(["Option 1", "Option 2", "Option 3", "Option 4"])

#         self.combo_2 = QComboBox(self)
#         font = self.combo_box.font()
#         font.setPointSize(20)  # Set the desired font size
#         font.setBold(True)
#         self.combo_2.setFont(font)
#         self.combo_2.addItems(["Option 1", "Option 2", "Option 3", "Option 4"])

#         main_widget = QWidget()
#         main_layout = QHBoxLayout()
#         main_layout.addWidget(self.combo_box)
#         self.combo_box.currentIndexChanged.connect(lambda idx: self.printOnClick(idx, 1))
#         self.combo_2.currentIndexChanged.connect(lambda idx: self.printOnClick(idx, 2))
#         main_layout.addWidget(self.combo_2)
#         main_widget.setLayout(main_layout)
#         self.setCentralWidget(main_widget) 

#     def printOnClick(self, idx, which):
#         print(f"combo #{which} switched to index {idx}")

# app = QtWidgets.QApplication([])
# main = MainWindow()
# main.show()
# app.exec()

# ====== Testing PyQtgraph ======
# import pyqtgraph as pg
# from PyQt5 import QtWidgets

# from random import randint

# import pyqtgraph as pg
# from PyQt5 import QtCore, QtWidgets

# class MainWindow(QtWidgets.QMainWindow):
#     def __init__(self):
#         super().__init__()

#         x = [0, 1, 2, 3, 4, 5, 6, 7, 8]
#         y = [3, 5, 2, 1, 5, 7, 8, 3, 4]

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
#         # self.time = self.time[1:] # remove first element of self.time
#         # self.time.append(self.time[-1] + 1) # add new time to the end of self.time
#         # self.temperature = self.temperature[1:] # remove first element of self.temperature
#         # self.temperature.append(randint(20, 40)) # add new random data point
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
