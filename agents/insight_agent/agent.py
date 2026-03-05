"""
ExpenseWise - Insight Agent
Generates AI-powered spending insights, summaries, and reports.
Handles: daily summary, weekly report, custom queries, trend analysis.
"""

import json
from decimal import Decimal
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from collections import defaultdict

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from loguru import logger

from api.config import settings
from api.models.expense import AgentState, AgentIntent


# ============================================================
# Insight Generation Prompt
# ============================================================

INSIGHT_PROMPT = """
You are a personal finance advisor for ExpenseWise.
Analyze the user's spending data and generate helpful insights.

Spending Data:
{spending_data}

User Query: {query}
Period: {period}

Generate a response that includes:
1. Key spending patterns
2. Top spending categories
3. Comparison to typical spending (if applicable)
4. 2-3 actionable recommendations
5. One positive observation

Format for WhatsApp (use *bold* for emphasis, keep it concise and friendly).
Limit to 300 words max.
"""


SUMMARY_FORMAT = """
You are generating a WhatsApp expense summary message.
Be concise, use emojis appropriately, format nicely.

Data: {data}
Period: {period}

Create a clean summary with:
- Total spent
- Category breakdown (top 5)
- Comparison to yesterday/last week
- One insight or tip

Use *bold* for numbers. Keep under 200 words.
"""


# ============================================================
# Data Aggregation Helpers
# ============================================================

def aggregate_by_category(expenses: List[dict]) -> Dict[str, Decimal]:
    """Sum expenses by category"""
    totals = defaultdict(Decimal)
    for exp in expenses:
        category = exp.get("category", "other")
        amount = Decimal(str(exp.get("amount", 0)))
        totals[category] += amount
    return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))


def format_category_breakdown(breakdown: Dict[str, Decimal], currency: str) -> str:
    """Format category breakdown for display"""
    emoji_map = {
        "food": "\ud83c\udf74",
        "transport": "\ud83d\ude97",
        "shopping": "\ud83d\udecd",
        "entertainment": "\ud83c\udfac",
        "health": "\ud83c\udfe5",
        "utilities": "\ud83d\udca1",
        "rent": "\ud83c\udfe0",
        "travel": "\u2708",
        "education": "\ud83d\udcda",
        "other": "\ud83d\udcb8",
    }
    
    lines = []
    for category, amount in list(breakdown.items())[:5]:  # Top 5
        emoji = emoji_map.get(category, "\ud83d\udcb8")
        cat_name = category.replace("_", " ").title()
        lines.append(f"{emoji} {cat_name}: {currency} {amount:,.0f}")
    
    return "\n".join(lines)


# ============================================================
# Daily Summary
# ============================================================

def generate_daily_summary_text(
    expenses: List[dict],
    total: Decimal,
    currency: str,
    target_date: str,
) -> str:
    """Generate a formatted daily summary without calling LLM"""
    if not expenses:
        return (
            f"\ud83d\uddd3 *No expenses on {target_date}*\n\n"
            f"Great job! No expenses recorded today.\n"
            f"Type 'weekly report' to see your week."
        )
    
    breakdown = aggregate_by_category(expenses)
    breakdown_text = format_category_breakdown(breakdown, currency)
    count = len(expenses)
    avg = total / count if count > 0 else Decimal("0")
    
    return (
        f"\ud83d\uddd3 *Daily Summary - {target_date}*\n\n"
        f"*Total Spent:* {currency} {total:,.0f}\n"
        f"*Transactions:* {count}\n"
        f"*Average:* {currency} {avg:,.0f}\n\n"
        f"*By Category:*\n{breakdown_text}\n\n"
        f"Type 'insights' for AI analysis or 'weekly report' for the week."
    )


def generate_weekly_summary_text(
    expenses: List[dict],
    total: Decimal,
    currency: str,
    week_start: str,
    week_end: str,
) -> str:
    """Generate weekly summary text"""
    if not expenses:
        return (
            f"\ud83d\udcc6 *Weekly Report ({week_start} to {week_end})*\n\n"
            f"No expenses this week. Keep tracking!"
        )
    
    breakdown = aggregate_by_category(expenses)
    breakdown_text = format_category_breakdown(breakdown, currency)
    
    # Daily average
    daily_avg = total / 7
    top_category = list(breakdown.keys())[0] if breakdown else "N/A"
    top_amount = list(breakdown.values())[0] if breakdown else Decimal("0")
    
    return (
        f"\ud83d\udcc6 *Weekly Report*\n"
        f"{week_start} to {week_end}\n\n"
        f"*Total Spent:* {currency} {total:,.0f}\n"
        f"*Daily Average:* {currency} {daily_avg:,.0f}\n"
        f"*Transactions:* {len(expenses)}\n\n"
        f"*Top Spending:*\n{breakdown_text}\n\n"
        f"*Biggest Category:* {top_category.replace('_', ' ').title()} ({currency} {top_amount:,.0f})\n\n"
        f"Type 'insights' for personalized AI recommendations."
    )


# ============================================================
# LangGraph Node
# ============================================================

async def insight_agent_node(state: AgentState) -> AgentState:
    """LangGraph node: Generate insights, summaries, and reports"""
    try:
        intent = state.intent
        message = state.user_message.lower()
        
        # Determine period
        today = date.today()
        period = "today"
        
        if any(w in message for w in ["week", "7 day", "7days"]):
            period = "week"
        elif any(w in message for w in ["month", "30 day", "monthly"]):
            period = "month"
        elif any(w in message for w in ["yesterday"]):
            period = "yesterday"
        
        # Mark what period we need to fetch
        state.metadata["insight_period"] = period
        state.metadata["insight_query"] = state.user_message
        
        # For now - generate a placeholder response
        # In full implementation, storage agent loads expenses first
        if intent == AgentIntent.GET_SUMMARY or "summary" in message or "today" in message:
            state.response = (
                f"\ud83d\uddd3 *Today's Summary*\n\n"
                f"Fetching your expenses...\n"
                f"Use Google Drive integration to see real data.\n\n"
                f"*Setup:* Connect your Google Drive to see live summaries!\n"
                f"Type 'connect drive' to get started."
            )
        elif period == "week":
            state.response = (
                f"\ud83d\udcc6 *Weekly Report*\n\n"
                f"Fetching this week's data...\n"
                f"Connect your cloud storage for real insights!"
            )
        else:
            # Generate AI insight from available context
            llm = ChatBedrock(
                model_id=settings.bedrock_model_id,
                model_kwargs={"max_tokens": 512, "temperature": 0.3},
                region_name=settings.aws_region,
            )
            
            prompt = f"""Generate a helpful expense tracking tip or insight for a WhatsApp user.
            They asked: '{state.user_message}'
            Keep it under 150 words, format nicely for WhatsApp with *bold* text.
            Be warm and helpful."""
            
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            state.response = response.content
        
    except Exception as e:
        logger.error(f"Insight agent error: {e}")
        state.response = "I had trouble generating insights. Please try again."
    
    return state
