"""
ExpenseWise - Core Data Models
Pydantic models for expenses, users, budgets, and events
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import uuid


# ============================================================
# Enums
# ============================================================

class ExpenseCategory(str, Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    UTILITIES = "utilities"
    RENT = "rent"
    SALARY = "salary"
    INVESTMENT = "investment"
    TRAVEL = "travel"
    EDUCATION = "education"
    PERSONAL_CARE = "personal_care"
    GIFTS = "gifts"
    OTHER = "other"


class StorageProvider(str, Enum):
    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"


class TransactionType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class BudgetPeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class AgentIntent(str, Enum):
    LOG_EXPENSE = "log_expense"
    QUERY_EXPENSES = "query_expenses"
    GET_SUMMARY = "get_summary"
    SET_BUDGET = "set_budget"
    CHECK_BUDGET = "check_budget"
    START_EVENT = "start_event"
    END_EVENT = "end_event"
    GET_INSIGHTS = "get_insights"
    HELP = "help"
    UNKNOWN = "unknown"


# ============================================================
# Core Models
# ============================================================

class Expense(BaseModel):
    """Core expense record model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_phone: str = Field(..., description="WhatsApp phone number of user")
    amount: Decimal = Field(..., gt=0, description="Expense amount")
    currency: str = Field(default="INR", max_length=3)
    category: ExpenseCategory = Field(default=ExpenseCategory.OTHER)
    description: str = Field(..., min_length=1, max_length=500)
    merchant: Optional[str] = Field(None, max_length=200)
    transaction_type: TransactionType = Field(default=TransactionType.DEBIT)
    tags: List[str] = Field(default_factory=list)
    event_id: Optional[str] = Field(None, description="Associated event/trip ID")
    receipt_url: Optional[str] = Field(None, description="URL of receipt image")
    raw_input: Optional[str] = Field(None, description="Original user message")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat()}


class ExpenseCreate(BaseModel):
    """Model for creating a new expense"""
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="INR")
    category: Optional[ExpenseCategory] = None
    description: str
    merchant: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    event_id: Optional[str] = None
    raw_input: Optional[str] = None


class ExpenseUpdate(BaseModel):
    """Model for updating an expense"""
    amount: Optional[Decimal] = None
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    merchant: Optional[str] = None
    tags: Optional[List[str]] = None


class ExpenseQuery(BaseModel):
    """Model for querying expenses"""
    user_phone: str
    category: Optional[ExpenseCategory] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_id: Optional[str] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    limit: int = Field(default=50, le=500)


# ============================================================
# User Models
# ============================================================

class User(BaseModel):
    """User profile model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    phone: str = Field(..., description="WhatsApp phone (E.164 format)")
    name: Optional[str] = None
    currency: str = Field(default="INR")
    timezone: str = Field(default="Asia/Kolkata")
    storage_provider: Optional[StorageProvider] = None
    storage_token: Optional[str] = Field(None, description="Encrypted OAuth token")
    storage_folder_id: Optional[str] = None
    is_active: bool = True
    onboarding_complete: bool = False
    daily_summary_enabled: bool = True
    weekly_report_enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(BaseModel):
    phone: str
    name: Optional[str] = None
    currency: str = "INR"
    timezone: str = "Asia/Kolkata"


# ============================================================
# Budget Models
# ============================================================

class Budget(BaseModel):
    """Budget limit model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_phone: str
    category: Optional[ExpenseCategory] = Field(None, description="None = overall budget")
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="INR")
    period: BudgetPeriod = Field(default=BudgetPeriod.MONTHLY)
    alert_threshold: float = Field(default=0.8, description="Alert at 80% by default")
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BudgetStatus(BaseModel):
    """Real-time budget utilization status"""
    budget: Budget
    spent: Decimal
    remaining: Decimal
    utilization_percent: float
    is_over_budget: bool
    alert_triggered: bool


# ============================================================
# Event / Trip Models
# ============================================================

class ExpenseEvent(BaseModel):
    """Named expense session (trip, party, project, etc.)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_phone: str
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    participants: List[str] = Field(default_factory=list, description="List of phone numbers")
    is_active: bool = True
    total_amount: Decimal = Field(default=Decimal("0"))
    currency: str = Field(default="INR")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================
# Agent State Models
# ============================================================

class ConversationMessage(BaseModel):
    """A single message in conversation history"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentState(BaseModel):
    """LangGraph agent state"""
    user_phone: str
    user_message: str
    intent: Optional[AgentIntent] = None
    extracted_expense: Optional[ExpenseCreate] = None
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    response: Optional[str] = None
    error: Optional[str] = None
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================
# WhatsApp Models
# ============================================================

class WhatsAppMessage(BaseModel):
    """Incoming WhatsApp message"""
    message_id: str
    from_number: str
    body: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None  # 'image', 'audio', 'document'
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WhatsAppResponse(BaseModel):
    """Response to send back to WhatsApp"""
    to: str
    message: str
    success: bool = True


# ============================================================
# Report Models
# ============================================================

class DailySummary(BaseModel):
    """Daily expense summary"""
    user_phone: str
    date: str
    total_spent: Decimal
    currency: str
    category_breakdown: Dict[str, Decimal]
    expense_count: int
    top_expense: Optional[Expense] = None
    budget_status: Optional[BudgetStatus] = None
    message: str  # Formatted WhatsApp message


class InsightReport(BaseModel):
    """AI-generated spending insight"""
    user_phone: str
    period: str
    total_spent: Decimal
    total_income: Decimal
    net: Decimal
    currency: str
    category_breakdown: Dict[str, Decimal]
    top_categories: List[str]
    insights: List[str]  # AI-generated text insights
    recommendations: List[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
