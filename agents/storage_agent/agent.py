"""
ExpenseWise - Storage Agent
Handles reading/writing expense data to user's cloud storage.
Supports: Google Drive (primary), Dropbox, OneDrive

Storage Structure (user's Google Drive):
  ExpenseWise/
    expenses/
      2026-03.json       <- Monthly expense file
      2026-02.json
    budgets.json
    events/
      goa-trip-2026.json
    summary/
      weekly-2026-W10.json
"""

import json
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from loguru import logger

from api.config import settings
from api.models.expense import AgentState, Expense, ExpenseCreate
from integrations.google_drive.client import GoogleDriveClient


# ============================================================
# Storage Agent Node
# ============================================================

async def storage_agent_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Save expense to user's cloud storage.
    Called after logging + categorization agents.
    """
    try:
        expense = state.extracted_expense
        if not expense:
            return state  # Nothing to store
        
        # Build full expense object
        full_expense = Expense(
            user_phone=state.user_phone,
            amount=expense.amount,
            currency=expense.currency,
            category=expense.category,
            description=expense.description,
            merchant=expense.merchant,
            tags=expense.tags,
            event_id=expense.event_id,
            raw_input=expense.raw_input,
        )
        
        # Try to save to Google Drive
        try:
            drive_client = await GoogleDriveClient.for_user(state.user_phone)
            if drive_client:
                await drive_client.save_expense(full_expense)
                logger.info(f"Expense saved to Google Drive for {state.user_phone}")
                # Update response to note it was saved
                if state.response:
                    state.response += "\n\n_Saved to your Google Drive_ \u2705"
            else:
                # Storage not configured - store locally (fallback)
                logger.warning(f"No cloud storage for {state.user_phone} - expense stored in memory only")
                state.response = (state.response or "") + (
                    "\n\n\u26a0\ufe0f *Storage not connected!*\n"
                    "Connect Google Drive to persist your expenses.\n"
                    "Type *'connect drive'* to set up."
                )
        except Exception as storage_error:
            logger.error(f"Storage error for {state.user_phone}: {storage_error}")
            # Don't fail the whole pipeline for storage errors
            state.response = (state.response or "") + "\n\n_(Storage unavailable - expense not saved)_"
        
    except Exception as e:
        logger.error(f"Storage agent error: {e}")
    
    return state


# ============================================================
# Expense Retrieval
# ============================================================

async def load_expenses_for_period(
    user_phone: str,
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    """Load expenses from user's cloud storage for a date range"""
    try:
        drive_client = await GoogleDriveClient.for_user(user_phone)
        if not drive_client:
            return []
        
        expenses = await drive_client.get_expenses(start_date, end_date)
        return expenses
    except Exception as e:
        logger.error(f"Error loading expenses for {user_phone}: {e}")
        return []


async def load_budgets_for_user(user_phone: str) -> List[Dict[str, Any]]:
    """Load user's budget configuration from cloud storage"""
    try:
        drive_client = await GoogleDriveClient.for_user(user_phone)
        if not drive_client:
            return []
        
        budgets = await drive_client.get_budgets()
        return budgets
    except Exception as e:
        logger.error(f"Error loading budgets for {user_phone}: {e}")
        return []
