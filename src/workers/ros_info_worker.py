import contextlib
import re
import select

import paramiko
from PyQt5.QtCore import QThread, pyqtSignal

from config import get_SSH_credentials
from workers.container_env import VOYAGE_LOG_DIR, WORKSPACE_ROOT, docker_exec

# How long select() waits between checks so stop() stays responsive.
STREAM_SELECT_TIMEOUT_SECONDS = 0.5
STREAM_CHUNK_SIZE = 4096

# The launch commands tee their combined stdout/stderr into VOYAGE_LOG_DIR (see
# Docker_Command_Type in data_object.py). That path is relative, so it lands
# under whatever directory the container command starts in - hence both the
# relative and workspace-anchored patterns below.
# All of these are globbed together and the single newest file wins, so a fresh
# run always beats a stale log from an older one. ``ros2 launch`` also writes
# ~/.ros/log/<run>/launch.log itself, which survives even if the tee does not.
LAUNCH_LOG_PATTERNS = (
    f"{VOYAGE_LOG_DIR}/combined_log_*.txt",
    f"{WORKSPACE_ROOT}/{VOYAGE_LOG_DIR}/combined_log_*.txt",
    "$HOME/.ros/log/*/launch.log",
)
# How long the remote side waits for a log file to show up before giving up, so
# attaching right after a launch does not lose the race against log creation.
LAUNCH_LOG_WAIT_SECONDS = 30
# When attaching to a launch we just started, only logs touched inside this
# window count. Without it the wait loop would settle on whatever old log is
# already lying around (the container keeps previous runs' combined logs) before
# the new run has written anything. Computed on the Pi, so clock skew between
# this machine and the Pi cannot skip a valid log.
RECENT_LOG_GRACE_SECONDS = 180
# Severities kept when following a launch log; everything else (INFO/DEBUG) is
# dropped remotely so only the interesting lines cross the SSH connection.
LAUNCH_LOG_SEVERITIES = ("FATAL", "ERROR", "WARNING", "WARN")
# Name shown above the live stream box while the launch log is being followed.
LAUNCH_LOG_STREAM_LABEL = "launch ERROR / WARN / FATAL logs"

# ros2/launch colourize their console output when a tty is attached; the pty we
# allocate counts as one, so the escape codes have to be stripped for display.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")
# Chatter the interactive shell writes into the pty; noise, not launch output.
_SHELL_NOISE_RE = re.compile(
    r"^(bash: cannot set terminal process group.*"
    r"|bash: no job control in this shell"
    r"|bash: .*tcsetattr: Inappropriate ioctl for device"
    r"|exit)\s*$"
)


def build_launch_log_command(
    tail_lines: int = 500,
    wait_seconds: int = LAUNCH_LOG_WAIT_SECONDS,
    *,
    recent_only: bool = False,
) -> str:
    """Builds a shell command that follows the newest global_launch log and
    emits only its FATAL/ERROR/WARN lines.

    The launch itself runs detached (``docker exec -d``), so its console output
    is only reachable through the log files it leaves behind. Those take a moment
    to appear, so the command waits for one rather than giving up immediately; if
    nothing shows up it reports where it looked (and from which directory) so the
    mismatch is visible in the GUI.

    ``recent_only`` restricts the search to logs touched in the last few minutes,
    which is what makes attaching to a launch we just started ignore leftovers
    from previous runs."""
    severities = "|".join(LAUNCH_LOG_SEVERITIES)
    # Unquoted so the container's shell expands the globs; patterns matching
    # nothing stay literal and are swallowed by find's suppressed stderr.
    globs = " ".join(LAUNCH_LOG_PATTERNS)
    patterns = " ".join(f'"{pattern}"' for pattern in LAUNCH_LOG_PATTERNS)
    floor = f"$(( $(date +%s) - {RECENT_LOG_GRACE_SECONDS} ))" if recent_only else "0"
    # Newest mtime across every pattern wins, so a run that starts while we are
    # waiting takes precedence over any log that already existed.
    newest_log = (
        f'find {globs} -maxdepth 0 -newermt "@$FLOOR" -printf "%T@ %p\\n" 2>/dev/null'
        ' | sort -rn | head -n 1 | cut -d " " -f 2-'
    )
    scope = (
        f"touched in the last {RECENT_LOG_GRACE_SECONDS}s"
        if recent_only
        else "in the searched locations"
    )
    return "\n".join(
        [
            f"FLOOR={floor}",
            "LOG=",
            "waited=0",
            f'while [ -z "$LOG" ] && [ "$waited" -lt {wait_seconds} ]; do',
            f"  LOG=$({newest_log})",
            '  if [ -z "$LOG" ]; then sleep 1; waited=$((waited + 1)); fi',
            "done",
            'if [ -z "$LOG" ]; then',
            (
                f'  echo "No launch log {scope} appeared within {wait_seconds}s'
                ' - is the software running?"'
            ),
            '  echo "Searched from $(pwd):"',
            f'  for pattern in {patterns}; do echo "  $pattern"; done',
            "  exit 1",
            "fi",
            'echo "=== following $LOG ==="',
            (
                f'tail -n {tail_lines} -F "$LOG" '
                f'| grep --line-buffered -E "\\[({severities})\\]"'
            ),
        ]
    )


def _clean_stream_text(text: str) -> str:
    """Strips ANSI colour codes, pty carriage returns and interactive-shell
    chatter from streamed output."""
    text = _ANSI_ESCAPE_RE.sub("", text).replace("\r\n", "\n").replace("\r", "")

    # The final element is whatever came before the chunk boundary; it may be a
    # partial line, so it is passed through untouched.
    lines = text.split("\n")
    kept = [line for line in lines[:-1] if not _SHELL_NOISE_RE.match(line)]
    kept.append(lines[-1])
    return "\n".join(kept)


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
    except paramiko.AuthenticationException as exc:
        raise RuntimeError(
            "Authentication failed. Check your username and password."
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"Could not connect to the Pi: {type(exc).__name__}: {exc}"
        ) from exc


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
            _, stdout, stderr = ssh.exec_command(
                docker_exec(self.container, self.ros_command)
            )
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode(errors="replace").strip()
            err = stderr.read().decode(errors="replace").strip()

            if exit_status != 0:
                self.error.emit(
                    err or out or f"'{self.ros_command}' exited {exit_status}."
                )
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
                docker_exec(self.container, self.ros_command),
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
                    self.line.emit(_clean_stream_text(data.decode(errors="replace")))
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
            # Best effort: the remote end may already be gone, and either way the
            # stream is finished, so a failure here has nothing to report.
            with contextlib.suppress(Exception):
                channel.close()

        ssh = self._ssh
        self._ssh = None
        if ssh is not None:
            with contextlib.suppress(Exception):
                ssh.close()
