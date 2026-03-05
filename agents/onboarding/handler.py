"""Onboarding handler - guides new users through setup via WhatsApp"""
import logging
from typing import Optional

from api.config import settings
from api.database import get_user, create_user, update_user
from integrations.whatsapp.sender import WhatsAppSender

logger = logging.getLogger(__name__)

WELCOME_MESSAGE = """👋 Welcome to *ExpenseWise* - your AI expense tracker!

I help you track expenses, set budgets, and generate reports - all via WhatsApp.

To get started, I need to connect to your cloud storage to securely save your data.

Your data is *only stored in YOUR Google Drive* - we never store your financial data on our servers.

Reply with *CONNECT* to link your Google Drive."""

CONNECTING_MESSAGE = """Great! Click the link below to connect your Google Drive:

{auth_url}

This link expires in 10 minutes. Your data will be stored in a folder called 'ExpenseWise' in your Google Drive."""

ALREADY_ONBOARDED_MESSAGE = """You're already set up! Here's what you can do:

📝 *Log expense:* "Spent $45 on dinner at Pizza Hut"
📊 *View summary:* "Show this month's expenses"
💰 *Set budget:* "Set $500 monthly food budget"
📈 *Get insights:* "Analyze my spending patterns"
📤 *Export:* "Export expenses to CSV"

What would you like to do?"""

HELP_MESSAGE = """*ExpenseWise Commands:*

📝 Log: "Spent $50 on groceries"
📊 Summary: "Show this month"
💰 Budget: "Set $300 food budget"
📈 Insight: "Where am I overspending?"
📤 Export: "Export to CSV"
🔗 Reconnect: "CONNECT" to re-link storage

Tip: You can also send photos of receipts!"""


class OnboardingHandler:
    """Handles the user onboarding flow"""

    def __init__(self):
        self.sender = WhatsAppSender()

    async def handle(self, phone: str, message: str) -> Optional[str]:
        """Handle onboarding messages. Returns response or None if handled by orchestrator."""
        message_lower = message.strip().lower()
        user = await get_user(phone)

        # New user first contact
        if not user:
            await create_user(phone)
            await self.sender.send_message(phone, WELCOME_MESSAGE)
            return WELCOME_MESSAGE

        # Already onboarded
        if user.get("is_onboarded"):
            if message_lower in ["help", "/help", "?"]:
                await self.sender.send_message(phone, HELP_MESSAGE)
                return HELP_MESSAGE
            return None  # Pass to orchestrator

        # Not yet onboarded - handle CONNECT command
        if message_lower in ["connect", "connect google drive", "link", "setup"]:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{settings.api_base_url}/auth/google/initiate/{phone}"
                    )
                    data = response.json()
                    auth_url = data.get("auth_url", "")
                msg = CONNECTING_MESSAGE.format(auth_url=auth_url)
                await self.sender.send_message(phone, msg)
                return msg
            except Exception as e:
                logger.error(f"Error generating auth URL: {e}")
                error_msg = "Sorry, I couldn't generate the connection link. Please try again."
                await self.sender.send_message(phone, error_msg)
                return error_msg

        # Not yet connected - prompt to connect
        prompt = (
            "You haven't connected your Google Drive yet.\n\n"
            "Reply with *CONNECT* to get started, or type *HELP* to learn more."
        )
        await self.sender.send_message(phone, prompt)
        return prompt

    async def send_welcome(self, phone: str):
        """Send welcome message to new user"""
        await self.sender.send_message(phone, WELCOME_MESSAGE)

    async def check_is_onboarded(self, phone: str) -> bool:
        """Check if user has completed onboarding"""
        user = await get_user(phone)
        if not user:
            return False
        return user.get("is_onboarded", False)

    async def send_onboarding_reminder(self, phone: str):
        """Send reminder to complete onboarding"""
        msg = (
            "Don't forget to connect your Google Drive to start tracking expenses!\n\n"
            "Reply *CONNECT* to link your account."
        )
        await self.sender.send_message(phone, msg)
