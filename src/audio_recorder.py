import sounddevice as sd
import numpy as np
import wave
from datetime import datetime
from src.transcriber import WHISPER_SAMPLERATE, Transcriber

class AudioRecorder:
    def __init__(self, transcriber: Transcriber):
        self.transcriber = transcriber
        self.is_recording = False
        self.samplerate = WHISPER_SAMPLERATE
        self.mic_frames = []
        self.mix_frames = []
        
        # Initialize audio devices
        self.init_audio_devices()
    
    def init_audio_devices(self):
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
            
        except Exception as e:
            print(f"Audio device error: {e}")
            self.current_mic = None
            self.current_mix = None
    
    def update_mic(self, index):
        self.current_mic = self.mic_devices[index]
    
    def start_recording(self):
        if self.current_mic is None:
            raise RuntimeError("No microphone selected")
            
        self.is_recording = True
        self.mic_frames = []
        self.mix_frames = []
        
        def mic_callback(indata, frames, time, status):
            if status:
                print(f"Mic Status: {status}")
            self.mic_frames.append(indata.copy())

            # Queue audio data for transcription
            self.transcriber.queue_audio(indata)

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
            
        except Exception as e:
            self.is_recording = False
            raise RuntimeError(f"Error starting recording: {str(e)}")
    
    def stop_recording(self):
        if not self.is_recording:
            return
            
        self.is_recording = False
        
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
                self.save_audio(self.mix_frames, f"audios/output_{timestamp}.wav", 
                              samplerate=self.current_mic['samplerate'])
            
            return "Recording saved!"
        except Exception as e:
            raise RuntimeError(f"Error saving recording: {str(e)}")
    
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
