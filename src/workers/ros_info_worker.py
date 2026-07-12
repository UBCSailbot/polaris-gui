import select

import paramiko
from PyQt5.QtCore import QThread, pyqtSignal

from config import get_SSH_credentials

# How long select() waits between checks so stop() stays responsive.
STREAM_SELECT_TIMEOUT_SECONDS = 0.5
STREAM_CHUNK_SIZE = 4096


def _connect_to_pi(timeout: int = 5) -> paramiko.SSHClient:
    """Opens an SSH connection to the Pi using the configured credentials.

    Raises RuntimeError on failure so callers can surface a clean message."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    hostname, username, password = get_SSH_credentials()
    try:
        ssh.connect(
            hostname=hostname,
            username=username,
            password=password,
            timeout=timeout,
        )
        return ssh
    except paramiko.AuthenticationException:
        raise RuntimeError("Authentication failed. Check your username and password.")
    except Exception as exc:
        raise RuntimeError(f"Could not connect to the Pi: {type(exc).__name__}: {exc}")


def _docker_exec(container: str, ros_command: str) -> str:
    """Wraps a ros2 command so it runs inside the container with ROS sourced.

    ``bash -ic`` is used (matching the docker launch path) so the interactive
    bashrc sources the ROS environment before the command runs."""
    return f'docker exec {container} bash -ic "{ros_command}"'


class RosCommandThread(QThread):
    """Runs a one-shot ros2 command (e.g. ``ros2 node list``) and returns its
    output. Used for snapshots that complete and exit on their own."""

    result = pyqtSignal(str)  # command stdout
    error = pyqtSignal(str)  # error message

    def __init__(self, container: str, ros_command: str) -> None:
        super().__init__()
        self.container = container
        self.ros_command = ros_command

    def run(self) -> None:
        try:
            ssh = _connect_to_pi()
        except RuntimeError as exc:
            self.error.emit(str(exc))
            return

        try:
            _, stdout, stderr = ssh.exec_command(_docker_exec(self.container, self.ros_command))
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode(errors="replace").strip()
            err = stderr.read().decode(errors="replace").strip()

            if exit_status != 0:
                self.error.emit(err or out or f"'{self.ros_command}' exited {exit_status}.")
                return

            self.result.emit(out or "(no output)")
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")
        finally:
            ssh.close()


class RosStreamThread(QThread):
    """Streams a long-running ros2 command (e.g. ``ros2 topic echo /rosout``)
    line by line until stop() is called.

    A pty is allocated so that closing the channel sends SIGHUP to the remote
    process, preventing an orphaned ros2 process on the Pi."""

    line = pyqtSignal(str)  # a chunk of streamed stdout
    error = pyqtSignal(str)  # error message

    def __init__(self, container: str, ros_command: str) -> None:
        super().__init__()
        self.container = container
        self.ros_command = ros_command

        self._ssh: paramiko.SSHClient | None = None
        self._channel: paramiko.Channel | None = None
        self._stop_requested = False

    def run(self) -> None:
        try:
            ssh = _connect_to_pi()
        except RuntimeError as exc:
            self.error.emit(str(exc))
            return

        self._ssh = ssh
        try:
            _, stdout, _ = ssh.exec_command(
                _docker_exec(self.container, self.ros_command),
                get_pty=True,
            )
            channel = stdout.channel
            self._channel = channel

            while not self._stop_requested:
                readable, _, _ = select.select(
                    [channel], [], [], STREAM_SELECT_TIMEOUT_SECONDS
                )
                if channel in readable and channel.recv_ready():
                    data = channel.recv(STREAM_CHUNK_SIZE)
                    if not data:
                        break
                    self.line.emit(data.decode(errors="replace"))
                elif channel.exit_status_ready() and not channel.recv_ready():
                    break
        except Exception as exc:
            if not self._stop_requested:
                self.error.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self._cleanup()

    def stop(self) -> None:
        self._stop_requested = True
        self._cleanup()

    def _cleanup(self) -> None:
        channel = self._channel
        self._channel = None
        if channel is not None:
            try:
                channel.close()
            except Exception:
                pass

        ssh = self._ssh
        self._ssh = None
        if ssh is not None:
            try:
                ssh.close()
            except Exception:
                pass
