import sys
import sounddevice as sd
import numpy as np
import wave
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                            QVBoxLayout, QWidget, QLabel, QFileDialog, 
                            QComboBox, QHBoxLayout, QGroupBox)
from PyQt6.QtCore import Qt, QTimer

class AudioRecorderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Call Recorder")
        self.setGeometry(100, 100, 500, 400)
        
        # Check for available audio devices
        try:
            devices = sd.query_devices()
            print("\nAvailable Audio Devices:")
            for idx, device in enumerate(devices):
                print(f"\nDevice {idx}: {device['name']}")
                print(f"  Input channels: {device['max_input_channels']}")
                print(f"  Output channels: {device['max_output_channels']}")
                print(f"  Default samplerate: {device['default_samplerate']}")
            
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
            
            print(f"\nDefault microphone: {self.current_mic['name']}")
            if self.current_mix:
                print(f"Stereo Mix device: {self.current_mix['name']}")
            else:
                print("No Stereo Mix device found - system audio won't be recorded")
            
        except Exception as e:
            self.current_mic = None
            self.current_mix = None
            print(f"Audio device error: {e}")
        
        # Recording settings
        self.is_recording = False
        self.mic_frames = []
        self.mix_frames = []
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add device selection
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
        
        # Add widgets to layout
        layout.addWidget(self.status_label)
        layout.addWidget(self.record_button)
        
        # Timer for updating recording duration
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_duration)
        self.recording_start_time = None
        
    def update_mic(self, index):
        self.current_mic = self.mic_devices[index]
        print(f"\nSelected microphone: {self.current_mic['name']}")
    
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
        self.record_button.setText("Stop Recording")
        self.recording_start_time = datetime.now()
        self.timer.start(1000)  # Update every second
        
        def mic_callback(indata, frames, time, status):
            if status:
                print(f"Mic Status: {status}")
            self.mic_frames.append(indata.copy())

        def mix_callback(indata, frames, time, status):
            if status:
                print(f"Mix Status: {status}")
            self.mix_frames.append(indata.copy())
        
        try:
            print("\nStarting recording with devices:")
            print(f"Microphone: {self.current_mic['name']} (ID: {self.current_mic['id']})")
            if self.current_mix:
                print(f"Stereo Mix: {self.current_mix['name']} (ID: {self.current_mix['id']})")
            
            # Start microphone input stream
            self.mic_stream = sd.InputStream(
                device=self.current_mic['id'],
                channels=1,  # Mono recording
                samplerate=int(self.current_mic['samplerate']),
                callback=mic_callback
            )
            
            # Start stereo mix stream if available
            if self.current_mix:
                self.mix_stream = sd.InputStream(
                    device=self.current_mix['id'],
                    channels=1,  # Mono recording
                    samplerate=int(self.current_mix['samplerate']),
                    callback=mix_callback
                )
            
            self.mic_stream.start()
            if self.current_mix:
                self.mix_stream.start()
            
            self.status_label.setText("Recording...")
        except Exception as e:
            self.status_label.setText(f"Error starting recording: {str(e)}")
            print(f"\nError details: {e}")
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
            
            # Save microphone audio
            self.save_audio(self.mic_frames, f"audios/mic_recording_{timestamp}.wav")
            
            # If we have system audio, save combined
            if self.mix_frames:
                self.save_combined_audio(self.mic_frames, self.mix_frames, f"audios/combined_recording_{timestamp}.wav")
            
            self.status_label.setText("Recording saved!")
        except Exception as e:
            self.status_label.setText(f"Error saving recording: {str(e)}")
    
    def save_audio(self, frames, filename):
        if not frames:
            return
            
        try:
            audio_data = np.concatenate(frames, axis=0)
            
            # Normalize to prevent clipping
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data / max_val
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(int(self.current_mic['samplerate']))
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
            max_val = np.max(np.abs(combined_data))
            if max_val > 0:
                combined_data = combined_data / max_val
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(int(self.current_mic['samplerate']))
                wf.writeframes((combined_data * 32767).astype(np.int16))
        except Exception as e:
            print(f"Error saving {filename}: {str(e)}")
    
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
