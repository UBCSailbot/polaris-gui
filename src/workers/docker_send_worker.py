import paramiko
from PyQt5.QtCore import QThread, pyqtSignal

from config import get_SSH_credentials
from data_object import Docker_Command, Docker_Command_Type


class DockerWorkerThread(QThread):
    success = pyqtSignal(Docker_Command_Type)  # action name
    error = pyqtSignal(str)  # error message
    output = pyqtSignal(str)

    def __init__(self, command: str, action: Docker_Command):
        super().__init__()
        self.command = command
        self.action = action

    def run(self):
        try:
            out = send_docker_command(self.command)

            if self.action.command_type == Docker_Command_Type.LIST_CONTAINERS:
                self.output.emit(out)

            self.success.emit(self.action.command_type)
        except Exception as e:
            self.error.emit(str(e))


def generate_docker_command(action: Docker_Command, container_name: str):
    command_text = ""

    match action.command_type:
        case Docker_Command_Type.STOP:
            print(f"Stopping container: {container_name}")
            command_text = f"{action.command} {container_name}"
        case Docker_Command_Type.LIST_CONTAINERS:
            print("Listing all availible containers:")
            command_text = action.command
        case _:
            run_text = f'docker exec -d {container_name} bash -ic "'
            command_text = (
                f'docker start {container_name} && {run_text} {action.command}"'
            )
            print(
                f"Running {action.command_type.name} on docker container {container_name}"
            )

    return command_text


def send_docker_command(command: str) -> str:
    # Set up the SSH Client
    ssh = paramiko.SSHClient()
    # Automatically add the server's SSH key (prevents "unknown host" errors)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    hostname, username, password = get_SSH_credentials()
    try:
        # Connect to the remote server
        ssh.connect(
            hostname=hostname,
            username=username,
            password=password,
            timeout=5,
        )

        # Execute the command over SSH
        _, stdout, stderr = ssh.exec_command(command)

        # Wait for the command to finish and get the exit status
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()

        print(f"[SSH] command: {command}")
        print(f"[SSH] exit_status: {exit_status}")
        print(f"[SSH] stdout: {out}")
        print(f"[SSH] stderr: {err}")

        if exit_status != 0:
            raise RuntimeError(err)

        return out

    except paramiko.AuthenticationException:
        raise RuntimeError("Authentication failed. Check your username and password.")

    finally:
        # Always close the connection when done!
        ssh.close()


# Add as a separate method to avoid blocking.
def kill_software():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    hostname, username, password = get_SSH_credentials()
    try:
        ssh.connect(
            hostname=hostname,
            username=username,
            password=password,
            timeout=2,
        )
        command = (
            'if [ -n "$(docker ps -q)" ]; then '
            "docker kill $(docker ps -q); "
            "echo 'Stopped all running Docker containers.'; "
            "else echo 'No running Docker containers found.'; fi"
        )
        _, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()

        print(f"[SSH] command: {command}")
        print(f"[SSH] exit_status: {exit_status}")
        print(f"[SSH] stdout: {out}")
        print(f"[SSH] stderr: {err}")

        if exit_status != 0:
            raise RuntimeError(err or out or "Failed to kill software.")

        return out or "Kill command completed."

    except paramiko.AuthenticationException:
        raise RuntimeError("Authentication failed. Check your username and password.")

    except Exception as e:
        raise RuntimeError(f"Failed to kill software: {str(e)}")

    finally:
        ssh.close()
