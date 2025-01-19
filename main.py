import sys
from PyQt6.QtWidgets import QApplication

from src.constants import *
from src.ui import TranscriptionSignals, MainWindow
from src.audio_recorder import AudioRecorder
from src.transcriber import Transcriber

def main():
    app = QApplication(sys.argv)
    signals = TranscriptionSignals()
    window = MainWindow(AudioRecorder(Transcriber(signals.transcription_ready)), signals)
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()