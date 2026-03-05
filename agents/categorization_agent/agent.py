"""
ExpenseWise - Categorization Agent
Re-verifies or overrides category assignment for logged expenses.
"""

import json
from loguru import logger
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage

from api.config import settings
from api.models.expense import AgentState, ExpenseCategory


CATEGORIZATION_PROMPT = """
Verify or improve the expense category assignment.

Expense details:
- Description: {description}
- Merchant: {merchant}
- Current category: {current_category}
- Amount: {currency} {amount}

Categories available:
food, transport, shopping, entertainment, health, utilities, rent,
salary, investment, travel, education, personal_care, gifts, other

Return JSON:
{{
  "category": "<best category>",
  "confidence": <0.0-1.0>,
  "tags": ["<relevant tags>"]
}}

Respond with valid JSON only.
"""


async def categorization_agent_node(state: AgentState) -> AgentState:
    """LangGraph node: Verify/improve expense category"""
    try:
        expense = state.extracted_expense
        if not expense:
            # No expense to categorize - pass through
            return state
        
        llm = ChatBedrock(
            model_id=settings.bedrock_model_id,
            model_kwargs={"max_tokens": 256, "temperature": 0.0},
            region_name=settings.aws_region,
        )
        
        prompt = CATEGORIZATION_PROMPT.format(
            description=expense.description,
            merchant=expense.merchant or "unknown",
            current_category=expense.category.value if expense.category else "other",
            currency=expense.currency,
            amount=float(expense.amount),
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        data = json.loads(response.content.strip())
        
        # Update category if confidence is high
        new_category_str = data.get("category", "other")
        confidence = data.get("confidence", 0.5)
        
        if confidence >= 0.7:
            try:
                state.extracted_expense.category = ExpenseCategory(new_category_str)
            except ValueError:
                pass  # Keep original if mapping fails
        
        # Add tags from categorization
        if data.get("tags"):
            existing_tags = state.extracted_expense.tags or []
            state.extracted_expense.tags = list(set(existing_tags + data["tags"]))
        
        logger.info(f"Category confirmed: {state.extracted_expense.category} (confidence: {confidence})")
        
    except Exception as e:
        logger.error(f"Categorization error: {e}")
        # Non-fatal - continue with original category
    
    return state
