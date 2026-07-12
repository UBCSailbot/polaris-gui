import webbrowser
from types import SimpleNamespace

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QMessageBox,
)

from config import pid_param_categories, pid_params
from data_object import DataObject, Docker_Command, Docker_Command_Type
from utils import all_objs
from workers.docker_send_worker import (
    DockerWorkerThread,
    generate_docker_command,
    kill_software,
)
from workers.visualizer_tunnel_worker import VisualizerTunnelThread

from . import elements as elemns
from . import styles as styles


# UI creation functions
class CANWindowUIMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def init_ui(self):
        top_bar_layout = elemns.init_top_bar(self)
        ssh_layout = elemns.init_ssh_dropdown(self)
        checkbox_layout = elemns.init_checkbox(self)

        self.instructions1_display = QLabel(
            "For Rudder    (+/- 3 degrees): A / S / D  (Left / Center / Right)"
        )
        self.instructions2_display = QLabel(
            "For Trim Tab (+/- 3 degrees): Q / W / E (Left / Center / Right)"
        )

        self.rudder_display = QLabel("Current Set Rudder Angle:  0 degrees")
        self.trimtab_display = QLabel("Current Trim Tab Angle:   0 degrees")

        self.desired_heading_input_group = elemns.init_desired_heading_input_group(self)
        self.rudder_input_group = elemns.init_rudder_input_group(self)
        self.trim_input_group = elemns.init_trim_input_group(self)

        self.pid_layout = elemns.init_pid_layout(self)

        # TODO: create a similar elemns function to abstract out creation of PID params
        # UI elements

        self.pid_param_dropdown_layout = elemns.init_pid_dropdown_layout(self)
        self.pid_param_input_layout = elemns.init_pid_input_layout(self)

        software_commands = [
            ("Start Software", Docker_Command(Docker_Command_Type.START)),
            ("Stop Software", Docker_Command(Docker_Command_Type.STOP)),
            (
                "Enable CAN Communcations",
                Docker_Command(Docker_Command_Type.START_COMMS),
            ),
            (
                "Disable CAN Communications",
                Docker_Command(Docker_Command_Type.STOP_COMMS),
            ),
            ("Start w/ visualizer", Docker_Command(Docker_Command_Type.START_VISUAL)),
            (
                "RECEIVE",
                Docker_Command(Docker_Command_Type.ROS_SERVICE_CALL),
            ),
        ]
        software_controls_layout = elemns.init_software_controls(
            self, software_commands
        )

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setMinimumWidth(350)

        # Separate terminal output display
        self.terminal_output_display = QTextEdit()
        self.terminal_output_display.setReadOnly(True)

        emergency_controls_layout = elemns.init_emergency_controls(self)

        # SSH Instructions for CAN and system control
        self.ssh_instructions_label = QLabel(
            "SSH Terminal Instructions:\n"
            "1. Open separate terminal/PowerShell\n"
            "2. ssh sailbot@192.168.0.10\n"
            "3. Password: sailbot\n"
            "Use buttons below to copy commands:"
        )

        self.ssh_instructions_label.setStyleSheet(styles.instructions_label)
        # Define commands with labels
        commands = [
            ("SSH Connect", "ssh sailbot@192.168.0.10"),
            ("CAN0 Down", "sudo ip link set can0 down"),
            (
                "CAN0 Up",
                "sudo ip link set can0 up type can bitrate 500000 dbitrate 1000000 fd on",
            ),
            # ("Check CAN Status", "ip link show can0"),
            # ("View System Logs", "dmesg | tail"),
            # ("System Info", "uname -a")
        ]

        self.commands_grid = elemns.init_commands_grid(self, commands)

        input_layout = elemns.init_input_layout(self)

        left_layout = elemns.init_left_layout(
            self,
            top_bar_layout,
            ssh_layout,
            checkbox_layout,
            input_layout,
            emergency_controls_layout,
            software_controls_layout,
        )

        # Graph Dropdown
        self.advanced_soft_panel = elemns.init_advanced_soft_panel(self)
        self.advanced_soft_panel_label = "Advanced Software Controls"
        self.advanced_soft_panel_entry = SimpleNamespace(
            dropdown_label=self.advanced_soft_panel_label,
            graph=self.advanced_soft_panel,
        )

        labels_layout = elemns.init_labels_layout()
        right_layout = elemns.init_right_layout(self)

        # Combine everything
        bottom_layout = QHBoxLayout()
        bottom_layout.addLayout(left_layout)
        bottom_layout.addLayout(labels_layout)
        bottom_layout.addLayout(right_layout, 1)

        self.setLayout(bottom_layout)

    def set_manual_steer(self, checked):
        self.rudder_input_group.setVisible(checked)
        self.desired_heading_input_group.setVisible(not checked)

    def toggle_keyboard_mode(self, checked):
        self.rudder_input.setDisabled(checked)
        self.rudder_button.setDisabled(checked)
        self.trim_input.setDisabled(checked)
        self.trim_button.setDisabled(checked)
        self.set_joystick_enabled(checked)

    def toggle_emergency_buttons(self, state):
        enabled = state == Qt.Checked
        self.power_off_btn.setEnabled(enabled)
        self.restart_btn.setEnabled(enabled)

    def copy_to_clipboard(self, text):
        """Copy text to system clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        # Show a brief confirmation
        self.output_display.append(f"[COPIED] {text}")

    def append_docker_log(self, message: str) -> None:
        if getattr(self, "docker_log_display", None) is not None:
            self.docker_log_display.append(message)

    def log_and_report_docker_error(self, message: str) -> None:
        self.append_docker_log(f"[ERROR] {message}")
        self.show_error(message, log_to_output=False)

    def log_docker_action(self, action: Docker_Command, container_name: str) -> None:
        self.append_docker_log(
            f"[{action.command_type.name}] Queued docker action for "
            f"container '{container_name}'."
        )

    def update_pid_param_dropdown(self, text: str) -> None:
        """Updates the PID param dropdown based on the category selected"""
        first, last = pid_param_categories[text]
        self.pid_param_dropdown.clear()
        self.pid_param_dropdown.addItems(pid_params[first:last])
        return

    # NOTE: Commented out this function as I don't need it
    # def getGraphObjFromXName(self, name):
    #     for obj in all_objs:
    #         if ((obj.graph_obj is not None) and (obj.graph_obj.dropdown_label == name)):
    #             return obj.graph_obj

    def getObjFromLabel(self, dropdown_label) -> DataObject:
        for obj in all_objs:
            if (obj.graph_obj is not None) and (
                obj.graph_obj.dropdown_label == dropdown_label
            ):
                return obj

    def setGraph(self, name: str, spot: int, dropdowns: list[QComboBox]) -> None:
        """
        Shows given graph at spot\n
        name = DataObj.graph_obj.dropdown_label\n
        spot = 0, 1, 2 (top, mid, bot)\n
        """
        # Check if the 'graph' is actually button pannel
        # TODO refactor this function to support rendering any pyqt widget
        if name == getattr(self, "advanced_soft_panel_label", None):
            newGraphObj = self.advanced_soft_panel_entry
            newObj = None
        else:
            newObj = self.getObjFromLabel(name)
            # newGraphObj = self.getGraphObjFromXName(name) # get graph to put in spot
            newGraphObj = newObj.graph_obj

        if newGraphObj.dropdown_label == self.visibleGraphObjs[spot].dropdown_label:
            return  # do nothing
        if (
            newGraphObj in self.visibleGraphObjs
        ):  # if graph to put in spot is already visible
            # don't allow the switch to happen - set dropdown text back to original and print error message
            print("[ERR] Graph is already visible")
            dropdowns[spot].setCurrentText(
                self.visibleGraphObjs[spot].dropdown_label
            )  # switch text back to original
        else:
            current_widget = self.visibleGraphObjs[spot].graph
            self.right_graphs_layout.removeWidget(current_widget)
            current_widget.hide()
            self.right_graphs_layout.addWidget(newGraphObj.graph, spot, 0)
            newGraphObj.graph.show()
            self.visibleGraphObjs[spot] = newGraphObj
            # Check again if the 'graph' is a real graph that needs updates
            if newObj is not None and hasattr(newObj, "update_line_data"):
                newObj.update_line_data()

        dropdowns[spot].clearFocus()

    def run_docker_command(self, action: Docker_Command):
        container_name = self.container_text_box.text().strip()

        if not container_name:
            self.log_and_report_docker_error("Enter a Docker container name.")
            return

        try:
            command = generate_docker_command(action, container_name)
        except RuntimeError as e:
            self.log_and_report_docker_error(str(e))
            return

        self.log_docker_action(action, container_name)

        self.docker_thread = DockerWorkerThread(command, action)
        self.docker_thread.success.connect(self._on_docker_success)
        self.docker_thread.error.connect(self._on_docker_error)

        if (
            action.command_type == Docker_Command_Type.START_VISUAL
            or action.visualizer_mode
        ):
            self.docker_thread.success.connect(lambda _: self.start_visualizer_tunnel())

        self.docker_thread.started.connect(lambda: self.enable_software_controls(False))
        self.docker_thread.finished.connect(lambda: self.enable_software_controls(True))

        self.docker_thread.start()

    def start_visualizer_tunnel(self):
        """Forward the Pi's Dash visualizer port to this machine so it can be
        viewed at http://localhost:8050, then open it in the browser."""
        existing = getattr(self, "visualizer_thread", None)
        if existing is not None and existing.isRunning():
            msg = "[VISUALIZER] Tunnel already running at http://localhost:8050"
            self.append_docker_log(msg)
            return

        self.visualizer_thread = VisualizerTunnelThread()
        self.visualizer_thread.status.connect(
            lambda msg: self._log_visualizer_message(msg)
        )
        self.visualizer_thread.error.connect(
            lambda msg: self._log_visualizer_message(msg, is_error=True)
        )
        self.visualizer_thread.tunnel_ready.connect(self._on_visualizer_ready)
        self.visualizer_thread.start()

    def _log_visualizer_message(self, message: str, is_error: bool = False) -> None:
        prefix = "[VISUALIZER][ERROR]" if is_error else "[VISUALIZER]"
        full_message = f"{prefix} {message}"
        self.append_docker_log(full_message)

    def _on_visualizer_ready(self, port: int):
        url = f"http://localhost:{port}"
        message = f"[VISUALIZER] Tunnel ready - opening {url}"
        self.append_docker_log(message)
        webbrowser.open(url)

    def _on_docker_success(self, action):
        container_name = self.container_text_box.text().strip()
        QMessageBox.information(
            self,
            "Success",
            f"Successfully {action.name.lower()} container:\n{container_name}",
        )
        self.append_docker_log(
            f"[INFO] Successfully {action.name}ed container: {container_name}"
        )

    def _on_docker_error(self, message: str):
        self.log_and_report_docker_error(message)

    def enable_software_controls(self, enabled: bool):
        for button in self.software_control_buttons:
            button.setEnabled(enabled)

    def call_software_emergency_kill(self):
        try:
            result = kill_software()
        except RuntimeError as e:
            self.log_and_report_docker_error(str(e))
            return

        self.append_docker_log(f"[INFO] {result}")

    def change_SSH_profile(self):
        profile = self.SSH_dropdown.currentText()
        self.request_restart(profile)
