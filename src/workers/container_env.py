"""Shared setup for the commands the GUI runs inside the sailbot container.

Every ros2 command the GUI sends goes through ``docker exec``, which starts a
fresh shell rather than reusing the devcontainer terminal a human would type
into. That shell only has ROS on its PATH if the container user's interactive
bashrc happens to source it, which is why a GUI-triggered launch could tee
nothing but ``ros2: command not found`` into its combined log. The environment
is therefore sourced explicitly here instead of being assumed.
"""

import shlex

WORKSPACE_ROOT = "/workspaces/sailbot_workspace"
# Where the launch commands tee their combined stdout/stderr. Relative, so it
# only resolves once the prelude below has moved into the workspace.
VOYAGE_LOG_DIR = "src/global_launch/voyage_log"

# Runs before every container command:
#  - move into the workspace, since `docker exec` starts in the image's WORKDIR
#    and the launch commands use workspace-relative paths;
#  - source the ROS distro (whichever one is installed) and then the workspace
#    overlay, which is what makes `global_launch` resolvable;
#  - make sure the tee target exists, so a launch cannot die on a missing dir.
# Each step is guarded so a container laid out differently still runs the
# command instead of failing in the prelude.
_CONTAINER_PRELUDE = "\n".join(
    [
        f'if [ -d "{WORKSPACE_ROOT}" ]; then cd "{WORKSPACE_ROOT}"; fi',
        'if [ -z "$ROS_DISTRO" ]; then',
        "  ROS_DISTRO=$(ls /opt/ros 2>/dev/null | head -n 1)",
        "fi",
        'if [ -f "/opt/ros/$ROS_DISTRO/setup.bash" ]; then',
        '  . "/opt/ros/$ROS_DISTRO/setup.bash"',
        "fi",
        "if [ -f install/setup.bash ]; then . install/setup.bash; fi",
        f"mkdir -p {VOYAGE_LOG_DIR} 2>/dev/null",
    ]
)


def container_command(ros_command: str) -> str:
    """Prefixes a command with the environment setup it needs in-container."""
    return f"{_CONTAINER_PRELUDE}\n{ros_command}"


def docker_exec(container: str, ros_command: str, *, detach: bool = False) -> str:
    """Wraps a command so it runs inside the container with ROS sourced.

    ``bash -ic`` is kept so the interactive bashrc still contributes whatever
    else it sets (DDS configuration, domain id, ...); the prelude only covers
    what must be there. The command is single-quoted so the Pi's shell hands it
    to the container untouched instead of expanding ``$(...)``/globs itself."""
    flags = "-d " if detach else ""
    return (
        f"docker exec {flags}{container} bash -ic "
        f"{shlex.quote(container_command(ros_command))}"
    )
