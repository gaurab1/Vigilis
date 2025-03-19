# Color scheme
COLORS = {
    'primary': '#2C3E50',    # Dark blue-grey
    'secondary': '#3498DB',  # Bright blue
    'accent': '#E74C3C',     # Red for recording
    'background': '#ECF0F1', # Light grey
    'text': '#2C3E50',       # Dark text
    'success': '#27AE60',    # Green for success messages
    'warning': '#F39C12'     # Orange for warnings
}

UIStyle = f"""
            QMainWindow {{
                background-color: {COLORS['background']};
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                padding: 5px;
            }}
            QPushButton {{
                background-color: {COLORS['secondary']};
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-size: 14px;
                min-width: 120px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary']};
            }}
            QGroupBox {{
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                margin-top: 1em;
            }}
            QComboBox {{
                border: 2px solid {COLORS['secondary']};
                border-radius: 6px;
                padding: 8px;
                min-width: 200px;
                background-color: white;
            }}
            QComboBox:hover {{
                border-color: {COLORS['primary']};
            }}
            QTextEdit {{
                border: 2px solid {COLORS['secondary']};
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                background-color: white;
                selection-background-color: {COLORS['secondary']};
            }}
        """

RecordingButtonStyle = f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    color: white;
                    border: none;
                    padding: 12px 20px;
                    border-radius: 6px;
                    font-size: 14px;
                    min-width: 120px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #C0392B;
                }}
            """

QFrameStyle = f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border: 1px solid {COLORS['secondary']};
            }}
        """

HeaderStyle = f"""
            font-size: 24px;
            color: {COLORS['primary']};
            font-weight: bold;
            padding: 10px;
        """

StatusStyle = f"""
            font-size: 16px;
            color: {COLORS['text']};
        """

TranscriptLabelStyle = f"""
            font-size: 16px;
            color: {COLORS['primary']};
            font-weight: bold;
        """

TranscriptAreaStyle = f"""
            QTextEdit {{
                background-color: white;
                border: 2px solid {COLORS['secondary']};
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                selection-background-color: {COLORS['secondary']};
                selection-color: white;
            }}
        """