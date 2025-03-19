import os
from twilio.rest import Client
from flask import Flask, request
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class TwilioSMS:    
    def __init__(self, account_sid=None, auth_token=None, twilio_phone_number=None):
        self.account_sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.environ.get("TWILIO_AUTH_TOKEN")
        self.twilio_phone_number = twilio_phone_number or os.environ.get("TWILIO_PHONE_NUMBER")
        
        # Initialize Twilio client
        self.client = Client(self.account_sid, self.auth_token)
    
    def send_sms(self, to_number, message_body):
        message = self.client.messages.create(
            body=message_body,
            from_=self.twilio_phone_number,
            to=to_number
        )
        return {
            "success": True,
            "message_sid": message.sid,
            "status": message.status
        }
    
    def send_mms(self, to_number, message_body, media_url):
        try:
            message = self.client.messages.create(
                body=message_body,
                from_=self.twilio_phone_number,
                to=to_number,
                media_url=media_url
            )
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


app = Flask(__name__)

@app.route("/sms", methods=['POST'])
def incoming_sms():
    # Get the message content
    incoming_message = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    
    print(f"From: {from_number}")
    print(f"Message: {incoming_message}")
    return ""


if __name__ == "__main__":
    twilio = TwilioSMS()
    result = twilio.send_sms(
        to_number="2243916520",  # Replace with actual recipient number
        message_body="Hello from Twilio!"
    )
    print(f"SMS sending result: {result}")