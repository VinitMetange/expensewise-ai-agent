"""Expense management REST API routes"""
from datetime import date
from typing import List, Optional
import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.database import get_user
from integrations.google_drive.client import GoogleDriveClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/expenses", tags=["expenses"])


class ExpenseCreate(BaseModel):
    amount: float
    currency: str = "USD"
    category: str
    description: str
    merchant: Optional[str] = None
    payment_method: Optional[str] = None
    date: date


@router.get("/{phone}")
async def get_expenses(
    phone: str,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    """Get expenses for a user in date range"""
    user = await get_user(phone)
    if not user or not user.get("storage_provider"):
        raise HTTPException(status_code=404, detail="User not found or storage not connected")
    drive_client = await GoogleDriveClient.for_user(phone)
    if not drive_client:
        raise HTTPException(status_code=401, detail="Storage not connected")
    if not start_date:
        today = date.today()
        start_date = today.replace(day=1)
    if not end_date:
        end_date = date.today()
    expenses = await drive_client.get_expenses(start_date, end_date)
    return {"expenses": expenses, "count": len(expenses)}


@router.get("/{phone}/export")
async def export_expenses(
    phone: str,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    """Export expenses as CSV and return download link"""
    user = await get_user(phone)
    if not user or not user.get("storage_provider"):
        raise HTTPException(status_code=404, detail="User not found or storage not connected")
    drive_client = await GoogleDriveClient.for_user(phone)
    if not drive_client:
        raise HTTPException(status_code=401, detail="Storage not connected")
    if not start_date:
        today = date.today()
        start_date = today.replace(day=1)
    if not end_date:
        end_date = date.today()
    csv_url = await drive_client.export_to_csv(start_date, end_date)
    if not csv_url:
        raise HTTPException(status_code=404, detail="No expenses found for date range")
    return {"csv_url": csv_url, "start_date": start_date, "end_date": end_date}


@router.get("/{phone}/budgets")
async def get_budgets(phone: str):
    """Get user's budget configuration"""
    user = await get_user(phone)
    if not user or not user.get("storage_provider"):
        raise HTTPException(status_code=404, detail="User not found or storage not connected")
    drive_client = await GoogleDriveClient.for_user(phone)
    if not drive_client:
        raise HTTPException(status_code=401, detail="Storage not connected")
    budgets = await drive_client.get_budgets()
    return {"budgets": budgets}


@router.post("/{phone}/budgets")
async def save_budgets(phone: str, budgets: List[dict]):
    """Save user's budget configuration"""
    user = await get_user(phone)
    if not user or not user.get("storage_provider"):
        raise HTTPException(status_code=404, detail="User not found")
    drive_client = await GoogleDriveClient.for_user(phone)
    if not drive_client:
        raise HTTPException(status_code=401, detail="Storage not connected")
    success = await drive_client.save_budgets(budgets)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save budgets")
    return {"message": "Budgets saved successfully"}


@router.get("/{phone}/summary")
async def get_summary(
    phone: str,
    period: str = Query(default="month", description="day, week, month, year"),
):
    """Get expense summary for a period"""
    from datetime import timedelta
    today = date.today()
    if period == "day":
        start_date = today
    elif period == "week":
        start_date = today - timedelta(days=today.weekday())
    elif period == "month":
        start_date = today.replace(day=1)
    elif period == "year":
        start_date = today.replace(month=1, day=1)
    else:
        start_date = today.replace(day=1)
    user = await get_user(phone)
    if not user or not user.get("storage_provider"):
        raise HTTPException(status_code=404, detail="User not found")
    drive_client = await GoogleDriveClient.for_user(phone)
    if not drive_client:
        raise HTTPException(status_code=401, detail="Storage not connected")
    expenses = await drive_client.get_expenses(start_date, today)
    total = sum(e.get("amount", 0) for e in expenses)
    by_category = {}
    for e in expenses:
        cat = e.get("category", "Other")
        by_category[cat] = by_category.get(cat, 0) + e.get("amount", 0)
    return {
        "period": period,
        "start_date": start_date,
        "end_date": today,
        "total": total,
        "count": len(expenses),
        "by_category": by_category,
        "currency": user.get("currency", "USD"),
    }
