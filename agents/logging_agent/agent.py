"""
ExpenseWise - Expense Logging Agent

Parses user messages (text, images, voice) to extract expense details.
Supports:
- Free text: "spent 450 on lunch at Truffles"
- Receipt images (via OCR)
- Voice notes (via transcription)
"""

import json
import re
from decimal import Decimal
from typing import Optional
from datetime import datetime

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from loguru import logger

from api.config import settings
from api.models.expense import AgentState, ExpenseCreate, ExpenseCategory


# ============================================================
# Expense Extraction Prompt
# ============================================================

EXPENSE_EXTRACTION_PROMPT = """
You are an expense parsing expert. Extract expense details from the user's message.

User message: "{message}"
Current date: {current_date}
User's default currency: {currency}

Extract and return JSON with these fields:
{{
  "amount": <number, required>,
  "currency": "<3-letter code, default INR>",
  "description": "<what was bought/paid for>",
  "merchant": "<merchant/shop name if mentioned, else null>",
  "category": "<one of: food, transport, shopping, entertainment, health, utilities, rent, salary, investment, travel, education, personal_care, gifts, other>",
  "tags": ["<relevant tags>"],
  "confidence": <0.0-1.0>,
  "needs_clarification": <true/false>,
  "clarification_question": "<ask user if something is unclear, else null>"
}}

Examples:
- "spent 450 on lunch" -> amount: 450, description: "lunch", category: "food"
- "uber to airport 850" -> amount: 850, description: "uber to airport", category: "transport", merchant: "Uber"
- "grocery shopping at DMart 2300" -> amount: 2300, merchant: "DMart", category: "shopping"
- "paid electricity bill 1500" -> amount: 1500, category: "utilities"

If amount is unclear, set needs_clarification: true.
Respond with valid JSON only.
"""


# ============================================================
# Text-Based Expense Parser
# ============================================================

async def parse_expense_from_text(
    message: str,
    user_phone: str,
    currency: str = "INR",
) -> Optional[ExpenseCreate]:
    """Use Claude to extract expense details from free text"""
    try:
        from langchain_aws import ChatBedrock
        llm = ChatBedrock(
            model_id=settings.bedrock_model_id,
            model_kwargs={"max_tokens": 1024, "temperature": 0.0},
            region_name=settings.aws_region,
        )
        
        prompt = EXPENSE_EXTRACTION_PROMPT.format(
            message=message,
            current_date=datetime.now().strftime("%Y-%m-%d"),
            currency=currency,
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        data = json.loads(response.content.strip())
        
        if data.get("amount") and float(data["amount"]) > 0:
            # Map category string to enum
            try:
                category = ExpenseCategory(data.get("category", "other"))
            except ValueError:
                category = ExpenseCategory.OTHER
            
            return ExpenseCreate(
                amount=Decimal(str(data["amount"])),
                currency=data.get("currency", currency),
                description=data.get("description", message[:200]),
                merchant=data.get("merchant"),
                category=category,
                tags=data.get("tags", []),
                raw_input=message,
            ), data.get("needs_clarification", False), data.get("clarification_question")
        
        return None, True, "I couldn't find an amount in your message. How much did you spend?"
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in expense extraction: {e}")
        return None, True, "Sorry, I had trouble understanding that. Could you say it differently? e.g. 'Spent 500 on lunch'"
    except Exception as e:
        logger.error(f"Expense parsing error: {e}")
        return None, True, "I had trouble parsing that. Please try: 'Spent [amount] on [description]'"


# ============================================================
# Receipt OCR Parser (AWS Textract)
# ============================================================

async def parse_expense_from_receipt(
    image_url: str,
    user_phone: str,
) -> Optional[ExpenseCreate]:
    """Extract expense from receipt image using AWS Textract + Claude"""
    try:
        import boto3
        import httpx
        
        # Download image
        async with httpx.AsyncClient() as client:
            img_response = await client.get(image_url)
            image_bytes = img_response.content
        
        # Run AWS Textract
        textract = boto3.client("textract", region_name=settings.aws_region)
        textract_response = textract.detect_document_text(
            Document={"Bytes": image_bytes}
        )
        
        # Extract text blocks
        text_blocks = [
            block["Text"]
            for block in textract_response["Blocks"]
            if block["BlockType"] == "LINE"
        ]
        extracted_text = "\n".join(text_blocks)
        
        logger.info(f"OCR extracted {len(text_blocks)} lines from receipt")
        
        # Use Claude to parse the OCR text
        if extracted_text:
            expense, needs_clarification, question = await parse_expense_from_text(
                f"Receipt text:\n{extracted_text}",
                user_phone,
            )
            return expense, needs_clarification, question
        
        return None, True, "I couldn't read your receipt clearly. Could you type the amount manually?"
        
    except Exception as e:
        logger.error(f"Receipt OCR error: {e}")
        return None, True, "I had trouble reading that receipt. Could you type the expense manually?"


# ============================================================
# Confirmation Message Formatter
# ============================================================

def format_expense_confirmation(expense: ExpenseCreate) -> str:
    """Format a confirmation message to show user what was logged"""
    emoji_map = {
        "food": "\ud83c\udf74",
        "transport": "\ud83d\ude97",
        "shopping": "\ud83d\udecd️",
        "entertainment": "\ud83c\udfac",
        "health": "\ud83c\udfe5",
        "utilities": "\ud83d\udca1",
        "rent": "\ud83c\udfe0",
        "salary": "\ud83d\udcb0",
        "investment": "\ud83d\udcc8",
        "travel": "\u2708️",
        "education": "\ud83d\udcda",
        "personal_care": "\ud83d\udc84",
        "gifts": "\ud83c\udf81",
        "other": "\ud83d\udcb8",
    }
    
    category_val = expense.category.value if expense.category else "other"
    emoji = emoji_map.get(category_val, "\ud83d\udcb8")
    merchant_str = f" @ {expense.merchant}" if expense.merchant else ""
    
    return (
        f"{emoji} *Expense Logged!*\n\n"
        f"*Amount:* {expense.currency} {expense.amount:,.0f}\n"
        f"*Description:* {expense.description}{merchant_str}\n"
        f"*Category:* {category_val.replace('_', ' ').title()}\n"
        f"\nSaved to your storage. Type 'summary' to see today's total."
    )


# ============================================================
# LangGraph Node
# ============================================================

async def logging_agent_node(state: AgentState) -> AgentState:
    """
    LangGraph node for expense logging.
    Handles both text and image (receipt) inputs.
    """
    try:
        media_type = state.metadata.get("media_type")
        media_url = state.metadata.get("media_url")
        
        # Route to appropriate parser
        if media_type == "image" and media_url:
            logger.info(f"Processing receipt image for {state.user_phone}")
            expense, needs_clarification, question = await parse_expense_from_receipt(
                media_url, state.user_phone
            )
        else:
            logger.info(f"Processing text expense for {state.user_phone}")
            expense, needs_clarification, question = await parse_expense_from_text(
                state.user_message, state.user_phone
            )
        
        if needs_clarification or not expense:
            state.requires_clarification = True
            state.clarification_question = question
            state.response = question
            return state
        
        # Store extracted expense in state
        state.extracted_expense = expense
        
        # Format confirmation message
        state.response = format_expense_confirmation(expense)
        
        logger.info(f"Expense parsed for {state.user_phone}: {expense.amount} {expense.currency} - {expense.description}")
        
    except Exception as e:
        logger.error(f"Logging agent error for {state.user_phone}: {e}")
        state.response = "I had trouble logging that expense. Please try: 'Spent [amount] on [description]'"
    
    return state
