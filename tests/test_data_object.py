import pytest
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from tests.helpers import Outcome
import project.config as cg

from project.data_object import (
    create_label, create_line, create_graph, GraphObject, DataObject
)

@pytest.mark.parametrize(
        "arguments, expected_result",
        [
            ({"title":"Label A", "min_width": None, "max_height": None}, Outcome.SUCCESS),
            ({"title":"Label B", "min_width": 100, "max_height": 200}, Outcome.SUCCESS),
            ({"title":"", "min_width": None, "max_height": 400}, Outcome.SUCCESS),
            ({"title":"Broken Label", "min_width": None, "max_height": 0}, Outcome.VALUE_ERROR),
            ({"title":"Broken 2", "min_width": 0, "max_height": 300}, Outcome.VALUE_ERROR),
            ({"title":"Broken 3.455", "min_width": -30, "max_height": None}, Outcome.VALUE_ERROR),
        ],
)
def test_create_label(arguments, expected_result, qtbot):
    try:
        label = create_label(arguments["title"], arguments["min_width"], arguments["max_height"])
        qtbot.addWidget(label)

        assert label.text() == arguments["title"]
        assert label.minimumWidth() == arguments["min_width"] if arguments["min_width"] is not None else cg.value_label_min_width
        assert label.maximumHeight() == arguments["max_height"] if arguments["max_height"] is not None else cg.value_label_max_height
        assert label.alignment() == Qt.AlignLeft
        assert label.styleSheet() == cg.value_style
        
    except ValueError:
        assert expected_result == Outcome.VALUE_ERROR
        return
    except Exception:
        assert False

    assert expected_result == Outcome.SUCCESS

# TODO: test create_line, create_graph

# TODO: create more sample graph objects for testing
# TODO: test GraphObject class - test all functions

graph_object_params = [
    ({"x_name": "X data", "y_name": "Y data", "x_units": "sec", "y_units": None, "minn": 0, "maxn": 100, "dropdown_label": None}),
    ({"x_name": "bob", "y_name": "jim", "x_units": None, "y_units": "bacteria", "minn": 30, "maxn": 80, "dropdown_label": "special_label"}),
    ({"x_name": "test test", "y_name": "234093rew98", "x_units": "hours", "y_units": "mg/cm^3", "minn": -50, "maxn": -10, "dropdown_label": None}),
]

@pytest.fixture()
def init_obj(params, qtbot):
    obj = GraphObject(params["y_name"], params["x_name"], params["y_units"], params["x_units"], params["minn"], params["maxn"], params["dropdown_label"])
    obj.initialize()
    qtbot.addWidget(obj.graph) # add graph to visible application window
    return obj

@pytest.mark.parametrize("params", graph_object_params, scope="class")
class Test_GraphObject:

    def test_constructor(self, init_obj, params): 
        obj = init_obj

        assert obj.x_name == params["x_name"]
        assert obj.y_name == params["y_name"]
        assert obj.x_units == params["x_units"]
        assert obj.y_units == params["y_units"]
        assert obj.minn == params["minn"]
        assert obj.maxn == params["maxn"]
        assert obj.visible == False
        assert obj.initialized == True
        assert obj.graph.isVisible() == False
        if (params["dropdown_label"] is None):
            assert obj.dropdown_label == obj.y_name
        else:
            assert obj.dropdown_label == params["dropdown_label"]
        
        # TODO: add expected_outcome as a parameter to this test, and add bad parameters for creating graphobjects (eg. min > max)
        # assert expected_outcome == Outcome.SUCCESS

    # def test_update_xlim(self, init_obj, params):
    #     # TODO: finish implementation
    #     # NOTE: it would be nice to also take begin, end as parameters to the test
    #     pass

    def test_visibility(self, init_obj):
        # hide even after already hidden; make visible after already visible
        # also obviously change back and forth between states
        # hide/show multiple times - each time should be correct

        obj = init_obj

        # Setup check
        assert obj.graph.isVisible() == False 
        assert obj.isVisible() == False

        # hide when already hidden
        obj.hide()
        assert obj.isVisible() == False
        assert obj.graph.isVisible() == False 

        obj.show()
        assert obj.isVisible() == True
        assert obj.graph.isVisible() == True

        # show when already visible
        obj.show()
        assert obj.isVisible() == True
        assert obj.graph.isVisible() == True 

        obj.hide()
        obj.show()
        assert obj.isVisible() == True
        assert obj.graph.isVisible() == True
        

# TODO: add more testing parameters/tweaks to get boundary cases
# - add simple example parsing functions (lambda?)

data_object_params = [
    ({"name": "Object 1", "dp": 2, "units": "cm", "parsing_fn": None, "line_dashed": False, "line_colour": "r", "symbol_brush": None, "has_label": True, 
      "graph": None}),
    ({"name": "Object 2", "dp": 1, "units": None, "parsing_fn": None, "line_dashed": False, "line_colour": "g", "symbol_brush": 'x', "has_label": True, 
      "graph": GraphObject("Y data", "X data", None, "secs", 0, 100)}),
    ({"name": "Object 2", "dp": 1, "units": None, "parsing_fn": None, "line_dashed": True, "line_colour": "y", "symbol_brush": 'o', "has_label": False, 
      "graph": GraphObject("Y data", "X data", None, "secs", 0, 100)})
]

@pytest.fixture()
def init_data_object(params, qtbot):
    d_obj = DataObject(params["name"], params["dp"], params["units"], params["parsing_fn"], params["line_dashed"], params["line_colour"], params["symbol_brush"], params["has_label"], params["graph"])
    d_obj.initialize()
    if (d_obj.has_label):
        qtbot.addWidget(d_obj.label)
    if (d_obj.graph_obj is not None):
        qtbot.addWidget(d_obj.graph_obj.graph)
    return d_obj

@pytest.mark.parametrize("params", data_object_params, scope="class")
class Test_DataObject:
    def test_constructor(self, init_data_object, params):
        # TODO: complete implementation
        obj = init_data_object
        assert obj.name == params["name"]
        assert obj.dp == params["dp"]
        if params["units"]:
            assert obj.units == params["units"]
        else: assert obj.units == ""
        assert obj.parsing_fn == params["parsing_fn"]
        assert obj.line_dashed == params["line_dashed"]
        assert obj.line_colour == params["line_colour"]
        assert obj.graph_obj == params["graph"]
        assert not obj.data # dataset is empty
        assert obj.current == None
        assert obj.has_label == params["has_label"]
        assert obj.symbol_brush == params["symbol_brush"]
        if params["has_label"]:
            assert obj.label is not None
            assert obj.label.text() == params["name"] + ": ---- "
        else:
            assert obj.label is None
        
        if params["graph"] is not None:
            assert obj.line is not None
            # data, colour, dashed, symbol, name?
            assert not obj.line.xData and not obj.line.yData
            if params["symbol_brush"] is not None:
                symbol = obj.line.opts["symbol"]
                assert symbol == params["symbol_brush"]
                pen = obj.line.opts["pen"]
                # TODO: figure out how to check pen colour- right now, I think it's just comparing that they are two different objects
                # assert pen.color() == QColor(params["line_colour"])
                if params["line_dashed"]:
                    assert pen.style() == Qt.DashLine
                else: assert pen.style() == Qt.SolidLine

