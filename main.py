import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from src.frontend import TranscriptionSignals, MainWindow
from src.audio_recorder import AudioRecorder
from src.transcriber import Transcriber

def main():
    app = QApplication(sys.argv)
    
    # Set application icon
    icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'download.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    signals = TranscriptionSignals()
    window = MainWindow(AudioRecorder(Transcriber(signals.transcription_ready)), signals)
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()