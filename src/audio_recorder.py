import sounddevice as sd
sd.default.latency = 'low'
import numpy as np
import wave
import os
from datetime import datetime
import queue
import base64
import audioop
import json
from src.transcriber import WHISPER_SAMPLERATE, TWILIO_SAMPLERATE, Transcriber

class AudioRecorder:
    def __init__(self, input_transcriber: Transcriber, mix_transcriber: Transcriber):
        self.input_transcriber = input_transcriber
        self.mix_transcriber = mix_transcriber
        self.is_recording = False
        self.samplerate = WHISPER_SAMPLERATE
        self.mic_frames = []
        self.mix_frames = []
        self.ws = None
        self.stream_sid = None
        
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
            self.input_transcriber.queue_audio(indata)

            pcm_data = indata.tobytes()
            mulaw_data = audioop.lin2ulaw(pcm_data, 2)  # Convert 16-bit PCM to 8-bit mu-law
            
            # Encode as base64
            b64_data = base64.b64encode(mulaw_data).decode('utf-8')
            
            # Create media message
            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": b64_data
                }
            }
            
            # Send through websocket
            try:
                self.ws.send(json.dumps(message))
            except Exception as e:
                print(f"Error sending audio: {e}")

        def mix_callback(indata, frames, time, status):
            if status:
                print(f"Mix Status: {status}")
            self.mix_frames.append(indata.copy())
            self.mix_transcriber.queue_audio(indata)

        def _audio_callback_output(outdata, frames, time, status):
            """Callback for audio output"""
            try:
                data = self.audio_queue.get_nowait()
                self.mix_frames.append(data.copy())
                self.mix_transcriber.queue_audio(data)
                if len(data) < len(outdata):
                    outdata[:len(data)] = data
                    outdata[len(data):] = np.zeros((len(outdata) - len(data), 1), dtype=np.int16)
                else:
                    outdata[:] = data[:len(outdata)]
            except queue.Empty:
                outdata[:] = np.zeros((len(outdata), 1), dtype=np.int16)
                   
        # Start microphone input stream
        # self.mic_stream = sd.InputStream(
        #     device=self.current_mic['id'],
        #     channels=1,  # Mono recording
        #     samplerate=self.samplerate,
        #     callback=mic_callback,
        #     blocksize=1024,
        #     latency='low'
        # )
        self.mic_stream = sd.InputStream(
            samplerate=TWILIO_SAMPLERATE,
            channels=1,
            dtype=np.int16,
            callback=mic_callback,
            blocksize=160,  # 20ms chunks at 8kHz
            latency='low'
        )
        
        # Audio playback setup
        self.audio_queue = queue.Queue()
        self.mix_stream = sd.OutputStream(
            samplerate=TWILIO_SAMPLERATE,
            channels=1,
            dtype=np.int16,
            callback=_audio_callback_output,
            latency='low'
        )

        # Start stereo mix stream if available
        # if self.current_mix:
        #     mix_blocksize = int(1024 * (self.current_mix['samplerate'] / WHISPER_SAMPLERATE))
        #     self.mix_stream = sd.InputStream(
        #         device=self.current_mix['id'],
        #         channels=1,  # Mono recording
        #         samplerate=self.current_mix['samplerate'],
        #         callback=mix_callback,
        #         blocksize=mix_blocksize,
        #         latency='low'
        #     )
        
        self.mic_stream.start()
        if self.current_mix:
            self.mix_stream.start()
    
    def start_call(self, stream_sid, ws):
        print(f"Starting call with stream SID: {stream_sid}")
        self.stream_sid = stream_sid
        self.ws = ws

    def stop_call(self):
        self.stream_sid = None
        self.ws = None

    def process_audio(self, audio_data):
        pcm_data = audioop.ulaw2lin(audio_data.tobytes(), 2)
        pcm_array = np.frombuffer(pcm_data, dtype=np.int16)
        pcm_array = pcm_array.reshape(-1, 1)
        self.audio_queue.put(pcm_array)

    def stop_recording(self, transcript_text=None):
        if not self.is_recording:
            return
            
        self.is_recording = False
        
        self.mic_stream.stop()
        self.mic_stream.close()

        if hasattr(self, 'mix_stream'):
            self.mix_stream.stop()
            self.mix_stream.close()
        
        # Save recordings
        timestamp = datetime.now().strftime("%Y-%m-%d@%H-%M")
        directory = f"outputs/{timestamp}"
        os.makedirs(directory, exist_ok=True)

        # Save audio files
        self.save_audio(self.mic_frames, f"{directory}/mic_recording.wav")
        if self.mix_frames:
            self.save_audio(self.mix_frames, f"{directory}/output.wav", 
                          samplerate=TWILIO_SAMPLERATE)
        
        if transcript_text:
            with open(f"{directory}/transcript.txt", 'w', encoding='utf-8') as f:
                f.write(transcript_text)
        
        return f"Recording saved to {directory}"
    
    def save_audio(self, frames, filename, samplerate=TWILIO_SAMPLERATE):
        if not frames:
            return
            
        try:
            audio_data = np.concatenate(frames, axis=0)
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(samplerate)
                wf.writeframes((audio_data).astype(np.int16))
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
