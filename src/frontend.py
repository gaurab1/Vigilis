from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                            QPushButton, QComboBox, QHBoxLayout, QGroupBox, 
                            QTextEdit, QFrame, QLineEdit, QDialog, QApplication, QSizePolicy,
                            QStackedWidget, QListWidget, QListWidgetItem, QSplitter, QMessageBox, QScrollArea,
                            QGridLayout)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize
from PyQt6.QtGui import QIcon, QFont, QTextCursor, QTextBlockFormat, QTextCharFormat, QColor, QTextFormat
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
    incoming_msg = pyqtSignal(str, str)
    

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

class MenuScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 10, 30, 30)  # Reduced top margin
        
        # Title
        title_label = QLabel("Fraud-Protected Communication App")
        title_label.setStyleSheet(HeaderStyle)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        

        
        # Add some space
        spacer = QWidget()
        spacer.setFixedHeight(20)
        layout.addWidget(spacer)
        
        # Button styles
        button_style = """
            QPushButton {
                border-radius: 10px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """
        
        message_button_style = """
            QPushButton {
                border-radius: 10px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """
        
        # Buttons container
        buttons_frame = StyleFrame()
        buttons_layout = QVBoxLayout(buttons_frame)
        buttons_layout.setSpacing(20)
        
        # Call platform button
        self.call_platform_button = QPushButton("Secure Call Platform")
        self.call_platform_button.setMinimumHeight(70)  # Slightly reduced height
        self.call_platform_button.setFont(QFont("Arial", 14))
        self.call_platform_button.setStyleSheet(button_style + "background-color: #4CAF50; color: white;")
        buttons_layout.addWidget(self.call_platform_button)
        
        # Messaging platform button
        self.message_button = QPushButton("Secure Messaging Platform")
        self.message_button.setMinimumHeight(70)  # Slightly reduced height
        self.message_button.setFont(QFont("Arial", 14))
        self.message_button.setStyleSheet(message_button_style + "background-color: #2196F3; color: white;")
        buttons_layout.addWidget(self.message_button)
        
        layout.addWidget(buttons_frame)
        
        # Add some spacing
        layout.addStretch()

class MessageScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_phone_numbers()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header with back button - more compact
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)  # Add bottom margin
        
        # Back button as an icon
        self.back_button = QPushButton()
        self.back_button.setIcon(QIcon.fromTheme("go-home", QIcon(":/icons/edit-undo.png")))
        self.back_button.setIconSize(QSize(24, 24))
        self.back_button.setFixedSize(36, 36)
        self.back_button.setStyleSheet("background-color: transparent;")
        self.back_button.setToolTip("Back to Menu")
        
        # Create a container for the back button
        back_container = QHBoxLayout()
        back_container.addWidget(self.back_button)
        back_container.addStretch()
        
        # Title in its own layout to ensure it's centered in the available space
        title_container = QHBoxLayout()
        header_label = QLabel("Secure Messaging Platform")
        header_label.setStyleSheet(HeaderStyle)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_container.addWidget(header_label)
        
        # Main header layout with proper proportions
        header_layout.addLayout(back_container, 1)  # Left side with back button
        header_layout.addLayout(title_container, 5)  # Center with title (more space)
        header_layout.addStretch(1)  # Right side empty space to balance
        
        layout.addLayout(header_layout)
        
        # Main content with phone list and chat
        content_layout = QHBoxLayout()
        
        # Phone number list
        self.phone_list = QListWidget()
        self.phone_list.setFixedWidth(200)
        self.phone_list.currentItemChanged.connect(self.load_chat_history)
        self.phone_list.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 5px;
                border: 1px solid #ddd;
                font-size: 14px;
            }
            QListWidget::item {
                height: 40px;
                border-bottom: 1px solid #e1e1e1;
                padding: 5px 10px;
                margin: 2px 0px;
                border-radius: 5px;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
                color: #1976D2;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
        """)
        content_layout.addWidget(self.phone_list)
        
        # Chat panel
        chat_panel = QWidget()
        chat_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        chat_layout = QVBoxLayout(chat_panel)
        
        # Replace QTextEdit with QScrollArea containing a QWidget with a QVBoxLayout
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(15)  # Space between messages
        self.chat_layout.setContentsMargins(20, 20, 20, 20)  # Margins around chat content
        
        self.chat_scroll.setWidget(self.chat_content)
        chat_layout.addWidget(self.chat_scroll)
        
        # Message input
        input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        
        send_button = QPushButton("Send")
        send_button.setFixedWidth(100)
        send_button.clicked.connect(self.send_message)
        input_layout.addWidget(send_button)
        
        chat_layout.addLayout(input_layout)
        content_layout.addWidget(chat_panel)
        
        layout.addLayout(content_layout)
        
    def create_message_label(self, message, is_output=False):
        label = QLabel(message)
        label.setWordWrap(True)
        label.setMaximumWidth(int(self.chat_scroll.width() * 0.8))
        
        if is_output:
            label.setStyleSheet("""
                background-color: #3498DB;
                color: white;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
                text-align: justify;
            """)
        else:
            label.setStyleSheet("""
                background-color: #27AE60;
                color: black;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
                text-align: justify;
            """)
        
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        
        if is_output:
            # Right-aligned message (output)
            grid.addWidget(label, 0, 1)  # Add to right column
            grid.setColumnStretch(0, 1)   # Make left column stretch
            grid.setColumnStretch(1, 0)   # Don't stretch the message column
        else:
            # Left-aligned message (input)
            grid.addWidget(label, 0, 0)   # Add to left column
            grid.setColumnStretch(0, 0)   # Don't stretch the message column
            grid.setColumnStretch(1, 1)   # Make right column stretch
        
        return container

    def load_phone_numbers(self):
        """Load phone numbers from the output directory"""
        current_numbers = set()
        for i in range(self.phone_list.count()):
            current_numbers.add(self.phone_list.item(i).text())
        
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
        
        # Look for .txt files that match phone number pattern
        for file in os.listdir(output_dir):
            if file.endswith(".txt") and file.startswith("+"):
                phone_number = file.replace(".txt", "")
                # Only add if not already in the list
                if phone_number not in current_numbers:
                    item = QListWidgetItem(phone_number)
                    self.phone_list.addItem(item)
    
    def load_chat_history(self, current_item, previous_item):
        """Load chat history for the selected phone number"""
        if not current_item:
            return
        
        phone_number = current_item.text()
        
        # Clear previous chat content
        # Delete all widgets from the layout
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Load chat history from file
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
        file_path = os.path.join(output_dir, f"{phone_number}.txt")
        with open(file_path, "r") as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if line.startswith("Output:"):
                # Message from us
                message = line[len("Output:"):].strip()
                message_widget = self.create_message_label(message, is_output=True)
                self.chat_layout.addWidget(message_widget)
                
            elif line.startswith("Input:"):
                # Message from them
                message = line[len("Input:"):].strip()
                message_widget = self.create_message_label(message, is_output=False)
                self.chat_layout.addWidget(message_widget)
        
        # Add a spacer at the bottom to push messages up
        self.chat_layout.addStretch()
        
        # Scroll to the bottom
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def send_message(self):
        """Send a new message"""
        message = self.message_input.text().strip()
        if not message:
            return
            
        current_item = self.phone_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Contact Selected", "Please select a contact to send a message to.")
            return
            
        phone_number = current_item.text()
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
        file_path = os.path.join(output_dir, f"{phone_number}.txt")
        
        try:
            # Append the new message to the file
            with open(file_path, "a") as f:
                f.write(f"\nOutput: {message}")
                
            self.message_input.clear()
            
            # Reload the chat history to show the new message
            self.load_chat_history(current_item, None)
            
            # TODO: Implement actual SMS sending functionality
            # This would connect to the Twilio API to send the message
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send message: {str(e)}")

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
        self.signals.incoming_msg.connect(self.handle_incoming_msg)
        self.last_prefix = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Secure Communication App")
        self.setGeometry(100, 100, 1000, 700)  # Reduced height from 800 to 700
        self.setStyleSheet(UIStyle)
        
        # Setup icon
        self.setup_icon()
        
        # Create stacked widget for multiple screens
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Create menu screen
        self.menu_screen = MenuScreen()
        self.stacked_widget.addWidget(self.menu_screen)
        
        # Create call screen
        self.call_screen = QWidget()
        self.setup_call_screen()
        self.stacked_widget.addWidget(self.call_screen)
        
        # Create message screen
        self.message_screen = MessageScreen()
        self.stacked_widget.addWidget(self.message_screen)
        
        # Connect buttons
        self.menu_screen.call_platform_button.clicked.connect(self.show_call_screen)
        self.menu_screen.message_button.clicked.connect(self.show_message_screen)
        self.message_screen.back_button.clicked.connect(self.show_menu_screen)
        
        # Start with menu screen
        self.stacked_widget.setCurrentIndex(0)
        
        # Timer for updating recording duration
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_duration)
        self.recording_start_time = None
    
    def show_menu_screen(self):
        self.stacked_widget.setCurrentIndex(0)
        
    def show_call_screen(self):
        self.stacked_widget.setCurrentIndex(1)
        
    def show_message_screen(self):
        self.stacked_widget.setCurrentIndex(2)
    
    def setup_call_screen(self):
        call_layout = QVBoxLayout(self.call_screen)
        call_layout.setSpacing(20)
        call_layout.setContentsMargins(30, 10, 30, 30)  # Reduced top margin
        
        # Header with back button - more compact
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)  # Add bottom margin
        
        # Back button as an icon
        back_button = QPushButton()
        back_button.setIcon(QIcon.fromTheme("go-home", QIcon(":/icons/edit-undo.png")))
        back_button.setIconSize(QSize(24, 24))
        back_button.setFixedSize(36, 36)
        back_button.setStyleSheet("background-color: transparent;")
        back_button.setToolTip("Back to Menu")
        back_button.clicked.connect(self.show_menu_screen)
        
        # Create a container for the back button
        back_container = QHBoxLayout()
        back_container.addWidget(back_button)
        back_container.addStretch()
        
        # Title in its own layout to ensure it's centered in the available space
        title_container = QHBoxLayout()
        header_label = QLabel("Call Recording & Transcription")
        header_label.setStyleSheet(HeaderStyle)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_container.addWidget(header_label)
        
        # Main header layout with proper proportions
        header_layout.addLayout(back_container, 1)  # Left side with back button
        header_layout.addLayout(title_container, 5)  # Center with title (more space)
        header_layout.addStretch(1)  # Right side empty space to balance
        
        call_layout.addLayout(header_layout)
        
        # Call controls
        self.setup_call_controls(call_layout)
        self.setup_controls(call_layout)
        self.setup_transcription(call_layout)
    
    def handle_incoming_msg(self, caller_number, message):
        if self.stacked_widget.currentIndex() == 2:
            self.message_screen.load_phone_numbers()
            print(self.message_screen.phone_list.currentItem())
            if self.message_screen.phone_list.currentItem() and self.message_screen.phone_list.currentItem().text() == caller_number:
                self.message_screen.load_chat_history(self.message_screen.phone_list.currentItem(), None)

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
        self.transcript_area.setMinimumHeight(300)
        self.transcript_area.setStyleSheet("""
            QTextEdit {
                border: none;
                background-color: white;
                padding: 10px;
                border-radius: 5px;
            }
        """)
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