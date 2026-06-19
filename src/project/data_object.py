from PyQt5 import QtCore
from PyQt5.QtWidgets import QLabel
from enum import Enum
import pyqtgraph as pg
import os
import csv
import project.config as cg
import math

graph_margin = 0.2
MAX_ANGLE_JUMP = 180

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

def generic_create_line(graph_obj, name, x_data, y_data, colour, line_width, line_dashed, symbol_brush = None, symbol = None) -> pg.PlotDataItem:  
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
    
def create_graph(title, x_label, y_label, interactable: bool, title_style = cg.graph_title_style, label_style = cg.graph_label_style, y_AxisItem: pg.AxisItem = None):
    graph = pg.PlotWidget(axisItems={'left': y_AxisItem}) if y_AxisItem is not None else pg.PlotWidget()
    graph.setBackground(cg.graph_bg)
    graph.setMinimumSize(cg.graph_min_width, cg.graph_min_height)
    graph.getPlotItem().getViewBox().setMouseEnabled(interactable, interactable)
    graph.setTitle(title, color=title_style[0], size=title_style[1])
    graph.setLabel("left", y_label, **label_style)
    graph.setLabel("bottom", x_label, **label_style)
    graph.addLegend()
    graph.showGrid(x=True, y=True)
    return graph

# A custom arrow based on the pyqtgraph ArrowItem class, used for visualising boat heading
class HeadingArrow(pg.ArrowItem):
    def paint(self, p, *args):
        p.translate(-2 * self.boundingRect().center())
        pg.ArrowItem.paint(self, p, *args)

def create_heading_arrow(angle, brush) -> HeadingArrow:
    # NOTE: Degrees for heading values in the 0x204 rudder debug CAN frame are defined as 0° for North and increasing clockwise
    # so conversion is necessary (standard function interprets angle # as 0 from W increasing clockwise)
    return HeadingArrow(angle=(angle + 90) % 360, headLen=cg.h_arrow_headLen, tailLen=cg.h_arrow_tailLen, headWidth=cg.h_arrow_headWidth, tailWidth=cg.h_arrow_tailWidth, pen=cg.h_arrow_pen, brush=brush)

# A custom class which is used for modifying axis labels on the IMU Headings graph
# such that it appears like 0 -> 359 -> 0 -> 359 -> ...
# NOTE: This class only overrides the AxisItem.tickStrings() method
class IMUHeadingAxisItem(pg.AxisItem):
    def tickStrings(self, values: list[float], scale: float, spacing: float) -> list[str]:
        return [str(round(val % 360, 5)) for val in values] # NOTE: the number of dp to round to is fairly arbitrary; it's just there to prevent small floating point errors from becoming visible in the GUI

# data is a dictionary with values = data logged, keys = time logged
class GraphObject: # struct which keeps together objects needed for a graph
    def __init__(self, y_name, x_name, y_units, x_units, minn, maxn, dropdown_label = None, interactable: bool = False): # data = history?
        '''
        Initialization for GraphObject\n
        minn : minimum data value expected over graph lifetime\n
        maxn : maximum data value expected over graph lifetime
        dropdown_label: alternate (shorter) name for the dropdown list (NOTE: this att must be unique across all GraphObjects)
        '''
        self.x_name = x_name
        self.y_name = y_name
        self.x_units = x_units
        self.y_units = y_units
        self.interactable = interactable

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
    
    def initialize(self, custom_y_AxisItem = None):
        self.graph = create_graph(self.dropdown_label if self.dropdown_label != self.x_name else f"{self.x_name} vs. {self.y_name}", f"{self.x_name} ({self.x_units})" if self.x_units else f"{self.x_name}", 
                                  f"{self.y_name} ({self.y_units})" if self.y_units else f"{self.y_name}", self.interactable, y_AxisItem = custom_y_AxisItem)
        self.graph.hide()
        self.initialized = True 

    def update_xlim(self, begin, end):
        self.graph.setXRange(begin, end)

    def update_ylim(self, begin, end):
        self.graph.setYRange(begin, end)

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
            self.init_empty_line()
        if self.has_label:
            self.label = create_label(self.name + ": ---- ") # should automatically create label
        else: self.label = None

    def init_empty_line(self) -> None:
        self.line = generic_create_line(self.graph_obj, self.name, [], [], self.line_colour, cg.linewidth, self.line_dashed, self.symbol_brush, symbol = 'o' if self.symbol_brush else None) # should automatically create line w/ empty data
        
    def get_current(self):
        '''
        Return a tuple with the time:value of the most current data point collected
        '''
        val = None
        if self.current and self.data.get(self.current) is not None:
            val = round(self.data.get(self.current), self.dp)
        return self.current, val # returns the time, value of most recently logged datapoint
    
    def add_datapoint(self, x, y):
        '''
        add a datapoint to self.data
        '''
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
        '''NOTE: current_time becomes the key of the data dict (and x_data on the graph)'''
        # calls the specific parsing_fn that belongs to this object
        # calls add_datapoint to add data
        if (parsed_dict is not None): # for can frames which contain multiple data values
            data = round(parsed_dict[self.name], self.dp)
        else: # for can frames which hold only a single value
            raw_data = data_line.split(']')[-1].strip().split()
            data = self.parsing_fn(''.join(raw_data))
            if self.dp is not None: # for values which do not have variable dp (ie. not salinity)
                data = round(data, self.dp)
        # print("current_time = ", current_time, "  | data = ", data)
        self.add_datapoint(current_time, data)
        return

    # if there is a graph associated with this object and there are some data points outside of the graph window,
    # remove those points 
    def update_data(self, current_time, scroll_window):
        '''
        if there is a graph associated with this object and there are some data points outside of the graph window,
        remove those points 
        '''
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

# A class for DataObjects which take manual input from the GUI and hold their value after a period of time
# So these should be graphed regularly over time after taking manual input, holding their value until changed - not once and stop
class InputDataObject(DataObject):
    # TODO: implementation
    pass

# A custom DataObject class for creating a graph object with a custom AxisItem (for y-axis)
# and calculating wrapping for IMU for smoother graph experiences
class IMUHeadingObject(DataObject):

    def __init__(self, name, dp, units, parsing_fn, line_dashed = False, line_colour = None, symbol_brush = None, has_label = True, graph: GraphObject = None):
        super().__init__(name, dp, units, None, line_colour = line_colour, symbol_brush = symbol_brush, graph = graph)
        # Tracks how many full rotations the boat has made since initialization for smooth graph readings
        # positive numbers are positive rotations (358->359->0->1), negative is the other way (1->0->359->358)
        self.current_rotations = 0 
        self.graph_data = {} # Data used for graphing only (not logging), contains data in self.data plus offset based on the number of rotations at the time

        return 
        
    def initialize(self, timestamp = None):
        if self.graph_obj:
            if not self.graph_obj.initialized: self.graph_obj.initialize(custom_y_AxisItem = IMUHeadingAxisItem("left"))
            # if not self.graph_obj.initialized: self.graph_obj.initialize()
            self.init_empty_line()
        if self.has_label:
            self.label = create_label(self.name + ": ---- ") # should automatically create label
        else: self.label = None

    def update_current_rotations(self, old_angle: float, new_angle: float) -> None:
        '''
        Compares the new angle to the last recorded angle (using get_current()) and decides 
        if a full rotation CW or CCW has occurred, updating self.current_rotations accordingly
        '''
        if old_angle is None or new_angle is None: return

        if (old_angle - new_angle) >= MAX_ANGLE_JUMP: self.current_rotations += 1
        elif (old_angle - new_angle) <= -(MAX_ANGLE_JUMP): self.current_rotations -= 1

        return

    def add_datapoint(self, x, y):
        '''
        Updates self.data and self.graph_data
        '''
        self.update_current_rotations(self.get_current()[1], y)
        # print("current_rotations = ", self.current_rotations)
        self.graph_data[x] = y + (self.current_rotations * 360)
        super().add_datapoint(x, y)
        # print("graph_data = ", self.graph_data)
        # print("self.line data = ", self.line.getData())

    def update_line_data(self) -> None:
        if (self.line is not None):
            # if graph_data is None: graph_data = self.data
            values = []
            for key in self.graph_data.keys():
                values.append(self.graph_data[key])
            self.line.setData(list(self.graph_data.keys()), values)
        return


class DesiredHeadingObject(IMUHeadingObject):
    def __init__(self, name, dp, units, parsing_fn, line_dashed = False, line_colour = None, symbol_brush = None, has_label = True, graph: GraphObject = None, imu_heading_ref_obj: IMUHeadingObject = None):
        super().__init__(name, dp, units, None, line_colour = line_colour, symbol_brush = symbol_brush, graph = graph)

        if imu_heading_ref_obj is None: raise ValueError("A DesiredHeadingObject requires a reference to a imu_heading_ref_obj")
        self.imu_heading_ref_obj = imu_heading_ref_obj # Uses .current_rotations from this obj as a reference to correctly graph data

        return

    def add_datapoint(self, x, y):
        '''
        Updates self.data and self.graph_data
        '''
        # self.update_current_rotations(self.get_current()[1], y)
        # print("current_rotations = ", self.current_rotations)
        self.graph_data[x] = y + (self.imu_heading_ref_obj.current_rotations * 360)
        super().add_datapoint(x, y)
        # print("graph_data = ", self.graph_data)
        # print("self.line data = ", self.line.getData()) 


class PIDObject(DataObject):
    def __init__(self, name, x_name, y_name, dp, units, parsing_fn, timeout_duration: int, line_dashed = False, line_colour = None, symbol_brush = None, has_label = True, graph: GraphObject = None) -> None:
        '''
        Args: timeout_duration: amount of time (secs) until new datapoint is deleted'''

        super().__init__(name, dp, units, None, has_label = False, line_colour = None, symbol_brush = symbol_brush, graph = graph)

        # Name for x data and y_data (for getting it out of the dict)
        self.x_name = x_name
        self.y_name = y_name
        
        # First GPS reading; becomes the (0, 0) reference point for the graph
        # Kept as unrounded values for more accurate calculations; 
        # Create get() function which rounds these values if users want to see them
        self.lat_ref = None
        self.lon_ref = None

        # Time of last placed datapoint with heading arrows
        self.last_arrow_time = None

        # Amount of time before datapoints are removed from memory
        self.timeout_duration = timeout_duration 

        return
    
    def set_refs(self, lat, lon):
        self.lat_ref = lat
        self.lon_ref = lon

    
    def parse_frame(self, current_time, data_line, parsed_dict=None):
        # NOTE: There definitely should be a parsed_dict when this function is called, error otherwise
        if (parsed_dict is None): raise ValueError("ERROR: No parsed_dict passed to PIDObject.parse_frame()")
        else:
            # print("parsed_dict = ", parsed_dict)
            x = round(parsed_dict[self.x_name], self.dp)
            y = round(parsed_dict[self.y_name], self.dp)
            # self.add_datapoint(current_time, (x, y)) # key is current time, value is a tuple with x, y values
            # NOTE: this replaces the above line to add reference to heading arrows
            # TODO: update with actual heading arrows, change update_line_data to also add the arrowItems, change update_data to also remove the arrowItems
            desired_arrow = None
            actual_arrow = None
            should_create_arrow = self.should_create_arrow(current_time, parsed_dict[self.x_name], parsed_dict[self.y_name])
            # print("after should_create_arrow()")
            if parsed_dict[cg.desired_heading_arrow_name] is not None and should_create_arrow:
                desired_arrow = create_heading_arrow(parsed_dict[cg.desired_heading_arrow_name], cg.h_arrow_desired_brush)
            if parsed_dict[cg.actual_heading_arrow_name] is not None and should_create_arrow:
                print("actual_heading_arrow being created!")
                actual_arrow = create_heading_arrow(parsed_dict[cg.actual_heading_arrow_name], cg.h_arrow_actual_brush)

            self.add_datapoint(current_time, 
                {self.x_name: x, self.y_name: y, 
                cg.desired_heading_arrow_name: desired_arrow,
                cg.actual_heading_arrow_name: actual_arrow})

        return

    def should_create_arrow(self, current_time: int, x: float, y: float) -> bool:
        '''Calculates the distance between this point and the last recorded point in metres; 
        returns true if distance is greater than or equal to config.dist_between_arrows'''
        if (self.last_arrow_time is None):
            self.last_arrow_time = current_time
            return True # NOTE: assuming that if [0] is not None, [1] will also not be None
        if cg.ARROW_TIME_SCALING_ENABLED:
            if (current_time - cg.min_time_between_arrows) >= self.last_arrow_time:
                self.last_arrow_time = current_time
                return True 
            else: return False
        else: # Distance-based scaling
            last_x = self.data[self.last_arrow_time][self.x_name]
            last_y = self.data[self.last_arrow_time][self.y_name]
            dist_between_pts = math.sqrt(((x - last_x) ** 2) + ((y - last_y) ** 2))
            # print("self.last_arrow_time = ", self.last_arrow_time)
            # print("last_x = ", last_x, "; last_y = ", last_y)
            # print("     x = ", x, "     y = ", y)
            # print("dist = ", dist_between_pts)

            if dist_between_pts >= cg.min_dist_between_arrows:
                self.last_arrow_time = current_time
                return True 
            else:
                return False


    def add_datapoint(self, x, y):
        # TODO: ArrowItems should be added to the graph only if the graph is visible - do this in update_line_data?
            # Actually, I don't think I want to keep updating; I'll set once here
        # y = {self.x_name: x_coord, self.y_name: y_coord, cg.desired...: desiredHeadingArrow, cg.actual...: actualHeadingArrow}

        # print("add_datapoint called")
        # print(y)

        desiredHeadingArrow = y[cg.desired_heading_arrow_name]
        actualHeadingArrow = y[cg.actual_heading_arrow_name]

        if desiredHeadingArrow is not None:
            desiredHeadingArrow.setPos(y[self.x_name], y[self.y_name])
            self.graph_obj.graph.addItem(desiredHeadingArrow)

        # NOTE: so far actualHeading cannot be None, but this may change in the future
        if actualHeadingArrow is not None:
            actualHeadingArrow.setPos(y[self.x_name], y[self.y_name])
            self.graph_obj.graph.addItem(actualHeadingArrow)
            # print("actualHeadingArrow added to graph")

        super().add_datapoint(x, y)
        # NOTE: below is stuff done in super().add_datapoint(x, y)
        # self.data[x] = y
        # self.current = x
        # if (self.graph_obj and self.graph_obj.graph.isVisible()):
        #     self.update_line_data()
        return
   
    def get_current(self):
        '''
        Return a tuple with the time:value of the most current data point collected
        '''
        val = None
        if self.current and self.data.get(self.current) is not None:
            val = self.data.get(self.current)
        return self.current, val # returns the time, value (full dict) of most recently logged datapoint
 
    def update_data(self, current_time, scroll_window):
        '''Update stored data points: remove any received before data_timeout'''
        # TODO: complete function; data_timeout should be set in config, and should be a parameter of PIDObject
        # TODO: I wonder if there's a faster way of doing this? Ordered list?
        points_to_delete = []
        for time_logged in self.data.keys():
            if ((current_time - time_logged) > self.timeout_duration): # if data has not been updated for long enough: remove dp
                points_to_delete.append(time_logged)
        for key in points_to_delete:
            self.remove_datapoint(key)
        if (self.graph_obj and self.graph_obj.graph.isVisible()):
            self.update_line_data()
        return
 
    def update_line_data(self):
        '''NOTE: This function operates on the assumption that self.dict is of the format current_time: (x, y)'''
        if (self.line is None): raise Exception("ERROR - PIDObject has no line")
        else:
            x = [value[self.x_name] for value in self.data.values()]
            y = [value[self.y_name]  for value in self.data.values()]
            # print("x = ", x)
            # print("y == ", y)
            self.line.setData(x, y)
        return


    def remove_datapoint(self, x):
        try:
            if self.data[x][cg.desired_heading_arrow_name] is not None:
                self.graph_obj.graph.removeItem(self.data[x][cg.desired_heading_arrow_name])
            if self.data[x][cg.actual_heading_arrow_name] is not None:
                self.graph_obj.graph.removeItem(self.data[x][cg.actual_heading_arrow_name])

            del self.data[x]
        except KeyError:
            print(f"ERR - trying to apply remove_datapoint() on a point which does not exist")

    def clear(self):
        '''
        Removes all datapoints from memory, clears initial gps "fix", clears the graph
        '''
        # Removes all datapoints from self.data, sets all initial "fixes" back to None (gps_fix, self.last_time, self.lat/lon_ref), clears the graph
        self.graph_obj.graph.clear()
        self.data = {} # clear all datapoints from memory
        self.last_arrow_time = None # Last arrow placed is gone, so set this to none
        self.lat_ref = None # reset first gps fix
        self.lon_ref = None 
        self.init_empty_line() # re-create line with no data


    
class AISObject(DataObject): 
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
        self.polaris_line = generic_create_line(self.graph_obj, "POLARIS", [], [], None, None, False, self.polaris_brush, 'x')

    def add_frame(self, x, y, key, data, x_key):
        '''x_key is the key for the value containing the x_value'''
        if x is None or y is None:
            print("ERR - add_frame() received None for lat or lon from AIS frame")
        if (key in self.dataset): # if ship already exists in dataset
            self.remove_datapoint(self.dataset[key][x_key]) # remove old lon/lat value from graph
        
        self.dataset[key] = data # NOTE: instead of appending, replace on ship SID - should self.dataset be a dict instead? Check that everything works like this
        # TODO: note that self.data is a dict with x: y - to replace pts, remove old pt using key(old longitude), then update longitude and put new point using new longitude
        self.add_datapoint(x, y) # add new (lon, lat) of ship to list of datapoints to graph 

    # NOTE: commented out as it is not being used currently
    # def add_line(self, name, x_data, y_data, colour, line_width, line_dashed, symbol_brush = None, symbol = None):
    #     return create_line(self.graph_obj, name, x_data, y_data, colour, line_width, line_dashed, symbol_brush, symbol)

    def clear_data(self):
        self.data.clear()

    def update_range(self, x_min = None, x_max = None, y_min = None, y_max = None):
        '''
        Modify the range of the x and y axes of the graph object belonging to this object.
        \nNote that manually setting the range at any point turns off auto-range.
        '''
        if self.graph_obj is None:
            print("ERROR - This object has no graph object")
        if (x_min is not None and x_max is not None):
            self.graph_obj.update_xlim(x_min, x_max)
        if (y_min is not None and y_max is not None):
            self.graph_obj.update_ylim(y_min, y_max)
        

    def update_data(self, current_time, scroll_window):
        '''Remove datapoints which have not been updated for a while (cg.data_timeout secs)'''
        points_to_delete = []
        for key, frame in self.dataset.items():
            if (current_time - frame[cg.LAST_UPDATED] > cg.data_timeout): # if data has not been updated for long enough: remove dp
                points_to_delete.append(key)
        for key in points_to_delete:
            self.remove_datapoint(self.dataset[key][AIS_Attributes.LONGITUDE])
            del self.dataset[key]
        if (self.graph_obj and self.graph_obj.graph.isVisible()):
            self.update_line_data()


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
                    for key in ais_attributes: # get the keys in data
                        if frame[key] is None:
                            values.append("None")
                        else: values.append(frame[key])
                    writer.writerow(values)
                csv_file.flush()  # Flush immediately to prevent data loss
        except Exception as e:
            print(f"Error logging AIS values: {e}")

        return
    
    def update_polaris_pos(self, lon, lat):
        if lon is None or lat is None: 
            print("ERR - update_polaris_pos(): POLARIS lon or lat is None, its position cannot be graphed")
            return # if either is None, can't graph position - just return
        if self.graph_obj.isVisible():
            self.polaris_line.setData([lon], [lat])
        # print("polaris_pos updated!")
        # print("self.polaris_line = (", self.polaris_line.xData, ", ", self.polaris_line.yData, ")")
        

    
### ----------  Structs/Enums ---------- ###
class AIS_Attributes(Enum):
    SID = "ship_id"
    LONGITUDE = "longitude"
    LATITUDE = "latitude"
    SOG = "speed_over_gnd"
    SOG_NA = 1023
    COG = "course_over_gnd"
    COG_NA = 3600
    HEADING = "true_heading"
    HEADING_NA = 511
    ROT = "rate_of_turn"
    ROT_NA = -128
    LENGTH = "ship_length"
    LENGTH_NA = 0
    WIDTH = "ship_width"
    WIDTH_NA = 0
    IDX = "index"
    TOTAL = "total_ships"

# This list is ordered according to 0x060 frame conventions as specified on confluence (don't reorder or else heading order will be incorrect)
ais_attributes = [
    AIS_Attributes.SID, 
    AIS_Attributes.LATITUDE,
    AIS_Attributes.LONGITUDE, 
    AIS_Attributes.SOG,
    AIS_Attributes.COG,
    AIS_Attributes.HEADING,
    AIS_Attributes.ROT,
    AIS_Attributes.LENGTH,
    AIS_Attributes.WIDTH,
    AIS_Attributes.IDX,
    AIS_Attributes.TOTAL
]