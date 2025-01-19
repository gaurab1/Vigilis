from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                            QPushButton, QComboBox, QHBoxLayout, QGroupBox, 
                            QTextEdit, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from src.constants import COLORS
from datetime import datetime

class StyleFrame(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border: 1px solid {COLORS['secondary']};
            }}
        """)

class TranscriptionSignals(QObject):
    transcription_ready = pyqtSignal(str)

class MainWindow(QMainWindow):
    def __init__(self, audio_recorder, signals):
        super().__init__()
        self.audio_recorder = audio_recorder
        self.signals = signals
        self.signals.transcription_ready.connect(self.update_transcript)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Call Recorder")
        self.setGeometry(100, 100, 1000, 800)
        self.apply_stylesheet()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        self.setup_header(main_layout)
        self.setup_device_section(main_layout)
        self.setup_controls(main_layout)
        self.setup_transcription(main_layout)
        
        # Timer for updating recording duration
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_duration)
        self.recording_start_time = None
        
    def apply_stylesheet(self):
        self.setStyleSheet(f"""
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
        """)

    def setup_header(self, layout):
        header_label = QLabel("Voice Recording & Transcription")
        header_label.setStyleSheet(f"""
            font-size: 24px;
            color: {COLORS['primary']};
            font-weight: bold;
            padding: 10px;
        """)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

    def setup_device_section(self, layout):
        device_frame = StyleFrame()
        device_layout = QVBoxLayout(device_frame)
        
        mic_group = QGroupBox("Audio Input Selection")
        mic_layout = QVBoxLayout()
        mic_layout.setSpacing(10)
        
        self.mic_combo = QComboBox()
        for device in self.audio_recorder.mic_devices:
            self.mic_combo.addItem(device['name'])
        self.mic_combo.currentIndexChanged.connect(self.audio_recorder.update_mic)
        mic_layout.addWidget(self.mic_combo)
        mic_group.setLayout(mic_layout)
        device_layout.addWidget(mic_group)
        layout.addWidget(device_frame)

    def setup_controls(self, layout):
        controls_frame = StyleFrame()
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setSpacing(20)
        
        self.status_label = QLabel("Ready to record")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            font-size: 16px;
            color: {COLORS['text']};
            font-weight: bold;
        """)
        
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setMinimumWidth(150)
        
        controls_layout.addWidget(self.status_label)
        controls_layout.addWidget(self.record_button)
        layout.addWidget(controls_frame)

    def setup_transcription(self, layout):
        transcript_frame = StyleFrame()
        transcript_layout = QVBoxLayout(transcript_frame)
        
        transcript_label = QLabel("Live Transcription")
        transcript_label.setStyleSheet(f"""
            font-size: 16px;
            color: {COLORS['primary']};
            font-weight: bold;
        """)
        transcript_layout.addWidget(transcript_label)
        
        self.transcript_area = QTextEdit()
        self.transcript_area.setReadOnly(True)
        self.transcript_area.setPlaceholderText("Transcription will appear here in real-time...")
        self.transcript_area.setMinimumHeight(300)
        transcript_layout.addWidget(self.transcript_area)
        layout.addWidget(transcript_frame)

    def toggle_recording(self):
        if not self.audio_recorder.is_recording:
            self.audio_recorder.start_recording()
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet(f"""
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
            """)
        else:
            self.audio_recorder.stop_recording()
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet("")

    def update_transcript(self, text):
        cursor = self.transcript_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text + " ")  # Add a space after each segment
        self.transcript_area.setTextCursor(cursor)
        self.transcript_area.verticalScrollBar().setValue(
            self.transcript_area.verticalScrollBar().maximum()
        )

    def update_duration(self):
        if self.recording_start_time:
            duration = datetime.now() - self.recording_start_time
            seconds = duration.total_seconds()
            minutes = int(seconds // 60)
            seconds = int(seconds % 60)
            self.status_label.setText(f"Recording... {minutes:02d}:{seconds:02d}")
