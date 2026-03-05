"""
ExpenseWise - WhatsApp Message Sender
Sends outbound messages via Twilio WhatsApp API
"""

from typing import Optional
from loguru import logger
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from tenacity import retry, stop_after_attempt, wait_exponential

from api.config import settings


# Initialize Twilio client
_twilio_client: Optional[Client] = None


def get_twilio_client() -> Client:
    """Get or create singleton Twilio client"""
    global _twilio_client
    if _twilio_client is None:
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            raise ValueError("Twilio credentials not configured")
        _twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    return _twilio_client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def send_whatsapp_message(
    to_number: str,
    message: str,
    media_url: Optional[str] = None,
) -> bool:
    """
    Send a WhatsApp message via Twilio.
    Auto-retries up to 3 times on failure.
    
    Args:
        to_number: Recipient phone (E.164 format, e.g. +919876543210)
        message: Text content
        media_url: Optional URL of image/file to send
    
    Returns:
        True if sent successfully
    """
    try:
        client = get_twilio_client()
        to_whatsapp = f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number
        
        params = {
            "from_": settings.twilio_whatsapp_from,
            "to": to_whatsapp,
            "body": message,
        }
        
        if media_url:
            params["media_url"] = [media_url]
        
        msg = client.messages.create(**params)
        logger.info(f"Message sent to {to_number}: SID={msg.sid}")
        return True

    except TwilioRestException as e:
        logger.error(f"Twilio error sending to {to_number}: {e.msg}")
        raise
    except Exception as e:
        logger.error(f"Failed to send message to {to_number}: {e}")
        raise


async def send_whatsapp_template(
    to_number: str,
    template_sid: str,
    variables: dict,
) -> bool:
    """Send a pre-approved WhatsApp template message"""
    try:
        client = get_twilio_client()
        to_whatsapp = f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number
        
        msg = client.messages.create(
            from_=settings.twilio_whatsapp_from,
            to=to_whatsapp,
            content_sid=template_sid,
            content_variables=str(variables),
        )
        logger.info(f"Template message sent to {to_number}: SID={msg.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send template to {to_number}: {e}")
        return False
