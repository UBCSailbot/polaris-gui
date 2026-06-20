import pytest

import project.config as cg
from project.data_object import (
    GraphObject, IMUHeadingObject
)

@pytest.fixture()
def test_graph_obj():
    return GraphObject("Test Graph Object", cg.graph_y, "°", cg.graph_y_units, 0, 360)

@pytest.fixture()
def test_obj(test_graph_obj):
    return IMUHeadingObject("Test IMU Heading Obj", 3, "°", None, line_colour="r", graph=test_graph_obj)

@pytest.mark.parametrize(
    "old_angle, new_angle, expected",
    [
        (0, 1, 0),
        (0, 10, 0),
        (0.123, 179.32, 0),
        (0, 179.5, 0),
        (0, 180, -1),
        (180, 0, 1),
        (0, 359.34, -1),
        (0, 350, -1),
        (350, 1, 1),
        (359, 0, 1),
        (352.1, 3, 1),
        (238, 289, 0),
        (129, 98.987, 0)
    ]
)
def test_update_current_rotations(old_angle, new_angle, expected, test_obj):
    # setup 
    assert test_obj.current_rotations == 0

    # test
    test_obj.update_current_rotations(old_angle, new_angle)

    # check
    assert test_obj.current_rotations == expected
    
    return