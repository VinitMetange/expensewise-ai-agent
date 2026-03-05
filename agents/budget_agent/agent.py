"""
ExpenseWise - Budget Agent
Handles budget setting, monitoring, and alerts.
"""

import json
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from loguru import logger

from api.config import settings
from api.models.expense import AgentState, AgentIntent, Budget, BudgetPeriod, ExpenseCategory


BUDGET_PARSE_PROMPT = """
Extract budget-setting details from this message.

Message: "{message}"

Return JSON:
{{
  "action": "set" or "check",
  "amount": <number or null>,
  "category": "<category name or null for overall>",
  "period": "daily" | "weekly" | "monthly" | "yearly",
  "currency": "<3-letter code, default INR>"
}}

Examples:
- "set food budget 5000" -> action: set, amount: 5000, category: food, period: monthly
- "monthly budget 20000" -> action: set, amount: 20000, category: null, period: monthly
- "how's my budget" -> action: check

Respond with valid JSON only.
"""


async def parse_budget_intent(message: str) -> dict:
    """Parse budget action from user message"""
    try:
        llm = ChatBedrock(
            model_id=settings.bedrock_model_id,
            model_kwargs={"max_tokens": 256, "temperature": 0.0},
            region_name=settings.aws_region,
        )
        prompt = BUDGET_PARSE_PROMPT.format(message=message)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return json.loads(response.content.strip())
    except Exception as e:
        logger.error(f"Budget parse error: {e}")
        return {"action": "check"}


def format_budget_set_confirmation(amount: Decimal, category: Optional[str], period: str, currency: str) -> str:
    """Format budget set confirmation message"""
    category_str = category.replace('_', ' ').title() if category else "Overall"
    return (
        f"*Budget Set!* \ud83d\udcca\n\n"
        f"*Category:* {category_str}\n"
        f"*Limit:* {currency} {amount:,.0f}\n"
        f"*Period:* {period.title()}\n\n"
        f"I'll alert you when you reach 80% of this budget."
    )


def format_budget_status(budgets_data: list) -> str:
    """Format budget status check response"""
    if not budgets_data:
        return (
            "You haven't set any budgets yet!\n\n"
            "Set one by typing:\n"
            "*'Set food budget 5000'*\n"
            "*'Monthly budget 20000'*"
        )
    
    lines = ["*Your Budget Status* \ud83d\udcca\n"]
    for item in budgets_data:
        budget = item.get("budget", {})
        spent = item.get("spent", 0)
        remaining = item.get("remaining", 0)
        utilization = item.get("utilization_percent", 0)
        
        category = budget.get("category") or "Overall"
        if isinstance(category, str):
            category = category.replace('_', ' ').title()
        
        status_emoji = "\ud83d\udfe2" if utilization < 80 else ("\ud83d\udfe1" if utilization < 100 else "\ud83d\udd34")
        
        lines.append(
            f"{status_emoji} *{category}*\n"
            f"   Spent: {budget.get('currency', 'INR')} {spent:,.0f} / {budget.get('amount', 0):,.0f}\n"
            f"   Used: {utilization:.0f}% | Remaining: {remaining:,.0f}"
        )
    
    return "\n\n".join(lines)


async def budget_agent_node(state: AgentState) -> AgentState:
    """LangGraph node: Handle budget set and check operations"""
    try:
        intent_data = await parse_budget_intent(state.user_message)
        action = intent_data.get("action", "check")
        
        if action == "set" and intent_data.get("amount"):
            amount = Decimal(str(intent_data["amount"]))
            category = intent_data.get("category")
            period = intent_data.get("period", "monthly")
            currency = intent_data.get("currency", "INR")
            
            # Store budget config in metadata for storage agent
            state.metadata["budget_action"] = "set"
            state.metadata["budget_config"] = {
                "amount": str(amount),
                "category": category,
                "period": period,
                "currency": currency,
            }
            
            state.response = format_budget_set_confirmation(amount, category, period, currency)
            
        else:
            # Check budget status - retrieve from storage
            state.metadata["budget_action"] = "check"
            
            # Placeholder response (storage agent will enrich this)
            state.response = (
                "*Budget Status* \ud83d\udcca\n\n"
                "Fetching your budget status from storage...\n\n"
                "To set a budget, type:\n"
                "*'Set food budget 5000'*"
            )
        
    except Exception as e:
        logger.error(f"Budget agent error: {e}")
        state.response = "I had trouble processing your budget request. Please try again."
    
    return state


# ============================================================
# Budget Alert Check (called after expense is logged)
# ============================================================

def format_budget_alert(category: str, spent: Decimal, limit: Decimal, currency: str) -> str:
    """Format a budget alert message"""
    utilization = float(spent / limit * 100) if limit > 0 else 0
    category_str = category.replace('_', ' ').title()
    
    if utilization >= 100:
        return (
            f"\u26a0\ufe0f *Budget Exceeded!*\n\n"
            f"Your {category_str} budget of {currency} {limit:,.0f} has been exceeded.\n"
            f"Spent: {currency} {spent:,.0f} ({utilization:.0f}%)"
        )
    elif utilization >= 80:
        return (
            f"\ud83d\udfe1 *Budget Alert!*\n\n"
            f"You've used {utilization:.0f}% of your {category_str} budget.\n"
            f"Spent: {currency} {spent:,.0f} / {limit:,.0f}\n"
            f"Remaining: {currency} {float(limit - spent):,.0f}"
        )
    return ""
