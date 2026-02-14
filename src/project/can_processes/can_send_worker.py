import multiprocessing
import paramiko
from data_object import *
from utility import *

def cansend_worker(cmd_queue: multiprocessing.Queue, response_queue: multiprocessing.Queue, can_log_queue: multiprocessing.Queue):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname, username=username, password=password)
        while True:
            cmd = cmd_queue.get()
            if cmd == "__EXIT__":
                break
            try:
                out = ""
                err = ""
                if (cmd[0:4] == "sudo"):
                    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
                    buf = ""
                    while (not buf.endswith("[sudo] password for sailbot: ")):
                        buf += stdout.channel.recv(1024).decode()
                    stdin.write(f"{password}\n")
                    stdin.flush()
                    out = stdout.read().decode()
                    err = stderr.read().decode()
                else:
                    stdin, stdout, stderr = client.exec_command(cmd)
                    out = stdout.read().decode()
                    err = stderr.read().decode()

                response_queue.put((cmd, out, err))
                if (not err):
                    can_log_queue.put_nowait(make_pretty(cmd))
                else:
                    raise Exception(f"Command not logged: {cmd}")
            except Exception as e:
                response_queue.put((cmd, "", f"Exec error: {str(e)}"))
    except Exception as e:
        response_queue.put(("ERROR", "", f"SSH error: {str(e)}"))
    finally:
        client.close()