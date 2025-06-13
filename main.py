import sys
import os
from PyQt6.QtWidgets import QApplication
from flask import Flask, render_template, request, send_from_directory
from flask_sock import Sock
from src.frontend import TranscriptionSignals, MainWindow
from src.audio_recorder import AudioRecorder
from src.transcriber import Transcriber, WHISPER_SAMPLERATE
from twilio.rest import Client

import threading
import json
import base64
import numpy as np

app = Flask(__name__)
sock = Sock(app)

qt_app = None
window = None
signals = None

def start_flask():
    app.run(host='0.0.0.0', port=5000)

@app.route('/twiml', methods=['POST'])
def return_twiml():
    """Initial TwiML response that plays ringtone and waits for acceptance"""
    
    call_sid = request.form.get('CallSid')
    caller = request.form.get('From', '')
    caller_state = request.form.get('CallerState', '')

    signals.incoming_call.emit(caller, caller_state, call_sid)
    
    ngrok_url = request.headers.get('Host')
    return render_template('streams.xml', url=ngrok_url)

@app.route('/accept', methods=['POST'])
def accept_call():
    """TwiML response when call is accepted"""
    caller = request.form.get('From', '')
    caller_state = request.form.get('CallerState', '')
    ngrok_url = request.headers.get('Host')
    return render_template('accept.xml', 
                         url=ngrok_url,
                         caller=caller,
                         caller_state=caller_state)

@app.route('/media', methods=['GET', 'POST'])
def media_fallback():
    """Handle regular HTTP requests to /media"""
    print(f"Non-WebSocket request to /media: {request.method}")
    print(f"Headers: {dict(request.headers)}")
    return "WebSocket endpoint", 200

@app.route("/sms", methods=['POST'])
def incoming_sms():
    # Get the message content
    incoming_message = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    
    print(f"From: {from_number}")
    print(f"Message: {incoming_message}")
    with open(f"outputs/messages/{from_number}.txt", "a") as f:
        f.write(f"\nInput: {incoming_message}")

    signals.incoming_msg.emit(from_number, incoming_message)
    return ""

@sock.route('/media')
def media_stream(ws):
    print("WebSocket connected")

    first_message = True

    while True:
        message = ws.receive()
        if message:
            data = json.loads(message)
            if data['event'] == 'start':
                # Extract caller information from start event
                caller_number = data['start']['customParameters']['caller_number']
                caller_state = data['start']['customParameters']['caller_state']
                window.audio_recorder.start_call(data['start']['streamSid'], ws)
                if window:
                    window.start_recording_from_call()
                    signals.call_status_changed.emit("start")
                    
            elif data['event'] == 'media' and 'media' in data:
                media = data['media']
                
                if first_message:
                    first_message = False
                    
                    
                audio_data = process_audio_payload(media['payload'])
                if audio_data is not None:
                    window.audio_recorder.process_audio(audio_data)

            elif data['event'] == 'stop':
                print("Received stop event")
                signals.call_status_changed.emit("stop")
                window.audio_recorder.stop_call()
                break
        else:
            print("No message received")
            break

def process_audio_payload(payload):
    """Process base64 encoded mulaw audio data from Twilio"""
    try:
        audio_bytes = base64.b64decode(payload)
        audio_data = np.frombuffer(audio_bytes, dtype=np.uint8)
        return audio_data
    except Exception as e:
        print(f"Error processing audio payload: {e}")
        return None

def main():
    global qt_app, window, signals
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    # Start Qt application
    qt_app = QApplication(sys.argv)
    signals = TranscriptionSignals()
    
    # Create audio recorder first to detect devices
    recorder = AudioRecorder(None, None)
    
    mic_transcriber = Transcriber(signals.mic_transcription_ready)
    mix_transcriber = Transcriber(signals.mix_transcription_ready)

    recorder.input_transcriber = mic_transcriber
    recorder.mix_transcriber = mix_transcriber
    
    window = MainWindow(recorder, signals)
    window.show()
    sys.exit(qt_app.exec())

if __name__ == '__main__':
    main()