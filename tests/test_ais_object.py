import pytest
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
from enum import Enum

from tests.helpers import Outcome, DataObject_Params
import project.config as cg

from project.data_object import AISObject # do I need to also import DataObject?


ais_object_params = [
    ({"name": "Object 1", "dp": 2, "units": "cm", "parsing_fn": None}) # TODO: finish adding parameters
]

@pytest.mark.parametrize("objects", ais_object_params)
class Test_AISObject:
    def test_constructor(self, object_params):
        # TODO: complete function
        pass