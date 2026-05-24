import pytest
import random
from src.objects import *

volt_delta = 0.0001
temp_delta = 0.01
cur_delta = 0.001

@pytest.mark.parametrize(
    "volt2, temp1, volt3, temp2, temp3, volt4, volt1, hp_cur, hs_cur, sp_cur, ss_cur",
    [
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (6.5535, 234, 1.543504, 0.01, 21.43, 0.0001, 5.234012, 38, 1.012, 8.001, 1.1), 
        (3.92, 125.231, 0.0128, 655.35, 9.89, 2.3989, 1.4009, 65.143, 0.01111, 43.1291, 1.10)
    ]
)
def test_parse_0x206_frame(volt2, temp1, volt3, temp2, temp3, volt4, volt1, hp_cur, hs_cur, sp_cur, ss_cur):

    # Setup
    volt2_data = int(volt2 * 10000).to_bytes(2, byteorder='little').hex()
    temp1_data = int(temp1 * 100).to_bytes(2, byteorder='little').hex()
    volt3_data = int(volt3 * 10000).to_bytes(2, byteorder='little').hex()
    temp2_data = int(temp2 * 100).to_bytes(2, byteorder='little').hex()
    temp3_data = int(temp3 * 100).to_bytes(2, byteorder='little').hex()
    volt4_data = int(volt4 * 10000).to_bytes(2, byteorder='little').hex()
    volt1_data = int(volt1 * 10000).to_bytes(2, byteorder='little').hex()
    hp_cur_data = int(hp_cur * 1000).to_bytes(2, byteorder='little').hex()
    hs_cur_data = int(hs_cur * 1000).to_bytes(2, byteorder='little').hex()
    sp_cur_data = int(sp_cur * 1000).to_bytes(2, byteorder='little').hex()
    ss_cur_data = int(ss_cur * 1000).to_bytes(2, byteorder='little').hex()
    
    data_hex = volt2_data + temp1_data + volt3_data + temp2_data + temp3_data + volt4_data + volt1_data + hp_cur_data + hs_cur_data + sp_cur_data + ss_cur_data + random.randbytes(2).hex()
    # Test - there should be no exception thrown
    try: 
        result = parse_0x206_frame(data_hex)
        assert result[volt1_obj.name] == pytest.approx(volt1, abs=volt_delta)
        assert result[volt2_obj.name] == pytest.approx(volt2, abs=volt_delta)
        assert result[volt3_obj.name] == pytest.approx(volt3, abs=volt_delta)
        assert result[volt4_obj.name] == pytest.approx(volt4, abs=volt_delta)
        assert result[temp1_obj.name] == pytest.approx(temp1, abs=temp_delta)
        assert result[temp2_obj.name] == pytest.approx(temp2, abs=temp_delta)
        assert result[temp3_obj.name] == pytest.approx(temp3, abs=temp_delta)
        assert result[mppt_hp_obj.name] == pytest.approx(hp_cur, abs=cur_delta)
        assert result[mppt_hs_obj.name] == pytest.approx(hs_cur, abs=cur_delta)
        assert result[mppt_sp_obj.name] == pytest.approx(sp_cur, abs=cur_delta)
        assert result[mppt_ss_obj.name] == pytest.approx(ss_cur, abs=cur_delta)

    except Exception as e:
        print(f"TEST ERROR - Exception thrown: {e}")
        assert False


def test_parse_0x206_frame_length_check(data_hex):
    # test for exception (when length is wrong)
    # TODO
    pass