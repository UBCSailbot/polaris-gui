import select
import socketserver

import paramiko
from PyQt5.QtCore import QThread, pyqtSignal

from config import hostname, password, username

# Port the Dash visualizer binds to (on the Pi and, after forwarding, locally)
VISUALIZER_PORT = 8050


class _ForwardServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class _ForwardHandler(socketserver.BaseRequestHandler):
    # These class attributes are filled in by forward_tunnel() via a subclass
    ssh_transport = None
    chain_host = None
    chain_port = None

    def handle(self):
        try:
            chan = self.ssh_transport.open_channel(
                "direct-tcpip",
                (self.chain_host, self.chain_port),
                self.request.getpeername(),
            )
        except Exception:
            return
        if chan is None:
            return

        while True:
            r, _, _ = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)

        chan.close()
        self.request.close()


def _make_forward_server(local_port, remote_host, remote_port, transport):
    """Bind a local port and forward all of its traffic over the SSH transport
    to remote_host:remote_port (as seen from the SSH server)."""

    class SubHandler(_ForwardHandler):
        ssh_transport = transport
        chain_host = remote_host
        chain_port = remote_port

    return _ForwardServer(("", local_port), SubHandler)


class VisualizerTunnelThread(QThread):
    """Verifies the Dash visualizer is live on the Pi, then opens a local
    SSH port-forward so http://localhost:<local_port> reaches it.

    Equivalent to: ssh -N -L <local_port>:localhost:<remote_port> user@host
    """

    status = pyqtSignal(str)  # human-readable progress message
    error = pyqtSignal(str)  # error message
    tunnel_ready = pyqtSignal(int)  # local port the tunnel is listening on

    def __init__(self, local_port=VISUALIZER_PORT, remote_port=VISUALIZER_PORT):
        super().__init__()
        self.local_port = local_port
        self.remote_port = remote_port
        self._server = None
        self._ssh = None

    def run(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(hostname, username=username, password=password, timeout=5)
        except paramiko.AuthenticationException:
            self.error.emit("Authentication failed. Check your username and password.")
            return
        except Exception as e:
            self.error.emit(f"Could not connect to the Pi: {e}")
            return

        self._ssh = ssh

        # 1. Confirm the visualizer is actually listening on the Pi.
        #    (No sudo so SSH stays non-interactive; the LISTEN line is enough.)
        try:
            _, stdout, _ = ssh.exec_command(f"ss -tln | grep ':{self.remote_port}'")
            stdout.channel.recv_exit_status()
            listening = stdout.read().decode().strip()
        except Exception as e:
            self.error.emit(f"Could not check the visualizer port on the Pi: {e}")
            ssh.close()
            return

        if not listening:
            self.error.emit(
                f"Visualizer is not listening on port {self.remote_port} on the Pi "
                "yet. Give it a moment after starting, then try again."
            )
            ssh.close()
            return

        self.status.emit(f"Visualizer is live on the Pi (port {self.remote_port}).")

        # 2. Open the local port-forward over the existing SSH transport.
        try:
            self._server = _make_forward_server(
                self.local_port, "localhost", self.remote_port, ssh.get_transport()
            )
        except OSError as e:
            self.error.emit(
                f"Could not bind local port {self.local_port} "
                f"(is the tunnel already running?): {e}"
            )
            ssh.close()
            return

        self.tunnel_ready.emit(self.local_port)

        try:
            self._server.serve_forever()
        finally:
            ssh.close()

    def stop(self):
        """Tear down the tunnel and close the SSH connection."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._ssh is not None:
            self._ssh.close()
            self._ssh = None
