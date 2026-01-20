import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QLabel
)
from datetime import datetime

# class LineObject:
#     def __init__(self, line: plt.Line2D):
#         self.line = line
#         self.data = {} # no data when initialized: of form time:value
#         self.current = None # key of most recent data entry datapoint 

#     def get_current(self):
#         return self.current, self.data[self.current] # returns the time, value of most recently logged datapoint
    
#     def add_datapoint(self, time, data):
#         self.data[time] = data
#         self.current = time
#         values = []
#         for key in self.data.keys:
#             values.append(self.data[key])
#         self.line.set_data(self.data.keys, values)

graph_margin = 0.2

# data is a dictionary with values = data logged, keys = time logged
class GraphObject: # struct which keeps together objects needed for a graph
    def __init__(self, graph :tuple[Figure, FigureCanvas, plt.Axes], minn, maxn): # data = history?
        '''
        Initialization for GraphObject\n
        minn : minimum data value expected over graph lifetime\n
        maxn : maximum data value expected over graph lifetime
        '''
        self.figure = graph[0]
        self.canvas = graph[1]
        self.ax = graph[2]
        self.minn = minn # min data value expected
        self.maxn = maxn # max data value expected

        self.ax.legend()
        return


class DataObject:
    def __init__(self, name, rounding, units, parsing_fn, graph: GraphObject = None, line: plt.Line2D = None, label: QLabel = None):
        self.name = name
        self.rounding = rounding # number of dp to round to
        self.units = units
        self.parsing_fn = parsing_fn
        self.graph = graph
        self.line = line
        self.label = label
        self.data = {} # no data when initialized: of form time:value
        self.current = None # key of most recent data entry datapoint

        return 
    
    # modify ylim based on the datapoints in the graph
    # just don't call it for pH
    # this replaces Auto Y adjustment
    def adjust_ylim(self):
        values = self.data.values()
        if (values):
            maxn = max(values)
            minn = min(values)
            self.graph.ax.set_ylim(max(minn - (self.graph.maxn * graph_margin), self.graph.minn), min(maxn + (self.graph.maxn * graph_margin), self.graph.maxn))

    # Return a tuple with the time:value of the most current data point collected
    def get_current(self):
        val = round(self.data.get(self.current), self.rounding) if (self.current is not None) else None
        return self.current, val # returns the time, value of most recently logged datapoint
    
    # add a datapoint to self.data (history equivalent)
    def add_datapoint(self, time, data):
        self.data[time] = data
        self.current = time
        self.update_line_data()
        return
    
    def update_line_data(self):
        values = []
        for key in self.data.keys():
            values.append(self.data[key])
        self.line.set_data(list(self.data.keys()), values)
        return

    def parse_frame(self, current_time, data_line, parsed_dict=None):
        # calls the specific parsing_fn that belongs to this object
        # calls add_datapoint to add data
        if (parsed_dict is not None): # for can frames which contain multiple data values
            data = round(parsed_dict[self.name], self.rounding)
        else: # for can frames which hold only a single value
            raw_data = data_line.split(']')[-1].strip().split()
            data = self.parsing_fn(''.join(raw_data))

        self.add_datapoint(current_time, data)
        return

    # if there is a graph associated with this object and there are some data points outside of the graph window,
    # remove those points - make sure to log those points before calling update_data
    # so this function should be called by log_data
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

    
