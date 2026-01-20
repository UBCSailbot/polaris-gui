from PyQt5 import QtCore
from PyQt5.QtWidgets import QLabel
import pyqtgraph as pg
import config as cg

graph_margin = 0.2

def create_label(title, min_width=cg.value_label_min_width, max_height=cg.value_label_max_height):
    label = QLabel(title)
    label.setMinimumWidth(min_width)
    label.setMaximumHeight(max_height)
    label.setAlignment(QtCore.Qt.AlignLeft)
    label.setStyleSheet(cg.value_style)
    return label

def create_line(graph_obj, name, x_data, y_data, colour, line_width, line_dashed, symbol = None):  
    '''
    Creates and returns a pyqt5 line attached to the given graph
    '''
    try:
        pen = pg.mkPen(colour, width=line_width, style=QtCore.Qt.DashLine if line_dashed else None)

        new_line = graph_obj.graph.plot(
            x_data,
            y_data,
            name = name,
            pen=pen, 
            symbol = "o" if symbol else None
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
    # graph.setYRange(init_y_min, init_y_max)
    graph.addLegend()
    graph.showGrid(x=True, y=True)
    return graph

# data is a dictionary with values = data logged, keys = time logged
class GraphObject: # struct which keeps together objects needed for a graph
    def __init__(self, x_name, y_name, x_units, y_units, minn, maxn): # data = history?
        '''
        Initialization for GraphObject\n
        minn : minimum data value expected over graph lifetime\n
        maxn : maximum data value expected over graph lifetime
        '''
        self.x_name = x_name
        self.y_name = y_name
        self.x_units = x_units
        self.y_units = y_units
        self.minn = minn # min data value expected
        self.maxn = maxn # max data value expected
        self.initialized = False # indicates if graph widget was created or not
        self.visible = False
        return
    
    def initialize(self):
        self.graph = create_graph(f"{self.x_name} vs. {self.y_name}", f"{self.x_name} ({self.x_units})" if self.x_units else f"{self.x_name}", 
                                  f"{self.y_name} ({self.y_units})")
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
    def __init__(self, name, dp, units, parsing_fn, line_dashed = False, line_colour = None, graph: GraphObject = None):
        self.name = name
        self.dp = dp # number of dp to round to
        self.units = units if units else ""
        self.parsing_fn = parsing_fn
        self.line_dashed = line_dashed # boolean indicating whether line should be dashed or not
        self.line_colour = line_colour # if not graphed, doesn't need line colour
        self.graph_obj = graph # if not graphed, doesn't need a graph
        if (line_colour is None and graph is not None):
            raise ValueError("DataObject __init__: Given a graph, but not a line colour")
        self.data = {} # no data when initialized: of form time:value
        self.current = None # key of most recent data entry datapoint
        return 
    
    def initialize(self):
        if self.graph_obj:
            if not self.graph_obj.initialized: self.graph_obj.initialize()
            self.line = create_line(self.graph_obj, self.name, [], [], self.line_colour, cg.linewidth, self.line_dashed, symbol=False) if self.graph_obj else None # should automatically create line w/ empty data
        self.label = create_label(self.name + ": ---- ") # should automatically create label
        
    # Return a tuple with the time:value of the most current data point collected
    def get_current(self):
        val = round(self.data.get(self.current), self.dp) if (self.current is not None) else None
        return self.current, val # returns the time, value of most recently logged datapoint
    
    # add a datapoint to self.data
    def add_datapoint(self, x, y):
        self.data[x] = y
        self.current = x
        if (self.graph_obj.graph.isVisible()):
            self.update_line_data()
        return
    
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

    
