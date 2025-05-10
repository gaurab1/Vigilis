# Vigilis

A fraud-protected desktop application allowing users to stay secure during audio calls, text messages, and web browsing.

## Features
- Send or Receive calls to/from your Twilio phone number, with active transcription
- Save recordings in WAV format, and transcripts in a .txt file
- Chat with people in a secure manner!

## Twilio & ngrok Setup
- Get a Twilio Account SID and Auth Token from [here](https://www.twilio.com/console)
- Get a Twilio Phone Number to make calls from (e.g. +1234567890)
- Make a Twilio API Key from [here](https://www.twilio.com/console/voice/apikeys)
- Create a TwiML App from [here](https://www.twilio.com/console/voice/twiml/apps)
- Make sure ngrok is installed in your system, and run the following command:
`ngrok http 5000 [--url your_url_if_exists]`
- Copy the ngrok URL into the endpoint of the TwiML App. You will not be able to make calls yet, but will be able to do so when running the Python app.
- Copy all of the environment variables into the .env.template file, and rename it to your .env file.

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

## Note
Make sure you have the necessary permissions and consent before recording any conversations.
