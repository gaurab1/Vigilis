from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                            QPushButton, QComboBox, QHBoxLayout, QGroupBox, 
                            QTextEdit, QFrame, QLineEdit, QDialog)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon
from datetime import datetime
import os
from src.styles import *
import json
from twilio.rest import Client

from dotenv import load_dotenv
load_dotenv()

class StyleFrame(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(QFrameStyle)

class TranscriptionSignals(QObject):
    mic_transcription_ready = pyqtSignal(str)
    mix_transcription_ready = pyqtSignal(str)
    call_status_changed = pyqtSignal(str)
    incoming_call = pyqtSignal(str, str, str)
    

class IncomingCallDialog(QDialog):
    def __init__(self, caller_number, caller_state, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Incoming Call")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        
        # Call information
        info_label = QLabel(f"Incoming call from:\n{caller_number}\nState: {caller_state}")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        accept_button = QPushButton("Accept")
        accept_button.setStyleSheet("background-color: green; color: white")
        accept_button.clicked.connect(self.accept)
        button_layout.addWidget(accept_button)
        
        reject_button = QPushButton("Reject")
        reject_button.setStyleSheet("background-color: red; color: white")
        reject_button.clicked.connect(self.reject)
        button_layout.addWidget(reject_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self, audio_recorder, signals):
        super().__init__()
        self.audio_recorder = audio_recorder
        self.signals = signals
        self.status_text = ["No active call", "", "Ready to record"]
        self.signals.mic_transcription_ready.connect(self.update_mic_transcript)
        self.signals.mix_transcription_ready.connect(self.update_mix_transcript)
        self.signals.call_status_changed.connect(self.update_call_status)
        self.signals.incoming_call.connect(self.handle_incoming_call)
        self.last_prefix = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Call Recorder")
        self.setGeometry(100, 100, 1000, 800)
        self.setStyleSheet(UIStyle)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        self.setup_icon()
        self.setup_header(main_layout)
        self.setup_call_controls(main_layout)
        self.setup_controls(main_layout)
        self.setup_transcription(main_layout)
        
        # Timer for updating recording duration
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_duration)
        self.recording_start_time = None
    
    def handle_incoming_call(self, caller_number=None, caller_state=None, call_sid=None):
        """Handle an incoming phone call by showing a modal dialog"""
        self.pending_call_sid = call_sid
        
        # Show incoming call dialog
        dialog = IncomingCallDialog(caller_number, caller_state, self)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Call was accepted
            self.status_text[0] = f"Call in progress - From: {caller_number}"
            self.status_text[1] = f"State: {caller_state}"
            self.status_text[2] = "Ready to record"
            self.update_status_label()
            
            # Update UI state
            self.call_button.setEnabled(False)
            self.update_end_call_button(True)
            
            # Accept the call
            client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
            call = client.calls(self.pending_call_sid).update(
                url=f"{os.getenv('NGROK_URL')}/accept"
            )
        else:
            # Call was rejected
            client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
            call = client.calls(self.pending_call_sid).update(status="completed")
            
        # Clear the pending call
        delattr(self, 'pending_call_sid')

    def start_recording_from_call(self):
        """Start recording when a call is connected"""
        if not self.audio_recorder.is_recording:
            self.recording_start_time = datetime.now()
            self.record_button.setText("Recording (In Call)")
            self.record_button.setStyleSheet("background-color: red")
            self.status_text[2] = "Recording... 00:00"
            self.update_status_label()
            self.audio_recorder.start_recording()
    
    def update_call_status(self, status):
        if status == "start":
            self.timer.start(1000)  # Update every second
            self.transcript_area.clear()
        elif status == "stop":
            self.timer.stop()
            self.stop_recording()

    def setup_icon(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

            if os.name == 'nt':  # Windows OS special case to handle app icon
                import ctypes
                myappid = 'mycompany.callrecorder.app.1'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    def setup_header(self, layout):
        header_label = QLabel("Call Recording & Transcription")
        header_label.setStyleSheet(HeaderStyle)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

    def setup_call_controls(self, layout):
        call_controls = StyleFrame()
        call_controls_layout = QHBoxLayout()
        call_controls.setLayout(call_controls_layout)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Enter phone number (e.g. +1234567890)")
        self.phone_input.setMinimumWidth(200)
        call_controls_layout.addWidget(self.phone_input)
        
        self.call_button = QPushButton("Call")
        self.call_button.clicked.connect(self.make_call)
        call_controls_layout.addWidget(self.call_button)
        
        self.end_call_button = QPushButton("End Call")
        self.end_call_button.clicked.connect(self.end_call)
        self.update_end_call_button(False)
        call_controls_layout.addWidget(self.end_call_button)
        
        layout.addWidget(call_controls)

    def setup_controls(self, layout):
        controls_frame = StyleFrame()
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setSpacing(20)
        
        self.status_label = QLabel()
        self.update_status_label()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(StatusStyle)
        controls_layout.addWidget(self.status_label)

        self.setup_buttons(controls_layout)
        
        layout.addWidget(controls_frame)

    def setup_buttons(self, layout):
        button_layout = QHBoxLayout()
        
        self.record_button = QPushButton("Start Recording")
        self.record_button.setStyleSheet("")
        self.record_button.clicked.connect(self.toggle_recording)
        button_layout.addWidget(self.record_button)
        
        layout.addLayout(button_layout)

    def setup_transcription(self, layout):
        transcript_frame = StyleFrame()
        transcript_layout = QVBoxLayout(transcript_frame)
        
        transcript_label = QLabel("Live Transcription")
        transcript_label.setStyleSheet(TranscriptLabelStyle)
        transcript_layout.addWidget(transcript_label)
        
        self.transcript_area = QTextEdit()
        self.transcript_area.setReadOnly(True)
        self.transcript_area.setPlaceholderText("Transcription will appear here in real-time...")
        self.transcript_area.setAcceptRichText(True)
        self.transcript_area.setMinimumHeight(400)  
        self.transcript_area.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | 
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.transcript_area.setStyleSheet(TranscriptAreaStyle)
        transcript_layout.addWidget(self.transcript_area)
        layout.addWidget(transcript_frame)

    def toggle_recording(self):
        if not self.audio_recorder.is_recording:
            self.audio_recorder.start_recording()
            self.recording_start_time = datetime.now()
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet("background-color: red")
            self.timer.start(1000)  # Update every second
            self.status_text[2] = "Recording... 00:00"
            self.update_status_label()
            # self.status_label.setText("\n".join(self.status_text))
        else:
            self.stop_recording()

    def stop_recording(self):
        if self.audio_recorder.is_recording:
            transcript = self.transcript_area.toPlainText()
            message = self.audio_recorder.stop_recording(transcript)
            self.status_label.setText(message)
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet("")
            self.timer.stop()
            self.recording_start_time = None
            self.status_text[0] = "No active call"
            self.status_text[1] = ""
            self.status_text[2] = "Ready to record"
            self.update_status_label()
            self.update_end_call_button(False)

    def update_mic_transcript(self, text):
        if text.strip():
            self._update_transcript_area("Input", text.strip())

    def update_mix_transcript(self, text):
        if text.strip():
            self._update_transcript_area("Output", text.strip())
        
    def _update_transcript_area(self, prefix, content):
        cursor = self.transcript_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        # Get current text and determine if we need a new line
        current_text = self.transcript_area.toPlainText().strip()
        
        if current_text:
            if prefix == self.last_prefix:
                cursor.insertHtml(f" {content}")
            else:
                cursor.insertHtml(f"<br><b>{prefix}</b>: {content}")
        else:
            cursor.insertHtml(f"<b>{prefix}</b>: {content}")
        
        self.last_prefix = prefix
        
        # Update scroll position
        self.transcript_area.setTextCursor(cursor)
        self.transcript_area.verticalScrollBar().setValue(
            self.transcript_area.verticalScrollBar().maximum()
        )

    def update_end_call_button(self, enabled):
        """Update end call button style based on enabled state"""
        if enabled:
            self.end_call_button.setEnabled(True)
            self.end_call_button.setStyleSheet("background-color: red; color: white")
        else:
            self.end_call_button.setEnabled(False)
            self.end_call_button.setStyleSheet("background-color: gray; color: white")

    def update_duration(self):
        """
        Update the status label with the current duration of the recording
        """
        if self.recording_start_time:
            duration = datetime.now() - self.recording_start_time
            seconds = duration.total_seconds()
            minutes = int(seconds // 60)
            seconds = int(seconds % 60)
            self.status_text[2] = f"Recording... {minutes:02d}:{seconds:02d}"
            self.update_status_label()

    def make_call(self):
        """Initiate an outbound call"""
        phone_number = self.phone_input.text().strip()
        if not phone_number:
            print("Please enter a phone number")
            return
            
        call_sid = make_outbound_call(phone_number)
        
        self.audio_recorder.call_sid = call_sid
        self.update_end_call_button(True)
        self.call_button.setEnabled(False)
        self.transcript_area.clear()

    def end_call(self):
        """End the current call"""
        if self.audio_recorder and self.audio_recorder.ws:
            # Close the WebSocket connection
            close_message = {
                "event": "stop",
                "streamSid": self.audio_recorder.stream_sid
            }
            self.audio_recorder.ws.send(json.dumps(close_message))

            # Terminate the call on the server
            self.audio_recorder.ws.close()
            self.audio_recorder.stop_call()
            self.stop_recording()

    def update_status_label(self):
        html_status = [f"<b>{self.status_text[0]}</b>", 
                      self.status_text[1],
                      f"<i>{self.status_text[2]}</i>"]
        self.status_label.setText("<br>".join(html_status))

def make_outbound_call(to_number):
    """Make an outbound call using Twilio API
    
    Args:
        to_number (str): The phone number to call in E.164 format (e.g. +1234567890)
    
    Returns:
        str: The call SID if successful, None if failed
    """
    client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
        
    # Get the ngrok URL for the TwiML endpoint
    ngrok_url = os.getenv('NGROK_URL')
            
    call = client.calls.create(
        url=f"{ngrok_url}/twiml",
        to=to_number,
        from_=os.getenv('TWILIO_PHONE_NUMBER')
    )
    print(f"Started outbound call: {call.sid}")
    return call.sid