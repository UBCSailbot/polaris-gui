import pytest
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt

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
    ({"x_name": "X data", "y_name": "Y data", "x_units": "sec", "y_units": "cm", "minn": 0, "maxn": 100, "dropdown_label": None}, Outcome.SUCCESS),
    ({"x_name": "bob", "y_name": "jim", "x_units": "m", "y_units": "bacteria", "minn": 30, "maxn": 80, "dropdown_label": "special_label"}, Outcome.SUCCESS),
    ({"x_name": "test test", "y_name": "234093rew98", "x_units": "hours", "y_units": "mg/cm^3", "minn": -50, "maxn": -10, "dropdown_label": None}, Outcome.SUCCESS),
]

@pytest.fixture()
def init_obj(params, qtbot):
    obj = GraphObject(params["x_name"], params["y_name"], params["x_units"], params["y_units"], params["minn"], params["maxn"], params["dropdown_label"])
    obj.initialize()
    qtbot.addWidget(obj.graph) # add graph to visible application window
    return obj

@pytest.mark.parametrize("params, expected_outcome", graph_object_params, scope="class")
class Test_GraphObject:

    def test_constructor(self, init_obj, params, expected_outcome):
        # TODO: complete implementation - add asserts
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
            assert obj.dropdown_label == obj.x_name
        else:
            assert obj.dropdown_label == params["dropdown_label"]
        
        assert expected_outcome == Outcome.SUCCESS


data_object_params = [
    ({"name": "Object 1", "dp": 2, "units": "cm", "parsing_fn": None, "line_dashed": False, "line_colour": "r", "symbol_brush": None, "hasLabel": True, "graph": None})

]

class Test_DataObject:
    def test_constructor():
        # TODO: complete implementation
        pass