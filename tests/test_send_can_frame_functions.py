import pytest
import sys
from PyQt5.QtWidgets import (
    QApplication # , QMainWindow
)

# from project.remote_debugger import CANWindow
from src.main import CANWindow

pytestmark = pytest.mark.skip(reason="These tests do not work yet")

# ==== Setup =====
@pytest.fixture
def app(autouse=True, scope="module"):
    return QApplication(sys.argv)

# @pytest.fixture
# def window(autouse=True, scope="module"):
#     return QMainWindow()

# @pytest.fixture
# def test_obj_null_args(app):
#     return CANWindow(None, None, None, None, None, None)

# @pytest.mark.skip
# def test_send_pid_param(test_obj_null_args):
#     assert False

# NOTE: Right now these tests don't work; hoping to extract CAN send functions into their own testable class later