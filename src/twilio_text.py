import os
from twilio.rest import Client
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
    
    def send_sms(self, to_number, message_body, media_url=None):
        if media_url:
            message = self.client.messages.create(
                body=message_body,
                from_=self.twilio_phone_number,
                to=to_number,
                media_url=media_url
            )
        else:
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