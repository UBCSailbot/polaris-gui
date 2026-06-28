import select
import socket
import socketserver
from typing import Optional

import paramiko
from PyQt5.QtCore import QThread, pyqtSignal

from config import hostname, password, username


# Port the Dash visualizer binds to on the Pi and locally after forwarding.
VISUALIZER_PORT = 8050
BUFFER_SIZE = 1024


class ForwardServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class ForwardHandler(socketserver.BaseRequestHandler):
    """Forwards traffic from a local socket to a remote host through SSH."""

    ssh_transport: paramiko.Transport
    remote_host: str
    remote_port: int

    def handle(self) -> None:
        try:
            channel = self.ssh_transport.open_channel(
                kind="direct-tcpip",
                dest_addr=(self.remote_host, self.remote_port),
                src_addr=self.request.getpeername(),
            )
        except Exception:
            return

        if channel is None:
            return

        try:
            self._forward_between(self.request, channel)
        finally:
            channel.close()
            self.request.close()

    @staticmethod
    def _forward_between(local_socket: socket.socket, ssh_channel: paramiko.Channel) -> None:
        """Bidirectionally forwards bytes between the local socket and SSH channel."""
        while True:
            readable, _, _ = select.select([local_socket, ssh_channel], [], [])

            if local_socket in readable:
                data = local_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                ssh_channel.sendall(data)

            if ssh_channel in readable:
                data = ssh_channel.recv(BUFFER_SIZE)
                if not data:
                    break
                local_socket.sendall(data)


def make_forward_server(
    local_port: int,
    remote_host: str,
    remote_port: int,
    transport: paramiko.Transport,
) -> ForwardServer:
    """Creates a local TCP server that forwards traffic through an SSH transport."""

    class SubHandler(ForwardHandler):
        ssh_transport = transport
        remote_host = remote_host
        remote_port = remote_port

    return ForwardServer(("", local_port), SubHandler)


class VisualizerTunnelThread(QThread):
    """Starts an SSH tunnel to the Dash visualizer running on the Pi.

    Equivalent to:

        ssh -N -L <local_port>:localhost:<remote_port> user@host

    Once ready, http://localhost:<local_port> reaches the Dash app on the Pi.
    """

    status = pyqtSignal(str)
    error = pyqtSignal(str)
    tunnel_ready = pyqtSignal(int)

    def __init__(
        self,
        local_port: int = VISUALIZER_PORT,
        remote_port: int = VISUALIZER_PORT,
    ) -> None:
        super().__init__()
        self.local_port = local_port
        self.remote_port = remote_port

        self._server: Optional[ForwardServer] = None
        self._ssh: Optional[paramiko.SSHClient] = None

    def run(self) -> None:
        ssh = self._connect_to_pi()
        if ssh is None:
            return

        self._ssh = ssh

        try:
            if not self._is_visualizer_listening(ssh):
                self.error.emit(
                    f"Visualizer is not listening on port {self.remote_port} on the Pi yet. "
                    "Please press Stop Container and then press Start w/ visualizer again."
                )
                return

            self.status.emit(
                f"Visualizer is live on the Pi on port {self.remote_port}."
            )

            transport = ssh.get_transport()
            if transport is None or not transport.is_active():
                self.error.emit("SSH transport is not active.")
                return

            self._server = make_forward_server(
                local_port=self.local_port,
                remote_host="localhost",
                remote_port=self.remote_port,
                transport=transport,
            )

            self.tunnel_ready.emit(self.local_port)
            self._server.serve_forever()

        except OSError as exc:
            self.error.emit(
                f"Could not bind local port {self.local_port}. "
                "The tunnel may already be running. "
                "Please press Stop Container and then press Start w/ visualizer again. "
                f"Details: {exc}"
            )

        except Exception as exc:
            self.error.emit(f"Visualizer tunnel failed: {exc}")

        finally:
            self._cleanup()

    def stop(self) -> None:
        """Stops the port-forward server and closes the SSH connection."""
        self._cleanup()

    def _connect_to_pi(self) -> Optional[paramiko.SSHClient]:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                hostname=hostname,
                username=username,
                password=password,
                timeout=5,
            )
            return ssh

        except paramiko.AuthenticationException:
            self.error.emit("Authentication failed. Check your username and password.")
            return None

        except Exception as exc:
            self.error.emit(f"Could not connect to the Pi: {exc}")
            return None

    def _is_visualizer_listening(self, ssh: paramiko.SSHClient) -> bool:
        """Checks whether the Dash visualizer is listening on the Pi."""
        command = f"ss -tlnH 'sport = :{self.remote_port}'"

        try:
            _, stdout, stderr = ssh.exec_command(command)

            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode(errors="replace").strip()
            error_output = stderr.read().decode(errors="replace").strip()

            if exit_status == 0 and output:
                return True

            self.status.emit(
                f"Visualizer port check returned no listener. "
                f"exit_status={exit_status}, stdout={output!r}, stderr={error_output!r}"
            )
            return False
        except Exception as exc:
            self.error.emit(
                "Could not check the visualizer port on the Pi. "
                "Please press Stop Container and then press Start w/ visualizer again. "
                f"Details: {exc}"
            )
            return False

    def _cleanup(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

        if self._ssh is not None:
            self._ssh.close()
            self._ssh = None