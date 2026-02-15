import pytest
from enum import Enum
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt

import project.config as cg

from project.data_object import (
    create_label, create_line, create_graph, DataObject, AISObject
)

class Outcome(Enum):
    SUCCESS = 0,
    VALUE_EXCEPTION = 1

@pytest.mark.parametrize(
        "arguments, expected_result",
        [
            ({"title":"Label A", "min_width": None, "max_height": None}, Outcome.SUCCESS),
            ({"title":"Label B", "min_width": 100, "max_height": 200}, Outcome.SUCCESS),
            ({"title":"", "min_width": None, "max_height": 400}, Outcome.SUCCESS),
            ({"title":"Broken Label", "min_width": None, "max_height": 0}, Outcome.VALUE_EXCEPTION),
            ({"title":"Broken 2", "min_width": 0, "max_height": 300}, Outcome.VALUE_EXCEPTION),
            ({"title":"Broken 3.455", "min_width": -30, "max_height": None}, Outcome.VALUE_EXCEPTION),
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
        assert expected_result == Outcome.VALUE_EXCEPTION
        return
    except Exception:
        assert False

    assert expected_result == Outcome.SUCCESS
