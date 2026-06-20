import pytest
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow
)

import project.config as cg
from project.data_object import (
    GraphObject, PIDObject, create_heading_arrow
)

# NOTE: I comment out the other data items in the dict, because they shouldn't be accessed by this function
parsed_dict_example =  {
    # 'gps_lat': 49.27251899999999, 
    # 'gps_lon': -123.198409, 
    'NS_offset': 35.26927799893974, # y.name
    'EW_offset': 6.60956064850514,  # x.name
    'desired_heading_arrow': None,  # desired_heading_arrow_name
    'actual_heading_arrow': 90.0,   # desired_heading_arrow_name
    # 'Speed_over_gnd_': 0.0
}

# ==== Setup =====
@pytest.fixture
def app(autouse=True, scope="module"):
    return QApplication(sys.argv)

@pytest.fixture
def window(autouse=True, scope="module"):
    return QMainWindow()

@pytest.fixture
def test_graph_obj(app): 
    return GraphObject("North/South Offset", "East/West Offset", "m", "m", -10000, 10000, "PLRS Path + Heading", interactable = True) # maxn, minn set pretty arbitrarily (+-10 km)
    # graph_obj.initialize()
    # return graph_obj

@pytest.fixture
def test_obj(test_graph_obj, autouse=True):
    pid_obj = PIDObject("PLRS_path", "EW_offset", "NS_offset", 6, "m", None, cg.plrs_path_data_timeout, symbol_brush = 'blue', has_label = False, graph = test_graph_obj)
    pid_obj.initialize()
    return pid_obj

@pytest.fixture
def exec(app, window, autouse=True, scope="module"):
    window.setCentralWidget(test_graph_obj.graph)
    app.exec()
    return

# ==== Main tests =====

def test_parse_frame_create_first_arrow(test_obj, current_time = 0, data_line = None, parsed_dict = parsed_dict_example):
    # Setup
    assert not test_obj.data # dictionary is empty

    # Testing
    test_obj.parse_frame(current_time, data_line, parsed_dict)

    # Check for success/failure
    # Check data
    assert len(test_obj.data) == 1
    assert test_obj.data[current_time]['NS_offset'] == round(35.26927799893974, test_obj.dp)
    assert test_obj.data[current_time]['EW_offset'] == round(6.60956064850514, test_obj.dp)
    assert test_obj.data[current_time][cg.desired_heading_arrow_name] is None
    assert test_obj.data[current_time][cg.actual_heading_arrow_name] is not None

    # # Check fixture refs
    # assert test_obj.lat_ref == round(49.27251899999999, test_obj.dp)
    # assert test_obj.lon_ref == round(-123.198409, test_obj.dp) 


def test_update_data_basic(test_obj):
    # Setup
    current_time = 0
    # put data in the object's dataset
    test_obj.parse_frame(current_time, data_line = None, parsed_dict = parsed_dict_example)

    # Test
    test_obj.remove_datapoint(current_time)

    # Check success/failure condition
    assert not test_obj.data


# NOTE: the below test could definitely test a lot more if I feel like adding that stuff
def test_arrow_constructor():
    arrow = create_heading_arrow(angle = 0, brush = 'blue')
    assert arrow.scene() is None


def test_graph_update(test_obj):
    # Setup
    current_time = 0
    test_obj.graph_obj.show() # set graph to be visible

    # Test
    # Add data and a heading_arrow object (for actual heading) to the graph
    test_obj.parse_frame(current_time, data_line = None, parsed_dict = parsed_dict_example)

    # Check graph
    arrow = test_obj.data[current_time][cg.actual_heading_arrow_name]
    assert arrow.scene() is not None
    assert arrow.isVisible()


def test_graph_delete(app, test_obj):
    # Setup
    current_time = 0
    test_obj.graph_obj.show() # set graph to be visible
    # Add data and a heading_arrow object (for actual heading) to the graph
    test_obj.parse_frame(current_time, data_line = None, parsed_dict = parsed_dict_example)
    arrow = test_obj.data[current_time][cg.actual_heading_arrow_name]

    # Test
    test_obj.remove_datapoint(current_time)

    # Check Success/Failure Condition
    assert arrow.scene() is None
    assert len(test_obj.graph_obj.graph.getPlotItem().dataItems) == 1

    # TODO: should the above assertions still be true if the graph is not visible? 
    # eg. not immediately updated

def test_graph_clear_basic(app, test_obj):
    # Setup
    current_time = 0
    test_obj.graph_obj.show() # set graph to be visible
    # Add data and a heading_arrow object (for actual heading) to the graph
    test_obj.parse_frame(current_time, data_line = None, parsed_dict = parsed_dict_example)

    # Test
    test_obj.clear()

    # Check data
    assert not test_obj.data
    assert test_obj.last_arrow_time is None
    assert test_obj.lat_ref is None
    assert test_obj.lon_ref is None

    # Check graph
    # assert len(test_obj.graph_obj.graph.getPlotItem().dataItems) == 1
    # Returns all QGraphicsItem objects rendered within the plot viewport
    # assert len([item for item in test_obj.graph_obj.graph.items()])

    # TODO: update this test to be more meaningful; the one data item should be a plotDataItem with no data points, and the graph should have no arrows
    # TODO: add check to ensure that no arrowItem is on the graph
    