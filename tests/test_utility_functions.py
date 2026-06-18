import pytest
from project.utility import *
from tests.helpers import Outcome

@pytest.mark.parametrize(
    "decimal, num_bytes, expected_value, expected_outcome",
    [
        (0, 0, "", Outcome.VALUE_ERROR),
        (0, 1, "00", Outcome.SUCCESS),
        (0, 2, "0000", Outcome.SUCCESS),
        (0xa, 4, "0000000A", Outcome.SUCCESS),
        (0x12343abc, 3, "", Outcome.VALUE_ERROR),
        (0x12343abc, 4, "12343ABC", Outcome.SUCCESS),
        (0x123498a89b938, 7, "0123498A89B938", Outcome.SUCCESS)
    ]
)
def test_convert_to_hex(decimal, num_bytes, expected_value, expected_outcome):
    try:
        result = convert_to_hex(decimal, num_bytes)
        assert result == expected_value
        assert expected_outcome == Outcome.SUCCESS
    except ValueError:
        assert expected_outcome == Outcome.VALUE_ERROR
    except Exception:
        assert False

@pytest.mark.parametrize(
    "hex_str, expected_value, expected_outcome",
    [
        ("", "", Outcome.SUCCESS),
        ("00", "00", Outcome.SUCCESS),
        ("0x123", "", Outcome.VALUE_ERROR),
        ("123", "", Outcome.VALUE_ERROR),
        ("1234", "3412", Outcome.SUCCESS),
        ("3427A09ECD", "cd9ea02734", Outcome.SUCCESS),
        ("0001101f", "1f100100", Outcome.SUCCESS),
    ]
)
def test_convert_to_little_endian(hex_str, expected_value, expected_outcome):
    try:
        result = convert_to_little_endian(hex_str)
        assert result == expected_value
        assert expected_outcome == Outcome.SUCCESS
    except ValueError:
        assert expected_outcome == Outcome.VALUE_ERROR
    except Exception:
        assert False


@pytest.mark.parametrize(
    "input, expected_output",
    [
        (0, "00000000"),
        (123.45, "42f6e666"),
        # (123.45, "66e6f642"),
        (34.2356, "4208f141"), 
        # (34.2356, "41f10842"), 
        (0.123456789, "3dfcd6ea"),
        # (0.123456789, "ead6fc3d"),
        (-911.2819, "c463d20b")
        # (-911.2819, "0bd263c4")
    ]
)
def test_convert_float_to_binary32hex(input, expected_output):
    try:
        actual_output = convert_float_to_binary32hex(input)
        assert actual_output == expected_output
    except Exception as e:
        assert False

class TestParsingFunctions:

    def test_parse_0x001_frame_basic(self):
        # Setup
        expected_output = {"steering_selection_bit": False, "steering_enable_bit": True, desired_heading_obj.name: 100.19, set_rudder_obj.name: 10.19}
        data = "5e87010040"

        # Test
        actual_output = parse_0x001_frame(data)

        # Check
        # assert actual_output == expected_output
        assert len(actual_output) == len(expected_output)
        assert actual_output['steering_selection_bit'] == expected_output['steering_selection_bit'] 
        assert actual_output['steering_enable_bit'] == expected_output['steering_enable_bit'] 
        assert actual_output[desired_heading_obj.name] == expected_output[desired_heading_obj.name] 
        assert actual_output[set_rudder_obj.name] == pytest.approx(expected_output[set_rudder_obj.name])

    def test_parse_0x001_frame_wrong_data_length(self):
        with pytest.raises(ValueError):
            parse_0x001_frame("001122334")
        with pytest.raises(ValueError):
            parse_0x001_frame("00112233445")


# TODO: first test a function to convert data to hex
# TODO: test the parse_0x204 frame issue