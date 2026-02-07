from .elements import *

class CANWindowUIMixin:
    def init_ui(self):   
          
        top_bar_layout = init_top_bar(self)
        checkbox_layout = init_checkbox(self)

        # === Left Panel ===

        self.instructions1_display = QLabel("For Rudder    (+/- 3 degrees): A / S / D  (Left / Center / Right)")
        self.instructions2_display = QLabel("For Trim Tab (+/- 3 degrees): Q / W / E (Left / Center / Right)")

        self.rudder_display = QLabel("Current Set Rudder Angle:  0 degrees")
        self.trimtab_display = QLabel("Current Trim Tab Angle:   0 degrees")

        self.desired_heading_input_group = init_desired_heading_input_group(self)
        self.rudder_input_group = init_rudder_input_group(self)
        self.trim_input_group = init_trim_input_group(self)
        
        self.pid_layout = init_pid_layout(self)
        emergency_controls_layout = init_emergency_controls(self)

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setMinimumWidth(350)

        # Separate terminal output display
        self.terminal_output_display = QTextEdit()
        self.terminal_output_display.setReadOnly(True)

        # SSH Instructions for CAN and system control
        self.ssh_instructions_label = QLabel(
            "SSH Terminal Instructions:\n"
            "1. Open separate terminal/PowerShell\n"
            "2. ssh sailbot@192.168.0.10\n"
            "3. Password: sailbot\n"
            "\nUse buttons below to copy commands:"
        )
        self.ssh_instructions_label.setStyleSheet(styles.instructions_lable)

        # Define commands with labels
        commands = [
            ("SSH Connect", "ssh sailbot@192.168.0.10"),
            ("CAN0 Down", "sudo ip link set can0 down"),
            ("CAN0 Up", "sudo ip link set can0 up type can bitrate 500000 dbitrate 1000000 fd on"),
            ("Check CAN Status", "ip link show can0"),
            ("View System Logs", "dmesg | tail"),
            ("System Info", "uname -a")
        ]
        
        # Create a grid layout for command buttons
        self.commands_grid = init_commands_grid(self, commands)   
         
        input_layout = init_input_layout(self)
        left_layout = init_left_layout(self, top_bar_layout, checkbox_layout, input_layout, emergency_controls_layout)
        
        # === Right Panel ===
        labels_layout = init_labels_layout()
        right_layout = init_right_layout(self)

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
    
    def getGraphObjFromXName(self, name):
        for obj in all_objs:
            if ((obj.graph_obj is not None) and (obj.graph_obj.dropdown_label == name)):
                return obj.graph_obj
            
    def setGraph(self, name, spot, dropdowns):
        '''
        Shows given graph at spot\n
        name = DataObj.graph_obj.dropdown_label\n
        spot = 0, 1, 2 (top, mid, bot)\n
        '''
        newGraphObj = self.getGraphObjFromXName(name) # get graph to put in spot
        if (newGraphObj.dropdown_label == self.visibleGraphObjs[spot].dropdown_label):
            return # do nothing
        if newGraphObj in self.visibleGraphObjs: # if graph to put in spot is already visible
            # don't allow the switch to happen - set dropdown text back to original and print error message
            print("[ERR] Graph is already visible")
            dropdowns[spot].setCurrentText(self.visibleGraphObjs[spot].dropdown_label) # switch text back to original
        else: 
            self.right_graphs_layout.removeWidget(self.visibleGraphObjs[spot].graph) # remove graph currently in spot
            self.visibleGraphObjs[spot].hide()
            self.right_graphs_layout.addWidget(newGraphObj.graph, spot, 0)
            newGraphObj.show()
            self.visibleGraphObjs[spot] = newGraphObj  

    # def setGraph(self, name, spot, dropdowns):
    #     '''
    #     Shows given graph at spot\n
    #     name = DataObj.graph_obj.x_name\n
    #     spot = 0, 1, 2 (top, mid, bot)\n
    #     '''
    #     newGraphObj = self.getGraphObjFromXName(name) # get graph to put in spot
    #     if (newGraphObj.x_name == self.visibleGraphObjs[spot].x_name):
    #         return # do nothing
    #     if newGraphObj in self.visibleGraphObjs: # if graph to put in spot is already visible
    #         # don't allow the switch to happen - set dropdown text back to original and print error message
    #         print("[ERR] Graph is already visible")
    #         dropdowns[spot].setCurrentText(self.visibleGraphObjs[spot].x_name) # switch text back to original
    #     else: 
    #         self.right_graphs_layout.removeWidget(self.visibleGraphObjs[spot].graph) # remove graph currently in spot
    #         self.visibleGraphObjs[spot].hide()
    #         self.right_graphs_layout.addWidget(newGraphObj.graph, spot, 0)
    #         newGraphObj.show()
    #         self.visibleGraphObjs[spot] = newGraphObj  
