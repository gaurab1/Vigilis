import threading
import queue
import numpy as np
import whisper
import time
from scipy import signal

# Model constants and configuration
WHISPER_MODEL = "base.en"
WHISPER_SAMPLERATE = 16000

class Transcriber:
    def __init__(self, transcription_ready, input_samplerate=None):
        self.model = whisper.load_model(WHISPER_MODEL)
        self.audio_queue = queue.Queue()
        self.should_stop = False
        self.transcription_ready = transcription_ready
        self.input_samplerate = input_samplerate or WHISPER_SAMPLERATE
        
        # Start transcription thread
        self.transcription_thread = threading.Thread(target=self.transcription_worker, daemon=True)
        self.transcription_thread.start()
    
    def queue_audio(self, audio_data):
        self.audio_queue.put(audio_data.copy())
    
    def transcription_worker(self):
        while not self.should_stop:
            audio_chunks = []
            timeout_counter = 0
            
            # Collect chunks for 2 seconds worth of audio
            target_samples = int(self.input_samplerate * 2)
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
                audio_data = np.concatenate(audio_chunks)
                
                # Resample if needed
                if self.input_samplerate != WHISPER_SAMPLERATE:
                    samples = len(audio_data)
                    new_samples = int(samples * WHISPER_SAMPLERATE / self.input_samplerate)
                    audio_data = signal.resample(audio_data, new_samples)
                
                audio_data = audio_data.astype(np.float32)
                audio_data = audio_data.flatten()
                max_amplitude = np.max(audio_data)
                
                if max_amplitude > 0.1:
                    audio_data = audio_data / max_amplitude
                    start = time.time()
                    result = self.model.transcribe(
                        audio_data,
                        language='en',
                        fp16=False,
                        condition_on_previous_text=False,
                        without_timestamps=True,
                    )
                    if result["text"].strip():
                        print(f"Transcribed text: {result['text']} in {time.time() - start:.2f} seconds")
                        self.transcription_ready.emit(result["text"])
    
    def stop(self):
        self.should_stop = True
