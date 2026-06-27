import paramiko
from PyQt5.QtCore import QThread, pyqtSignal

from config import hostname, password, username
from data_object import Docker_Commands


class DockerWorkerThread(QThread):
    success = pyqtSignal(Docker_Commands)  # action name
    error = pyqtSignal(str)  # error message

    def __init__(self, command: str, action: Docker_Commands):
        super().__init__()
        self.command = command
        self.action = action

    def run(self):
        try:
            send_docker_command(self.command)
            self.success.emit(self.action)
        except Exception as e:
            self.error.emit(str(e))


def generate_docker_command(action: Docker_Commands, container_name: str):
    command_text = "docker "

    match action:
        case Docker_Commands.STOP:
            command_text += f"stop {container_name}"
        case _:
            run_text = f'docker exec -d {container_name} bash -ic "'
            command_text += f'start {container_name} && {run_text} {action.value}"'

    return command_text


def send_docker_command(command: str):
    # Set up the SSH Client
    ssh = paramiko.SSHClient()
    # Automatically add the server's SSH key (prevents "unknown host" errors)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the remote server
        ssh.connect(hostname, username=username, password=password, timeout=5)

        # Execute the command over SSH
        _, stdout, stderr = ssh.exec_command(command)

        # Wait for the command to finish and get the exit status
        exit_status = stdout.channel.recv_exit_status()
        err = stderr.read().decode().strip()

        if exit_status != 0:
            raise RuntimeError(err)

    except paramiko.AuthenticationException:
        raise RuntimeError("Authentication failed. Check your username and password.")

    finally:
        # Always close the connection when done!
        ssh.close()


# Add as a separate method to avoid blocking.
def kill_software():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname, username=username, password=password, timeout=2)
        command = "docker kill $(docker ps -q)"
        ssh.exec_command(command)

    except paramiko.AuthenticationException:
        raise RuntimeError("Authentication failed. Check your username and password.")

    except Exception as e:
        raise RuntimeError(f"Failed to kill software: {str(e)}")

    finally:
        ssh.close()
