# Style for emergency buttons (power controls)
red_button = """
        QPushButton {
            background-color: red;
            color: white;
            border: none;
            padding: 3px 6px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover:enabled {
            background-color: yellow;
            color: black;
        }
        QPushButton:disabled {
            background-color: yellow;
            color: black;
        }
    """

instructions_lable = """
        QLabel {
            color: blue;
            font-size: 11px;
            font-weight: bold;
            padding: 4px;
            background-color: #e6f3ff;
            border: 2px solid #4d94ff;
            border-radius: 3px;
            margin: 2px;
        }
"""

command_button = """
        QPushButton {
            background-color: #4d94ff;
            color: white;
            border: none;
            padding: 2px 4px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #0066cc;
        }
        QPushButton:pressed {
            background-color: #003d7a;
        }
"""
