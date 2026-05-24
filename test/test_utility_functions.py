import pytest
from re import escape
# from helpers import Outcome
from src.objects import *

@pytest.mark.parametrize(
    "decimal, num_bytes, expected_value, exception_type",
    [
        (0, 0, "", ValueError),
        (0, 1, "00", None),
        (0, 2, "0000", None),
        (0xa, 4, "0000000A", None),
        (0x12343abc, 3, "", ValueError),
        (0x12343abc, 4, "12343ABC", None),
        (0x123498a89b938, 7, "0123498A89B938", None)
    ]
)
def test_convert_to_hex(decimal, num_bytes, expected_value, exception_type):
    try:
        result = convert_to_hex(decimal, num_bytes)
        assert result == expected_value
        assert exception_type == None
    except ValueError:
        assert exception_type == ValueError
    except Exception:
        assert False

@pytest.mark.parametrize(
    "hex_str, expected_value, exception_type, exception_message", # NOTE: expected_value is not evaluated in the case of a thrown exception
    [
        ("", "", None, None),
        ("00", "00", None, None),
        ("0x1234", "", ValueError, "non-hexadecimal number found in fromhex() arg at position 1"), # No '0x' prefix accepted;
        ("123", "", ValueError, "ERROR - convert_to_little_endian received argument with odd number of characters"), # The hex string must contain an even number of digits
        ("001101f", "", ValueError, "ERROR - convert_to_little_endian received argument with odd number of characters"),
        ("1234", "3412", None, None),
        ("3427A09ECD", "cd9ea02734", None, None),
    ]
)
def test_convert_to_little_endian(hex_str, expected_value, exception_type, exception_message):
    if  exception_type == None:
        result = convert_to_little_endian(hex_str)
        assert result == expected_value
    elif exception_type == ValueError:
            with pytest.raises(ValueError, match=escape(exception_message)):
                 convert_to_little_endian(hex_str)
    else:
        assert False


@pytest.mark.parametrize(
    "raw_bytes, start, end, div, expected_value, exception_type",
    [
        (bytes.fromhex('48 65 6c'), 0, 3, 1, 7103816, None),
        (bytes.fromhex('48 65 6c'), 0, 3, 10, 710381.6, None),
        (bytes.fromhex('48 65 6c'), 2, 3, 7, 108 / 7, None),
        (bytes.fromhex('32 0f a0 00'), 0, 2, 2, 1945, None),
        (bytes.fromhex('32 0f a0 00'), 3, 2, 1, 1945, ValueError),
        (bytes.fromhex('32 0f a0 00'), 3, 3, 1, 1945, ValueError),
    ]
)
def test_val(raw_bytes, start, end, div, expected_value, exception_type) -> None: 
    if exception_type == None:
        result = val(raw_bytes, start, end, div)
        assert result == expected_value
    elif exception_type == ValueError:
        with pytest.raises(ValueError):
            val(raw_bytes, start, end, div)
    else:
        assert False
