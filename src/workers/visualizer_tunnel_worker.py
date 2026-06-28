import select
import socket
import socketserver
import time
from typing import Optional

import paramiko
from PyQt5.QtCore import QThread, pyqtSignal

from config import hostname, password, username

# Port the Dash visualizer binds to on the Pi and locally after forwarding.
VISUALIZER_PORT = 8050
BUFFER_SIZE = 1024

# The Dash app takes a few seconds to bind its port after the container starts,
# so poll for it instead of checking just once.
LISTEN_POLL_ATTEMPTS = 20
LISTEN_POLL_DELAY_SECONDS = 2.0


class ForwardServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class ForwardHandler(socketserver.BaseRequestHandler):
    """Forwards traffic from a local socket to a remote host through SSH."""

    # Filled in per-tunnel by make_forward_server() via a subclass.
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
    def _forward_between(
        local_socket: socket.socket, ssh_channel: paramiko.Channel
    ) -> None:
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
    target_host: str,
    target_port: int,
    transport: paramiko.Transport,
) -> ForwardServer:
    """Creates a local TCP server that forwards traffic through an SSH transport.

    NOTE: target_host/target_port intentionally differ from the handler's
    remote_host/remote_port attribute names. Reusing the same name inside the
    class body (e.g. ``remote_host = remote_host``) raises NameError, because
    the assignment makes it a class-local that shadows the function argument.
    """

    class SubHandler(ForwardHandler):
        ssh_transport = transport
        remote_host = target_host
        remote_port = target_port

    return ForwardServer(("", local_port), SubHandler)


class VisualizerTunnelThread(QThread):
    """Creates a tunnel equivalent to:

        ssh -N -L 8050:localhost:8050 sailbot@100.95.219.3

    Then http://localhost:8050 on the laptop reaches the Dash visualizer on the Pi.
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
        self._stop_requested = False

    def run(self) -> None:
        ssh = self._connect_to_pi()
        if ssh is None:
            return

        self._ssh = ssh

        try:
            if not self._wait_for_visualizer(ssh):
                self.error.emit(
                    f"Visualizer never came up on port {self.remote_port} on the Pi "
                    f"after {LISTEN_POLL_ATTEMPTS * LISTEN_POLL_DELAY_SECONDS:.0f}s. "
                    "Make sure the container was started with visualizer_mode:=true."
                )
                return

            self.status.emit(
                f"Visualizer is listening on the Pi at 127.0.0.1:{self.remote_port}."
            )

            transport = ssh.get_transport()
            if transport is None or not transport.is_active():
                self.error.emit("SSH transport is not active.")
                return

            self._server = make_forward_server(
                local_port=self.local_port,
                target_host="127.0.0.1",
                target_port=self.remote_port,
                transport=transport,
            )

            self.status.emit(
                f"Tunnel open: http://localhost:{self.local_port} forwards to "
                f"Pi 127.0.0.1:{self.remote_port}."
            )
            self.tunnel_ready.emit(self.local_port)

            self._server.serve_forever()

        except OSError as exc:
            self.error.emit(
                f"Could not bind local port {self.local_port}. "
                "The tunnel may already be running. "
                f"Details: {exc}"
            )

        except Exception as exc:
            self.error.emit(f"Visualizer tunnel failed: {type(exc).__name__}: {exc}")

        finally:
            self._cleanup()

    def stop(self) -> None:
        self._stop_requested = True
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
            self.error.emit("Authentication failed. Check username/password.")
            return None

        except Exception as exc:
            self.error.emit(f"Could not connect to the Pi: {type(exc).__name__}: {exc}")
            return None

    def _wait_for_visualizer(self, ssh: paramiko.SSHClient) -> bool:
        """Polls the Pi until the visualizer port is listening, or attempts run
        out. Returns True as soon as it is up."""
        for attempt in range(1, LISTEN_POLL_ATTEMPTS + 1):
            if self._stop_requested:
                return False

            if self._is_visualizer_listening(ssh):
                return True

            if attempt < LISTEN_POLL_ATTEMPTS:
                self.status.emit(
                    f"Waiting for visualizer on :{self.remote_port} "
                    f"(attempt {attempt}/{LISTEN_POLL_ATTEMPTS})..."
                )
                time.sleep(LISTEN_POLL_DELAY_SECONDS)

        return False

    def _is_visualizer_listening(self, ssh: paramiko.SSHClient) -> bool:
        """Equivalent to: ss -tln | grep :8050 run on the Pi host.

        /usr/sbin and /sbin are added to PATH because a non-interactive SSH
        command gets a minimal PATH that often omits them, so a bare `ss` would
        fail with "command not found". The `-E ':PORT([^0-9]|$)'` filter matches
        the port exactly (so :8050 does not also match :80500)."""

        command = (
            f"PATH=$PATH:/usr/sbin:/sbin ss -tln | "
            f"grep -E ':{self.remote_port}([^0-9]|$)'"
        )

        try:
            _, stdout, stderr = ssh.exec_command(command)

            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode(errors="replace").strip()
            error_output = stderr.read().decode(errors="replace").strip()

            # grep prints the matching LISTEN line(s) iff the port is bound.
            if output:
                return True

            print(f"[SSH] command: {command}")
            print(f"[SSH] exit_status: {exit_status}")
            print(f"[SSH] stdout: {output}")
            print(f"[SSH] stderr: {error_output}")

            return False

        except Exception as exc:
            self.error.emit(
                "Could not check the visualizer port on the Pi. "
                f"Details: {type(exc).__name__}: {exc}"
            )
            return False

    def _cleanup(self) -> None:
        server = self._server
        self._server = None

        if server is not None:
            server.shutdown()
            server.server_close()

        ssh = self._ssh
        self._ssh = None

        if ssh is not None:
            ssh.close()
