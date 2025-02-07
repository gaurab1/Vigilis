from flask import Flask, render_template, request
from flask_sock import Sock
import json
import base64
import numpy as np
import wave
import os
import audioop
import sounddevice as sd
sd.default.latency = 'low'
import queue
from datetime import datetime

app = Flask(__name__)
sock = Sock(app)

class AudioStreamHandler:
    def __init__(self, stream_sid, websocket):
        self.stream_sid = stream_sid
        self.ws = websocket
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        os.makedirs("outputs", exist_ok=True)
        
        # WAV file setup for incoming audio
        self.wav_file = wave.open(f"outputs/call_{timestamp}_{stream_sid}.wav", 'wb')
        self.wav_file.setnchannels(1)  # Mono
        self.wav_file.setsampwidth(2)  # 16-bit audio
        self.wav_file.setframerate(8000)  # 8kHz sample rate
        self.chunks_received = 0
        
        # Audio playback setup
        self.audio_queue = queue.Queue()
        self.stream_out = sd.OutputStream(
            samplerate=8000,
            channels=1,
            dtype=np.int16,
            callback=self._audio_callback_output
        )
        
        # Microphone input setup
        self.stream_in = sd.InputStream(
            samplerate=8000,
            channels=1,
            dtype=np.int16,
            callback=self._audio_callback_input,
            blocksize=160  # 20ms chunks at 8kHz
        )
        
        # Start streams
        self.stream_out.start()
        self.stream_in.start()
        self.active = True
    
    def _audio_callback_output(self, outdata, frames, time, status):
        """Callback for audio output"""
        try:
            data = self.audio_queue.get_nowait()
            if len(data) < len(outdata):
                outdata[:len(data)] = data
                outdata[len(data):] = np.zeros((len(outdata) - len(data), 1), dtype=np.int16)
            else:
                outdata[:] = data[:len(outdata)]
        except queue.Empty:
            outdata[:] = np.zeros((len(outdata), 1), dtype=np.int16)
    
    def _audio_callback_input(self, indata, frames, time, status):
        """Callback for microphone input"""
        if not self.active:
            return
            
        if status:
            print(status)
        
        try:
            # Convert to PCM then mu-law
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
            self.ws.send(json.dumps(message))
        except Exception as e:
            print(f"Error sending audio: {e}")
    
    def process_audio(self, audio_data):
        """Convert mulaw to PCM and handle audio data"""
        # Convert mulaw to 16-bit PCM using audioop
        pcm_data = audioop.ulaw2lin(audio_data.tobytes(), 2)
        
        # Save to WAV file
        self.wav_file.writeframes(pcm_data)
        self.chunks_received += 1
        
        # Convert to numpy array for playback
        pcm_array = np.frombuffer(pcm_data, dtype=np.int16)
        # Reshape for mono output
        pcm_array = pcm_array.reshape(-1, 1)
        # Add to playback queue
        self.audio_queue.put(pcm_array)
    
    def close(self):
        self.active = False
        if hasattr(self, 'stream_out'):
            self.stream_out.stop()
            self.stream_out.close()
        if hasattr(self, 'stream_in'):
            self.stream_in.stop()
            self.stream_in.close()
        self.wav_file.close()
        print(f"Saved {self.chunks_received} chunks of audio")

def process_audio_payload(payload):
    """Process base64 encoded mulaw audio data from Twilio"""
    try:
        # Decode base64 to bytes
        audio_bytes = base64.b64decode(payload)
        # Convert to numpy array (8-bit unsigned integers)
        audio_data = np.frombuffer(audio_bytes, dtype=np.uint8)
        return audio_data
    except Exception as e:
        print(f"Error processing audio payload: {e}")
        return None

@app.route('/twiml', methods=['POST'])
def return_twiml(): 
    print("POST TwiML")
    print(f"Headers: {dict(request.headers)}")
    print(f"Data: {request.get_data().decode()}")
    ngrok_url = request.headers.get('Host')
    return render_template('streams.xml', url=ngrok_url)

@app.route('/media', methods=['GET', 'POST'])
def media_fallback():
    """Handle regular HTTP requests to /media"""
    print(f"Non-WebSocket request to /media: {request.method}")
    print(f"Headers: {dict(request.headers)}")
    return "WebSocket endpoint", 200

@sock.route('/media')
def media_stream(ws):
    print("WebSocket connected")
    stream_handler = None

    while True:
        message = ws.receive()
        if message:
            data = json.loads(message)
            if data['event'] == 'media' and 'media' in data:
                media = data['media']
                
                # Initialize stream handler if this is the first chunk
                if stream_handler is None:
                    stream_handler = AudioStreamHandler(data['streamSid'], ws)
                    print(f"Started recording stream {data['streamSid']}")
                
                if 'payload' in media:
                    audio_data = process_audio_payload(media['payload'])
                    if audio_data is not None:
                        stream_handler.process_audio(audio_data)
            elif data['event'] == 'stop':
                print("Received stop event")
                break
        else:
            print("No message received")
            break

    if stream_handler:
        stream_handler.close()
    print("WebSocket closed")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)