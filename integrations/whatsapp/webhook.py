"""
ExpenseWise - WhatsApp Webhook Handler
Handles all incoming WhatsApp messages via Twilio
Routes to the AI Agent Orchestrator
"""

import hmac
import hashlib
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Request, Form, Header, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from loguru import logger
from twilio.request_validator import RequestValidator

from api.config import settings
from api.models.expense import WhatsAppMessage
from agents.orchestrator.graph import run_agent
from integrations.whatsapp.sender import send_whatsapp_message
from integrations.whatsapp.onboarding import handle_onboarding

router = APIRouter()


# ============================================================
# Twilio Signature Validation
# ============================================================

def validate_twilio_signature(request_url: str, params: dict, signature: str) -> bool:
    """Validate incoming webhook is genuinely from Twilio"""
    if not settings.twilio_auth_token:
        logger.warning("Twilio auth token not configured - skipping validation")
        return True
    validator = RequestValidator(settings.twilio_auth_token)
    return validator.validate(request_url, params, signature)


# ============================================================
# Message Parsing
# ============================================================

def parse_twilio_message(form_data: dict) -> Optional[WhatsAppMessage]:
    """Parse a Twilio WhatsApp webhook payload into WhatsAppMessage"""
    try:
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        body = form_data.get("Body", "").strip()
        message_id = form_data.get("MessageSid", "")
        media_url = form_data.get("MediaUrl0")
        media_type = form_data.get("MediaContentType0")

        if not from_number:
            return None

        return WhatsAppMessage(
            message_id=message_id,
            from_number=from_number,
            body=body if body else None,
            media_url=media_url,
            media_type=media_type.split("/")[0] if media_type else None,
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"Failed to parse Twilio message: {e}")
        return None


# ============================================================
# Background Task: Process Message via AI Agent
# ============================================================

async def process_message_async(message: WhatsAppMessage):
    """Process message through AI agent pipeline asynchronously"""
    try:
        logger.info(f"Processing message from {message.from_number}: {message.body[:50] if message.body else '[media]'}")

        # Check if user needs onboarding
        onboarding_response = await handle_onboarding(message.from_number)
        if onboarding_response:
            await send_whatsapp_message(message.from_number, onboarding_response)
            return

        # Run through AI Agent Orchestrator
        response = await run_agent(
            user_phone=message.from_number,
            message=message,
        )

        # Send response back to user
        if response:
            await send_whatsapp_message(message.from_number, response)

    except Exception as e:
        logger.error(f"Error processing message from {message.from_number}: {e}")
        error_msg = "Sorry, I encountered an error. Please try again or type *help* for assistance."
        await send_whatsapp_message(message.from_number, error_msg)


# ============================================================
# Webhook Endpoints
# ============================================================

@router.post("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_twilio_signature: Optional[str] = Header(None),
):
    """
    Main WhatsApp webhook endpoint.
    Twilio sends a POST here for every incoming message.
    We respond immediately (200 OK) and process asynchronously.
    """
    try:
        # Parse form data
        form_data = dict(await request.form())

        # Validate signature in production
        if settings.app_env == "production" and x_twilio_signature:
            is_valid = validate_twilio_signature(
                str(request.url), form_data, x_twilio_signature
            )
            if not is_valid:
                logger.warning(f"Invalid Twilio signature from {request.client.host}")
                raise HTTPException(status_code=403, detail="Invalid signature")

        # Parse message
        message = parse_twilio_message(form_data)
        if not message:
            logger.warning("Could not parse incoming message")
            return PlainTextResponse("OK")

        # Process in background (respond immediately to Twilio)
        background_tasks.add_task(process_message_async, message)

        # Twilio expects empty 200 response
        return PlainTextResponse("")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return PlainTextResponse("")


@router.get("/whatsapp/health", response_class=PlainTextResponse)
async def webhook_health():
    """Health check for WhatsApp webhook"""
    return PlainTextResponse("ExpenseWise WhatsApp webhook is active")
