import sys
import os
from PyQt6.QtWidgets import QApplication

from src.frontend import TranscriptionSignals, MainWindow
from src.audio_recorder import AudioRecorder
from src.transcriber import Transcriber, WHISPER_SAMPLERATE

def main():
    app = QApplication(sys.argv)
    signals = TranscriptionSignals()
    
    # Create audio recorder first to detect devices
    recorder = AudioRecorder(None, None)
    
    mic_transcriber = Transcriber(signals.mic_transcription_ready)
    mix_transcriber = Transcriber(signals.mix_transcription_ready, 
                                input_samplerate=recorder.current_mix['samplerate'] if recorder.current_mix else None)

    recorder.input_transcriber = mic_transcriber
    recorder.mix_transcriber = mix_transcriber
    
    window = MainWindow(recorder, signals)
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()