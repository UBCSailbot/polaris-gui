# -- Source - https://stackoverflow.com/a/49223444
# -- Posted by eyllanesc, modified by community. See post 'Timeline' for change history
# -- Retrieved 2026-05-30, License - CC BY-SA 3.0
# https://stackoverflow.com/questions/49219278/pyqtgraph-move-origin-of-arrowitem-to-local-center

import numpy as np
import math
# from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets, QtGui


class MyArrowItem(pg.ArrowItem):
    def paint(self, p, *args):
        p.translate(-2 * self.boundingRect().center())
        pg.ArrowItem.paint(self, p, *args)

def create_arrow_item(angle: int, headLen: int, tailLen: int, tailWidth: int, headWidth: int, pen: pg.QtGui.QPen, brush: pg.QtGui.QBrush) -> MyArrowItem:
    return MyArrowItem(angle=angle, headLen=headLen, tailLen=tailLen, tailWidth=tailWidth, headWidth=headWidth, pen=pen, brush=brush)

# Sample data points
# x = np.array([1, 2, 3, 4, 5, -2, -2, 10, 10])
# y = np.array([2, 4, 5, 5, 3, -1, 8, -1, 8])
desired_heading = np.array([180, 180, 180, 180, 180])
actual_heading = np.array([130, 135, 165, 222.5, 205])

lat_ref = 49.2722
lon_ref = -123.1985
num_dp = 500
lat_test_sine_path = [lat_ref + (0.00001 * (i * 0.1)) for i in range(0, num_dp)]
lon_test_sine_path = [lon_ref + (0.00001 * math.sin(i * 0.1)) for i in range(0, num_dp)]
d_heading_sine_path = [90 * math.sin(i) for i in range(0, num_dp)]
a_heading_sine_path = [90, 90, 90, 45, 45, 45, 90, 90, 90, 135, 135, 135] * num_dp
    
y = [(lat_data - lat_ref) * 110562 for lat_data in lat_test_sine_path]
x = [(lon_data - lon_ref) * math.cos(math.radians(lat_ref)) * 111320 for lon_data in lon_test_sine_path]
print("lat[0:5] = ", lat_test_sine_path[0:5])
print("lon[0:5] = ", lon_test_sine_path[0:5])
print("x[0:5] = ", x[0:5])
print("y[0:5] = ", y[0:5])

app = QtWidgets.QApplication([])

p = pg.PlotWidget()
p.showGrid(x = True, y = True, alpha = 0.3)
p.setBackground('w')

line = p.plot(
    x,
    y,
    name="Path",
    pen=None, # no line colour = no line
    symbol='o',
    symbolBrush = 'black'
)

# b = MyArrowItem(angle=0, headLen=20, tailLen=40, tailWidth=10, headWidth=10, pen={'color': 'w', 'width': 3})
last_x = None
last_y = None
last_pix_x = None
last_pix_y = None
last_win_x = None
last_win_y = None
last_glo_x = None
last_glo_y = None

# for i in range(0, len(x)):
#     if len(desired_heading) > i:
#         arrow = create_arrow_item(angle=desired_heading[i], headLen=20, tailLen=45, tailWidth=8, headWidth=8, pen={'color': 'w', 'width': 3}, brush='b')
#         actual_arrow = create_arrow_item(angle=actual_heading[i], headLen=20, tailLen=45, tailWidth=8, headWidth=8, pen={'color': 'w', 'width': 3}, brush='r')
#         arrow.setPos(x[i], y[i])
#         actual_arrow.setPos(x[i], y[i])
#         p.addItem(arrow)
#         p.addItem(actual_arrow)

#     scene_pixel = p.plotItem.vb.mapViewToScene(pg.Point(x[i], y[i]))
#     window_pixel = p.mapToParent(scene_pixel.toPoint())
#     global_screen_pixel = p.mapToGlobal(scene_pixel.toPoint())

#     # print(f"scene_pixel({x[i]},{y[i]}): ", scene_pixel)
#     if (last_x is not None) and (last_y is not None):
#         print(f"distance from ({last_x},{last_y}) to ({x[i]}, {y[i]}) = ", math.sqrt((last_x - x[i]) ** 2 + (last_y - y[i]) ** 2))
#         print(f"screen pixel distance from ({last_x},{last_y}) to ({x[i]}, {y[i]}) = ", math.sqrt((last_pix_x - scene_pixel.x()) ** 2 + (last_pix_y - scene_pixel.y()) ** 2))
#         print(f"window pixel distance from ({last_x},{last_y}) to ({x[i]}, {y[i]}) = ", math.sqrt((last_win_x - window_pixel.x()) ** 2 + (last_win_y - window_pixel.y()) ** 2))
#         print(f"global pixel distance from ({last_x},{last_y}) to ({x[i]}, {y[i]}) = ", math.sqrt((last_glo_x - global_screen_pixel.x()) ** 2 + (last_glo_y - global_screen_pixel.y()) ** 2))
    
#     last_x = x[i]
#     last_y = y[i]
#     last_pix_x = scene_pixel.x()
#     last_pix_y = scene_pixel.y()
#     last_win_x = window_pixel.x()
#     last_win_y = window_pixel.y()
#     last_glo_x = global_screen_pixel.x()
#     last_glo_y = global_screen_pixel.y()

# vb = p.plotItem.vb

# 1. Map to Scene Pixels (local widget pixel system)
# scene_pixel = vb.mapViewToScene(pg.Point(x[0], y[0]))
# print(f"scene_pixel({x[0]},{y[0]}): ", scene_pixel)
# scene_pixel = vb.mapViewToScene(pg.Point(x[1], y[1]))
# print(f"scene_pixel({x[1]},{y[1]}): ", scene_pixel)
# scene_pixel = vb.mapViewToScene(pg.Point(x[2], y[2]))
# print(f"scene_pixel({x[2]},{y[2]}): ", scene_pixel)
# scene_pixel = vb.mapViewToScene(pg.Point(x[3], y[3]))
# print(f"scene_pixel({x[3]},{y[3]}): ", scene_pixel)
# scene_pixel = vb.mapViewToScene(pg.Point(x[4], y[4]))
# print(f"scene_pixel({x[4]},{y[4]}): ", scene_pixel)

layout = QtWidgets.QHBoxLayout()
layout.addWidget(p)
layout.addWidget(QtWidgets.QLabel("sample label"))

main_widget = QtWidgets.QWidget()
main_widget.setLayout(layout)

w = QtWidgets.QMainWindow()
w.show()
w.resize(640, 480)
# w.setCentralWidget(p)
w.setCentralWidget(main_widget)
w.setWindowTitle('pyqtgraph example: ArrowItem')

# a = MyArrowItem(angle=0, tipAngle=60, headLen=40, tailLen=40, tailWidth=20, pen={'color': 'w', 'width': 3},  brush='r')
# # b is the chosen arrow (can modify this later if necessary)
# b = MyArrowItem(angle=-160, headLen=20, tailLen=40, tailWidth=10, headWidth=10, pen={'color': 'w', 'width': 3})
# c = MyArrowItem(angle=45, tipAngle=30, headLen=20, headWidth=10, tailLen=40, tailWidth=10, pen={'color': 'w', 'width': 3},  brush='g')

# a.setPos(0,0)
# b.setPos(0,0)
# c.setPos(0, 0)

# p.addItem(a)
# p.addItem(b)
# p.addItem(c)

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    app.exec()


# # ===== Example PID Graph (Basic) ===== 
# # NOTE: I might want to use a scatterplot for this
# import pyqtgraph as pg
# from pyqtgraph.Qt import QtGui
# import numpy as np

# # 1. Initialize plot and scatter plot item
# app = pg.mkQApp("Arrow Scatter Plot")
# plt = pg.plot()
# plt.setBackground("w")
# sp = pg.ScatterPlotItem()

# plt.addItem(sp)

# # 2. Create arrow QPainterPath and rotate it
# tr = QtGui.QTransform()
# tr.rotate(45) # Pointing up-right (45 degrees)
# thick_arrow_path = tr.map(pg.makeArrowPath(headLen = 20, headWidth = 5, tailLen = 20, tailWidth = 5, baseAngle = 0))
# arrow_path = tr.map(pg.makeArrowPath(headLen = 15, headWidth = 5, tailLen = 15, tailWidth = 3, baseAngle = 0))
# thin_arrow_path = tr.map(pg.makeArrowPath(headLen = 10, headWidth = 5, tailLen = 30, tailWidth = 3, baseAngle = 0))

# # 3. Define data
# x = np.array([1, 2, 3, 4, 5])
# y = np.array([2, 4, 1, 5, 3])

# # 4. Set data with the custom arrow symbol
# sp.setData(
#     x=x, 
#     y=y, 
#     symbol=[thin_arrow_path, arrow_path, thick_arrow_path, arrow_path, arrow_path], 
#     # symbol=arrow_path,
#     size=25, 
#     symbolBrush='y', 
#     symbolPen='w'
# )

# if __name__ == '__main__':
#     pg.exec()


# from random import randint, uniform

# import pyqtgraph as pg
# from PyQt5 import QtCore, QtWidgets, QtGui

# class MainWindow(QtWidgets.QMainWindow):
#     def __init__(self):
#         super().__init__()

#         self.time = list(range(10)) # create a list of times from 1-10 for time
#         x_data = [uniform(-180, 180) for i in range(10)] 
#         y_data = [uniform(-90, 90) for j in range(10)] # randint(1, 9) for i in range(0, 10)]
#         print("longitude: ", x_data)
#         print("latitude: ", y_data)

#         polaris_pen = pg.mkPen(color='r', width=5) # set point border color (red)
#         polaris_brush = pg.mkBrush(color='r')
#         other_pen = pg.mkPen(color='b', width=1)
#         other_brush = pg.mkBrush(color='b')

#         '''
#         Optional list of dicts. Each dict specifies parameters for a single spot: {‘pos’: (x,y), ‘size’, ‘pen’, ‘brush’, ‘symbol’}. 
#         This is just an alternate method of passing in data for the corresponding arguments.
#         '''
#         # spots = []
#         # for pt in self.time:
#         #     if (pt == 5):
#         #         spots.append({'pos': (x_data[pt - 1], y_data[pt - 1]), 'size':10, 'pen': polaris_pen, 'brush': polaris_brush, 'symbol': 'x'}) # Each point can have its own brush, pen, symbol
#         #     else:
#         #         spots.append({'pos': (x_data[pt - 1], y_data[pt - 1]), 'size':10, 'pen': other_pen, 'brush': other_brush, 'symbol': 'o'})

#         # Graph using PlotWidget
#         self.plot_widget = pg.PlotWidget()

#         # setup - all from create_graph function
#         self.plot_widget.setBackground("w")
#         self.plot_widget.getPlotItem().getViewBox().setMouseEnabled(False, False)
#         self.plot_widget.setTitle("Ship Positions", color='black')
#         self.plot_widget.setLabel("left", "Latitude")
#         self.plot_widget.setLabel("bottom", "Longitude")
#         self.plot_widget.addLegend()
#         self.plot_widget.showGrid(x=True, y=True)

#         # create line objects for polaris & for other ships; add data
#         # TODO: copy necessary bits from create_line here
#         other_line = self.plot_widget.plot(
#             x_data, 
#             y_data,
#             name="other ships",
#             pen=None,
#             symbolBrush=other_brush,
#             symbol = "o"
#             # symbolSize=40
#         )

#         polaris_line = self.plot_widget.plot(
#             name="Polaris",
#             pen=None,
#             symbolBrush=polaris_brush,
#             symbol = "t"
#         )

#         arrow = pg.ArrowItem(angle=45, brush='y') # Points down
#         arrow.setPos(0, 0) # Position in data coordinates   
#         self.plot_widget.addItem(arrow)

#         polaris_line.setData([0], [0])

        
#         # Graph using ScatterPLotItem
#         # self.plot_widget = pg.PlotWidget()
#         # self.plot_widget.getPlotItem().getViewBox().setMouseEnabled(False, False) # disable graph interaction
#         # self.plot_widget.setBackground("w") # set background color to white
#         # self.plot_widget.setTitle("Longitude vs. Latitude", color="b", size="20pt") # set title of graph
#         # styles = {"color": "red", "font-size": "18px"} # create a style sheet
#         # self.plot_widget.setLabel("left", "Latitude (DD)", **styles) # create y-axis label, set its style
#         # self.plot_widget.setLabel("bottom", "Longitude (DD)", **styles) # create x-axis label, set its style
#         # self.plot_widget.addLegend() # must be called before calling plot to add legend to graph
#         # self.plot_widget.showGrid(x=True, y=True) # set grid on graph

#         # self.plot_graph = pg.ScatterPlotItem(spots) # create ScatterPlot object
#         # self.plot_widget.addItem(self.plot_graph)
        
#         self.setCentralWidget(self.plot_widget) 

# app = QtWidgets.QApplication([])
# main = MainWindow()
# main.show()
# app.exec()


# # ===== Example Heartbeat ===== 
# # from random import randint, uniform

# # import pyqtgraph as pg
# from PyQt5 import QtWidgets
# from PyQt5.QtWidgets import (
#     QVBoxLayout, QLabel, QWidget, QPushButton
# )

# from PyQt5.QtCore import QTimer


# from project.config import (
#     heartbeat_label_style, heartbeat_status_good_style,
#     heartbeat_status_bad_style
# )

# class MainWindow(QtWidgets.QMainWindow):
#     def __init__(self):
#         super().__init__()

#         # Create Heartbeat widget
#         central_widget = QWidget()
#         central_layout = QVBoxLayout()
#         # heartbeat_label = QLabel()
#         # heartbeat_label.setStyleSheet(heartbeat_label_style)
#         # heartbeat_label.setText(
#         #     f"""PDB Status: <font style=\"{heartbeat_status_bad_style}\">NOT RESPONDING</font>
#         #         <br>SAIL Status: <font style=\"{heartbeat_status_good_style}\">ALIVE<\font>"""
#         # )

#         pdb_timeout = 0

#         pdb_title_text = "PDB Status: "
#         sail_title_text = "SAIL Status: "

#         pdb_hb_label = QLabel()
#         pdb_hb_label.setStyleSheet(heartbeat_label_style)
#         pdb_hb_label.setText(f"{pdb_title_text} <font style=\"{heartbeat_status_bad_style}\">NOT RESPONDING</font>")

#         pdb_button = QPushButton("pdb heartbeat")
#         pdb_button.clicked.connect(lambda: self.on_clicked(pdb_hb_label, pdb_title_text))
        
#         sail_hb_label = QLabel()
#         sail_hb_label.setStyleSheet(heartbeat_label_style)
#         sail_hb_label.setText(f"{sail_title_text} <font style=\"{heartbeat_status_bad_style}\">NOT RESPONDING</font>")

#         sail_button = QPushButton("sail heartbeat")
#         sail_button.clicked.connect(lambda: self.on_clicked(sail_hb_label, sail_title_text))
        
#         central_layout.addWidget(pdb_hb_label)
#         central_layout.addWidget(sail_hb_label)
#         central_layout.addSpacing(15)
#         central_layout.addWidget(pdb_button)
#         central_layout.addWidget(sail_button)

#         central_widget.setLayout(central_layout)
#         self.setCentralWidget(central_widget) 

#         self.timer = QTimer()
#         self.timer.timeout.connect(self.update)
#         self.timer.start(300)

#     def on_clicked(self, label, title_text):
#         label.setText(title_text + f"<font style=\"{heartbeat_status_good_style}\">ALIVE</font>")
#         pass

#     def update(self):
#         # TODO: if more than 10 secs have passed, switch to disconnected
        
#         pass

# app = QtWidgets.QApplication([])
# main = MainWindow()
# main.show()
# app.exec()

# ===== Example AIS Graph (Basic) ===== 
# from random import randint, uniform

# import pyqtgraph as pg
# from PyQt5 import QtCore, QtWidgets, QtGui

# class MainWindow(QtWidgets.QMainWindow):
#     def __init__(self):
#         super().__init__()

#         self.time = list(range(10)) # create a list of times from 1-10 for time
#         x_data = [uniform(-180, 180) for i in range(10)] 
#         y_data = [uniform(-90, 90) for j in range(10)] # randint(1, 9) for i in range(0, 10)]
#         print("longitude: ", x_data)
#         print("latitude: ", y_data)

#         polaris_pen = pg.mkPen(color='r', width=5) # set point border color (red)
#         polaris_brush = pg.mkBrush(color='r')
#         other_pen = pg.mkPen(color='b', width=1)
#         other_brush = pg.mkBrush(color='b')

#         '''
#         Optional list of dicts. Each dict specifies parameters for a single spot: {‘pos’: (x,y), ‘size’, ‘pen’, ‘brush’, ‘symbol’}. 
#         This is just an alternate method of passing in data for the corresponding arguments.
#         '''
#         # spots = []
#         # for pt in self.time:
#         #     if (pt == 5):
#         #         spots.append({'pos': (x_data[pt - 1], y_data[pt - 1]), 'size':10, 'pen': polaris_pen, 'brush': polaris_brush, 'symbol': 'x'}) # Each point can have its own brush, pen, symbol
#         #     else:
#         #         spots.append({'pos': (x_data[pt - 1], y_data[pt - 1]), 'size':10, 'pen': other_pen, 'brush': other_brush, 'symbol': 'o'})

#         # Graph using PlotWidget
#         self.plot_widget = pg.PlotWidget()

#         # setup - all from create_graph function
#         self.plot_widget.setBackground("w")
#         self.plot_widget.getPlotItem().getViewBox().setMouseEnabled(False, False)
#         self.plot_widget.setTitle("Ship Positions", color='black')
#         self.plot_widget.setLabel("left", "Latitude")
#         self.plot_widget.setLabel("bottom", "Longitude")
#         self.plot_widget.addLegend()
#         self.plot_widget.showGrid(x=True, y=True)

#         # create line objects for polaris & for other ships; add data
#         # TODO: copy necessary bits from create_line here
#         other_line = self.plot_widget.plot(
#             x_data, 
#             y_data,
#             name="other ships",
#             pen=None,
#             symbolBrush=other_brush,
#             symbol = "o"
#             # symbolSize=40
#         )

#         polaris_line = self.plot_widget.plot(
#             name="Polaris",
#             pen=None,
#             symbolBrush=polaris_brush,
#             symbol = "t"
#         )

#         arrow = pg.ArrowItem(angle=45, brush='y') # Points down
#         arrow.setPos(0, 0) # Position in data coordinates   
#         self.plot_widget.addItem(arrow)

#         polaris_line.setData([0], [0])

        
#         # Graph using ScatterPLotItem
#         # self.plot_widget = pg.PlotWidget()
#         # self.plot_widget.getPlotItem().getViewBox().setMouseEnabled(False, False) # disable graph interaction
#         # self.plot_widget.setBackground("w") # set background color to white
#         # self.plot_widget.setTitle("Longitude vs. Latitude", color="b", size="20pt") # set title of graph
#         # styles = {"color": "red", "font-size": "18px"} # create a style sheet
#         # self.plot_widget.setLabel("left", "Latitude (DD)", **styles) # create y-axis label, set its style
#         # self.plot_widget.setLabel("bottom", "Longitude (DD)", **styles) # create x-axis label, set its style
#         # self.plot_widget.addLegend() # must be called before calling plot to add legend to graph
#         # self.plot_widget.showGrid(x=True, y=True) # set grid on graph

#         # self.plot_graph = pg.ScatterPlotItem(spots) # create ScatterPlot object
#         # self.plot_widget.addItem(self.plot_graph)
        
#         self.setCentralWidget(self.plot_widget) 

# app = QtWidgets.QApplication([])
# main = MainWindow()
# main.show()
# app.exec()

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
