import sys
import sounddevice as sd
import numpy as np
import wave
import whisper
import time
import queue
import threading
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                            QVBoxLayout, QWidget, QLabel, QFileDialog, 
                            QComboBox, QHBoxLayout, QGroupBox, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject

WHISPER_MODEL = "tiny.en"
WHISPER_SAMPLERATE = 16000

class TranscriptionSignals(QObject):
    transcription_ready = pyqtSignal(str)

class AudioRecorderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Call Recorder")
        self.setGeometry(100, 100, 800, 600)
        
        # Check for available audio devices
        try:
            devices = sd.query_devices()
            
            # Get microphone and stereo mix devices
            self.mic_devices = []
            self.stereo_mix_devices = []
            
            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0:
                    info = {
                        'id': i,
                        'name': d['name'],
                        'channels': d['max_input_channels'],
                        'samplerate': d['default_samplerate']
                    }
                    if 'Stereo Mix' in d['name']:
                        self.stereo_mix_devices.append(info)
                    else:
                        self.mic_devices.append(info)
            
            if not self.mic_devices:
                raise RuntimeError("No microphone devices found")
            
            # Use first microphone device as default
            self.current_mic = self.mic_devices[0]
            self.current_mix = self.stereo_mix_devices[0] if self.stereo_mix_devices else None
            self.samplerate = WHISPER_SAMPLERATE
        except Exception as e:
            self.current_mic = None
            self.current_mix = None
        
        # Recording settings
        self.is_recording = False
        self.mic_frames = []
        self.mix_frames = []
        
        # Initialize Whisper model (using small model for better accuracy)
        self.model = whisper.load_model(WHISPER_MODEL)
        self.audio_queue = queue.Queue()
        self.transcription_buffer = []
        self.signals = TranscriptionSignals()
        self.signals.transcription_ready.connect(self.update_transcript)
        
        # Start transcription thread
        self.should_stop = False
        self.transcription_thread = threading.Thread(target=self.transcription_worker, daemon=True)
        self.transcription_thread.start()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Microphone selection
        mic_group = QGroupBox("Select Microphone")
        mic_layout = QVBoxLayout()
        self.mic_combo = QComboBox()
        for device in self.mic_devices:
            self.mic_combo.addItem(device['name'])
        self.mic_combo.currentIndexChanged.connect(self.update_mic)
        mic_layout.addWidget(self.mic_combo)
        mic_group.setLayout(mic_layout)
        layout.addWidget(mic_group)
        
        # Create UI elements
        self.status_label = QLabel("Ready to record", alignment=Qt.AlignmentFlag.AlignCenter)
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        
        # Add transcription text area
        self.transcript_area = QTextEdit()
        self.transcript_area.setReadOnly(True)
        self.transcript_area.setPlaceholderText("Transcription will appear here...")
        
        # Add widgets to layout
        layout.addWidget(self.status_label)
        layout.addWidget(self.record_button)
        layout.addWidget(self.transcript_area)
        
        # Timer for updating recording duration
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_duration)
        self.recording_start_time = None
        
    def update_mic(self, index):
        self.current_mic = self.mic_devices[index]
    
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        if self.current_mic is None:
            self.status_label.setText("Error: No microphone selected")
            return
            
        self.is_recording = True
        self.mic_frames = []
        self.mix_frames = []
        self.transcript_area.clear()
        self.record_button.setText("Stop Recording")
        self.recording_start_time = datetime.now()
        self.timer.start(1000)  # Update every second
        
        def mic_callback(indata, frames, time, status):
            if status:
                print(f"Mic Status: {status}")
            self.mic_frames.append(indata.copy())
            # Queue audio data for transcription
            self.process_audio_for_transcription(indata)

        def mix_callback(indata, frames, time, status):
            if status:
                print(f"Mix Status: {status}")
            self.mix_frames.append(indata.copy())
        
        try:            
            # Start microphone input stream with larger buffer
            self.mic_stream = sd.InputStream(
                device=self.current_mic['id'],
                channels=1,  # Mono recording
                samplerate=self.samplerate,  # Whisper expects 16kHz
                callback=mic_callback,
                blocksize=1024,  # Smaller block size
                latency='high'   # Use high latency for stability
            )
            
            # Start stereo mix stream if available
            if self.current_mix:
                self.mix_stream = sd.InputStream(
                    device=self.current_mix['id'],
                    channels=1,  # Mono recording
                    samplerate=self.current_mic['samplerate'],
                    callback=mix_callback,
                )
            
            self.mic_stream.start()
            if self.current_mix:
                self.mix_stream.start()
            
            self.status_label.setText("Recording...")
        except Exception as e:
            self.status_label.setText(f"Error starting recording: {str(e)}")
            self.is_recording = False
            self.record_button.setText("Start Recording")
            self.timer.stop()
    
    def stop_recording(self):
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.record_button.setText("Start Recording")
        self.timer.stop()
        
        try:
            self.mic_stream.stop()
            if hasattr(self, 'mix_stream'):
                self.mix_stream.stop()
            self.mic_stream.close()
            if hasattr(self, 'mix_stream'):
                self.mix_stream.close()
            
            # Save recordings
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.save_audio(self.mic_frames, f"audios/mic_recording_{timestamp}.wav")
            if self.mix_frames:
                self.save_audio(self.mix_frames, f"audios/output_{timestamp}.wav", samplerate=self.current_mic['samplerate'])
            
            self.status_label.setText("Recording saved!")
        except Exception as e:
            self.status_label.setText(f"Error saving recording: {str(e)}")
    
    def save_audio(self, frames, filename, samplerate=WHISPER_SAMPLERATE):
        if not frames:
            return
            
        try:
            audio_data = np.concatenate(frames, axis=0)
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(samplerate)
                wf.writeframes((audio_data * 32767).astype(np.int16))
        except Exception as e:
            print(f"Error saving {filename}: {str(e)}")
    
    def save_combined_audio(self, mic_frames, mix_frames, filename):
        if not mic_frames or not mix_frames:
            return
            
        try:
            # Convert both to numpy arrays
            mic_data = np.concatenate(mic_frames, axis=0)
            mix_data = np.concatenate(mix_frames, axis=0)
            
            # Make sure both arrays are the same length
            min_length = min(len(mic_data), len(mix_data))
            mic_data = mic_data[:min_length]
            mix_data = mix_data[:min_length]
            
            # Mix the audio streams
            combined_data = mic_data + mix_data
            
            # Normalize to prevent clipping
            max_val = max(np.max(np.abs(combined_data)), 1e-2)
            if max_val > 0:
                combined_data = combined_data / max_val
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(int(self.current_mic['samplerate']))
                wf.writeframes((combined_data * 32767).astype(np.int16))
        except Exception as e:
            print(f"Error saving {filename}: {str(e)}")
    
    def process_audio_for_transcription(self, audio_data):
        try:
            # Just queue the audio data and return quickly
            self.audio_queue.put(audio_data.copy())
        except Exception as e:
            print(f"Error queuing audio: {e}")

    def transcription_worker(self):
        while not self.should_stop:
            # Collect audio data for 2 seconds
            audio_chunks = []
            timeout_counter = 0
            
            # Collect chunks for 2 seconds worth of audio
            target_samples = int(self.samplerate * 2)  # 2 seconds of audio
            collected_samples = 0
            
            while collected_samples < target_samples and timeout_counter < 20:
                try:
                    chunk = self.audio_queue.get(timeout=0.1)
                    audio_chunks.append(chunk)
                    collected_samples += len(chunk)
                except queue.Empty:
                    timeout_counter += 1
                    continue
            
            if audio_chunks:
                # Combine chunks and convert to the format Whisper expects
                audio_data = np.concatenate(audio_chunks)
                
                # Convert to mono if necessary
                if audio_data.ndim > 1:
                    audio_data = audio_data.mean(axis=1)
                
                # Normalize audio to float32 in range [-1, 1]
                audio_data = audio_data.astype(np.float32)
                if np.max(np.abs(audio_data)) > 0:
                    audio_data = audio_data / np.max(np.abs(audio_data))
                
                try:
                    start = time.time()
                    result = self.model.transcribe(
                        audio_data,
                        language='en',
                        fp16=False
                    )
                    if result["text"].strip():
                        print(f"Transcribed text: {result['text']} in {time.time() - start:.2f} seconds")
                        self.signals.transcription_ready.emit(result["text"])
                except Exception as e:
                    print(f"Transcription failed: {e}")
    
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

def main():
    app = QApplication(sys.argv)
    window = AudioRecorderApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
