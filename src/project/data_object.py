from PyQt5 import QtCore
from PyQt5.QtWidgets import QLabel
import pyqtgraph as pg
# import time
# from datetime import datetime
import os
import csv
import project.config as cg

graph_margin = 0.2

def create_label(title, min_width=None, max_height=None):
    if (min_width is None): min_width = cg.value_label_min_width
    if (max_height is None): max_height = cg.value_label_max_height
    if (min_width <= 0 or max_height <= 0): raise ValueError
    label = QLabel(title)
    label.setMinimumWidth(min_width)
    label.setMaximumHeight(max_height)
    label.setAlignment(QtCore.Qt.AlignLeft)
    label.setStyleSheet(cg.value_style)
    return label

def create_line(graph_obj, name, x_data, y_data, colour, line_width, line_dashed, symbol_brush = None, symbol = None):  
    '''
    Creates and returns a pyqt5 line attached to the given graph
    '''
    try:
        if colour is not None:
            pen = pg.mkPen(colour, width=line_width, style=QtCore.Qt.DashLine if line_dashed else None)

        new_line = graph_obj.graph.plot( # a line is a PlotDataItem
            x_data,
            y_data,
            name=name,
            pen=pen if colour is not None else None, # no line colour indicates no line
            symbolBrush=symbol_brush,
            symbol=symbol if symbol else None
        )        
        return new_line
        
    except Exception as e:
        raise ValueError(f"Error creating line: {e}")
    
def create_graph(title, x_label, y_label, title_style = cg.graph_title_style, label_style = cg.graph_label_style):
    graph = pg.PlotWidget()
    graph.setBackground(cg.graph_bg)
    graph.setMinimumSize(cg.graph_min_width, cg.graph_min_height)
    graph.getPlotItem().getViewBox().setMouseEnabled(False, False)
    graph.setTitle(title, color=title_style[0], size=title_style[1])
    graph.setLabel("left", y_label, **label_style)
    graph.setLabel("bottom", x_label, **label_style)
    graph.addLegend()
    graph.showGrid(x=True, y=True)
    return graph

# data is a dictionary with values = data logged, keys = time logged
class GraphObject: # struct which keeps together objects needed for a graph
    def __init__(self, y_name, x_name, y_units, x_units, minn, maxn, dropdown_label = None): # data = history?
        '''
        Initialization for GraphObject\n
        minn : minimum data value expected over graph lifetime\n
        maxn : maximum data value expected over graph lifetime
        '''
        self.x_name = x_name
        self.y_name = y_name
        self.x_units = x_units
        self.y_units = y_units

        # NOTE: minn and maxn are not used currently - limit y-range using these?
        # Currently I'm not setting y-range with these values because that turns the autorange off
        self.minn = minn # min data value expected
        self.maxn = maxn # max data value expected

        self.initialized = False # indicates if graph widget was created or not
        self.visible = False
        if dropdown_label is None:
            self.dropdown_label = self.y_name
        else:
            self.dropdown_label = dropdown_label
        return
    
    def initialize(self):
        self.graph = create_graph(self.dropdown_label if self.dropdown_label != self.x_name else f"{self.x_name} vs. {self.y_name}", f"{self.x_name} ({self.x_units})" if self.x_units else f"{self.x_name}", 
                                  f"{self.y_name} ({self.y_units})" if self.y_units else f"{self.y_name}")
        self.graph.hide()
        self.initialized = True 

    def update_xlim(self, begin, end):
        self.graph.setXRange(begin, end)

    def hide(self):
        '''Disallow plotting & line updates'''
        self.visible = False
        self.graph.setVisible(False)

    def show(self):
        '''Allow plotting & line updates'''
        self.visible = True
        self.graph.setVisible(True)

    def isVisible(self):
        return self.visible

class DataObject:
    def __init__(self, name, dp, units, parsing_fn, line_dashed = False, line_colour = None, symbol_brush = None, has_label = True, graph: GraphObject = None):
        self.name = name
        self.dp = dp # number of dp to round to
        self.units = units if units else ""
        self.parsing_fn = parsing_fn
        self.line_dashed = line_dashed # boolean indicating whether line should be dashed or not
        self.line_colour = line_colour # if not graphed, doesn't need line colour
        self.graph_obj = graph # if not graphed, doesn't need a graph
        # if (line_colour is None and graph is not None):
        #     raise ValueError("DataObject __init__: Given a graph, but not a line colour")
        self.data = {} # no data when initialized: of form time:value
        self.current = None # key of most recent data entry datapoint
        self.line = None
        self.has_label = has_label
        self.symbol_brush = symbol_brush
        return 
    
    def initialize(self, timestamp = None):
        if self.graph_obj:
            if not self.graph_obj.initialized: self.graph_obj.initialize()
            self.line = create_line(self.graph_obj, self.name, [], [], self.line_colour, cg.linewidth, self.line_dashed, self.symbol_brush, symbol = 'o' if self.symbol_brush else None) # should automatically create line w/ empty data
        if self.has_label:
            self.label = create_label(self.name + ": ---- ") # should automatically create label
        else: self.label = None
        
    # Return a tuple with the time:value of the most current data point collected
    def get_current(self):
        val = None
        if self.current and self.data.get(self.current) is not None:
            val = round(self.data.get(self.current), self.dp)
        return self.current, val # returns the time, value of most recently logged datapoint
    
    # add a datapoint to self.data
    def add_datapoint(self, x, y):
        self.data[x] = y
        self.current = x
        if (self.graph_obj and self.graph_obj.graph.isVisible()):
            self.update_line_data()
        return
    
    def remove_datapoint(self, x):
        try:
            del self.data[x]
        except KeyError:
            print(f"ERR - trying to apply remove_datapoint() on a point which does not exist")
    
    def update_line_data(self):
        if (self.line is not None):
            values = []
            for key in self.data.keys():
                values.append(self.data[key])
            self.line.setData(list(self.data.keys()), values)
        return

    def parse_frame(self, current_time, data_line, parsed_dict=None):
        # calls the specific parsing_fn that belongs to this object
        # calls add_datapoint to add data
        if (parsed_dict is not None): # for can frames which contain multiple data values
            data = round(parsed_dict[self.name], self.dp)
        else: # for can frames which hold only a single value
            raw_data = data_line.split(']')[-1].strip().split()
            data = self.parsing_fn(''.join(raw_data))
            if self.dp is not None: # for values which do not have variable dp (ie. not salinity)
                data = round(data, self.dp)
        
        self.add_datapoint(current_time, data)
        return

    # if there is a graph associated with this object and there are some data points outside of the graph window,
    # remove those points - make sure to log those points before calling update_data
    def update_data(self, current_time, scroll_window):
        keys = list(self.data.keys())
        for key in keys:
            if (key < (current_time - scroll_window - 5)): # if value is outside graph plus some margin of time
                del self.data[key]
        self.update_line_data()
        return
    
    def update_label(self):
        if (self.label is not None):
            self.label.setText(
                f"{self.name}: {self.get_current()[1]} {self.units}"
            )
        return

    
class AISObject(DataObject): # NOTE: does this class need to take all arguments of parent class?
    def __init__(self, name, dp, units, parsing_fn, other_brush, log_value_headers: list[str], polaris_brush = None, graph: GraphObject = None):
        super().__init__(name, dp, units, None, has_label = False, line_colour = None, symbol_brush = other_brush, graph = graph)
        # below all done by super
        # self.name = name
        # self.dp = dp # number of dp to round to
        # self.units = units if units else ""
        # self.parsing_fn = parsing_fn
        # self.line_dashed = line_dashed # boolean indicating whether line should be dashed or not
        # self.line_colour = line_colour # if not graphed, doesn't need line colour
        # self.graph_obj = graph # if not graphed, doesn't need a graph
        # if (line_colour is None and graph is not None):
        #     raise ValueError("DataObject __init__: Given a graph, but not a line colour")
        # no data when initialized: of form time:value
        # self.current = None # key of most recent data entry datapoint
        self.brush = other_brush
        self.polaris_brush = polaris_brush if polaris_brush is not None else other_brush
        self.polaris_pos = (None, None) # tuple with polaris's (longitude, latitude)
        self.dataset_list = [] # a list of dictionaries, where each dictionary contains all data for one frame
        self.dataset = {} # same as above but is a dictionary containing a bunch of frames instead, of the form MSID: dictionary
        self.log_value_headers = log_value_headers

    def initialize(self, timestamp = None):
        super().initialize()
        if timestamp is None: 
            print("ERROR: AISObject.initialize received null timestamp")
        self.init_logging(timestamp)
        # self.polaris_line = self.add_line("POLARIS", [], [], None, None, False, symbol_brush = self.polaris_brush, symbol = 'x')
        self.polaris_line = create_line(self.graph_obj, "POLARIS", [], [], None, None, False, self.polaris_brush, 'x')

    def add_frame(self, x, y, key, data, x_key):
        '''x_key is the key for the value containing the x_value'''
        if x is None or y is None:
            print("ERR - add_frame() received None for lat or lon from AIS frame")
        if (key in self.dataset): # if ship already exists in dataset
            self.remove_datapoint(self.dataset[key][x_key]) # remove old lon/lat value from graph
        
        self.dataset[key] = data # NOTE: instead of appending, replace on ship SID - should self.dataset be a dict instead? Check that everything works like this
        # TODO: note that self.data is a dict with x: y - to replace pts, remove old pt using key(old longitude), then update longitude and put new point using new longitude
        self.add_datapoint(x, y) # add new (lon, lat) of ship to list of datapoints to graph 

    def add_line(self, name, x_data, y_data, colour, line_width, line_dashed, symbol_brush = None, symbol = None):
        return create_line(self.graph_obj, name, x_data, y_data, colour, line_width, line_dashed, symbol_brush, symbol)

    def clear_data(self):
        self.data.clear() # remove all old data

    def init_logging(self, timestamp):       
        """Initialize CSV logging files with timestamped names"""
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # Create timestamped filename       
        # AIS log file (log file only for AIS values)
        self.ais_log_file = os.path.join('logs', f'ais_values_{timestamp}.csv')

        # Header names
        values_header = ['Timestamp', 'Elapsed_Time_s'] + self.log_value_headers

        # Write headers to file
        with open(self.ais_log_file, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(values_header)
            csv_file.flush()
        
        print(f"AIS logging initialized: {self.ais_log_file}")

    def log_data(self, timestamp, elapsed_time):
        '''log AIS data from current batch into csv file''' 
        if (not self.dataset): return # No data in dataset
        try:
            with open(self.ais_log_file, 'a', newline='') as csv_file:
                writer = csv.writer(csv_file)
                for frame in self.dataset.values(): # for each frame in the dataset
                    # print("frame = ", frame)
                    values = [timestamp, elapsed_time]
                    for key in frame.keys(): # get the keys in data
                        if frame[key] is None:
                            values.append("None")
                        else: values.append(frame[key])
                    writer.writerow(values)
                csv_file.flush()  # Flush immediately to prevent data loss
        except Exception as e:
            print(f"Error logging AIS values: {e}")

        print("AIS data logged!")
        # self.dataset.clear() # Don't clear data 
        return
    
    def update_polaris_pos(self, lon, lat):
        if lon is None or lat is None: 
            print("ERR - update_polaris_pos(): POLARIS lon or lat is None, its position cannot be graphed")
            return # if either is None, can't graph position - just return
        if self.graph_obj.isVisible():
            self.polaris_line.setData([lon], [lat])
        print("polaris_pos updated!")
        print("self.polaris_line = (", self.polaris_line.xData, ", ", self.polaris_line.yData, ")")
        