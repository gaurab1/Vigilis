import threading
import queue
import numpy as np
import whisper
from src.constants import WHISPER_MODEL
import time

class Transcriber:
    def __init__(self, transcription_ready):
        self.model = whisper.load_model(WHISPER_MODEL)
        self.audio_queue = queue.Queue()
        self.should_stop = False
        self.transcription_ready = transcription_ready
        
        # Start transcription thread
        self.transcription_thread = threading.Thread(target=self.transcription_worker, daemon=True)
        self.transcription_thread.start()
    
    def queue_audio(self, audio_data):
        try:
            self.audio_queue.put(audio_data.copy())
        except Exception as e:
            print(f"Error queuing audio: {e}")
    
    def transcription_worker(self):
        while not self.should_stop:
            # Collect audio data for 2 seconds
            audio_chunks = []
            timeout_counter = 0
            
            # Collect chunks for 2 seconds worth of audio
            target_samples = int(16000 * 2)  # 2 seconds of audio at 16kHz
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
                        self.transcription_ready.emit(result["text"])
                except Exception as e:
                    print(f"Transcription failed: {e}")
    
    def stop(self):
        self.should_stop = True
