import multiprocessing
import time

import paramiko


def ros2_output_process(
    queue: multiprocessing.Queue,
    container_name_queue: multiprocessing.Queue,
    credentials: tuple[str, str, str],
):
    """
    Stream ROS2 output from docker container to a queue.

    Args:
        queue: Multiprocessing queue to put ROS2 output lines
        container_name_queue: Queue to get the container name (updated in real-time)
        credentials: SSH credentials tuple (hostname, username, password)
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    hostname, username, password = credentials
    transport = None
    channel = None
    current_container = None

    try:
        client.connect(
            hostname=hostname,
            username=username,
            password=password,
        )
        transport = client.get_transport()

        while True:
            try:
                # Check if container name has changed (non-blocking check)
                try:
                    new_container = container_name_queue.get_nowait()
                    if new_container != current_container:
                        current_container = new_container
                        if channel is not None:
                            channel.close()
                            channel = None
                        if current_container:
                            msg = f"[INFO] Connecting to container: {current_container}"
                            queue.put(msg)
                except Exception:
                    pass  # No new container name

                # If no container is selected, wait and try again
                if not current_container:
                    time.sleep(0.5)
                    continue

                # If channel is not active, try to create one
                if channel is None:
                    if transport is None or not transport.is_active():
                        client.close()
                        client = paramiko.SSHClient()
                        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        client.connect(
                            hostname=hostname,
                            username=username,
                            password=password,
                        )
                        transport = client.get_transport()

                    channel = transport.open_session()
                    channel.set_combine_stderr(True)
                    # Tail the most recent ROS2 log file using bash
                    cmd = (
                        f"docker exec {current_container} bash -c "
                        "'tail -f src/global_launch/voyage_log/combined_log_*.txt "
                        "2>/dev/null'"
                    )
                    channel.exec_command(cmd)
                    msg = f"[INFO] Streaming output from container: {current_container}"
                    queue.put(msg)

                # Try to read available data (non-blocking style)
                if channel.recv_ready():
                    try:
                        data = channel.recv(4096)
                        if data:
                            lines = data.decode("utf-8", errors="ignore").split("\n")
                            for output_line in lines:
                                stripped = output_line.strip()
                                if stripped:
                                    queue.put(stripped)
                        else:
                            # Channel closed
                            channel = None
                    except Exception as read_err:
                        queue.put(f"[ERROR] Read error: {str(read_err)}")
                        channel = None
                else:
                    time.sleep(0.1)

            except paramiko.SSHException as ssh_err:
                channel = None
                queue.put(f"[ERROR] SSH error: {str(ssh_err)}")
                time.sleep(1)
            except Exception as stream_err:
                channel = None
                queue.put(f"[ERROR] {str(stream_err)}")
                time.sleep(1)

    except paramiko.AuthenticationException:
        queue.put("[ERROR] Authentication failed")
    except Exception as conn_err:
        queue.put(f"[ERROR] Connection failed: {str(conn_err)}")
    finally:
        if channel is not None:
            try:
                channel.close()
            except Exception:
                pass
        if client is not None:
            client.close()


def check_container_running(
    container_name: str, credentials: tuple[str, str, str]
) -> bool:
    """
    Check if a docker container is currently running.

    Args:
        container_name: Name of the docker container
        credentials: SSH credentials tuple (hostname, username, password)

    Returns:
        True if container is running, False otherwise
    """
    if not container_name or not container_name.strip():
        return False

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        hostname, username, password = credentials

        ssh.connect(
            hostname=hostname,
            username=username,
            password=password,
            timeout=2,
        )

        cmd = f"docker inspect -f '{{{{.State.Running}}}}' {container_name}"
        _, stdout, _ = ssh.exec_command(cmd)
        result = stdout.read().decode().strip()
        ssh.close()

        return result.lower() == "true"

    except Exception as e:
        print(f"[ERROR] Failed to check container status: {str(e)}")
        return False
