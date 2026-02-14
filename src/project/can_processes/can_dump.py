import multiprocessing
import time
import paramiko
from data_object import *
from utility import *

### ----------  Background CAN Dump Process ---------- ###
def candump_process(queue: multiprocessing.Queue, testing):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if (testing):
        # TODO
        print("TESTING MODE ON")
    else:
        try:
            client.connect(hostname, username=username, password=password)
            transport = client.get_transport()
            # session = transport.open_session()
            # session.exec_command("bash sailbot_workspace/scripts/canup.sh -l")
            session = transport.open_session()
            session.exec_command(f"candump {can_line}")
            while True:
                if session.recv_ready():
                    line = session.recv(1024).decode()
                    lines = line.split("\n")
                    for l in lines:
                        if (l != ""): queue.put(l.strip())
                time.sleep(0.1)
        except Exception as e:
            queue.put(f"[ERROR] {str(e)}")
        finally:
            client.close()