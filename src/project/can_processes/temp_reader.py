import time
import paramiko
from project.data_object import *
from project.utility import *

def _send_status(pipe, connected, value):
    try:
        pipe.send((connected, value))
        return True
    except (BrokenPipeError, EOFError, OSError):
        return False

def temperature_reader(pipe):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname, username=username, password=password)
        while True:
            try:
                stdin, stdout, stderr = client.exec_command("cat /sys/class/thermal/thermal_zone0/temp")
                raw = stdout.read().decode().strip()
                if raw:
                    temp = float(raw) / 1000
                    if not _send_status(pipe, True, f"{temp:.1f}°C"):
                        break
                else:
                    if not _send_status(pipe, False, "ERROR"):
                        break
            except Exception:
                if not _send_status(pipe, False, "ERROR"):
                    break
            time.sleep(1)
    except Exception:
        while _send_status(pipe, False, "DISCONNECTED"):
            time.sleep(1)
    finally:
        try:
            pipe.close()
        except Exception:
            pass
        client.close()
