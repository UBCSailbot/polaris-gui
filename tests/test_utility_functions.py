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