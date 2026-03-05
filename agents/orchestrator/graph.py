"""
ExpenseWise - Orchestrator Agent (LangGraph)

The main AI brain of ExpenseWise.
Receives all WhatsApp messages and routes them to the appropriate sub-agent.

Flow:
  Message In -> Intent Detection -> Route to Sub-Agent -> Format Response -> Message Out

Sub-Agents:
  - Expense Logging Agent   (add_expense)
  - Categorization Agent    (categorize)
  - Insight Agent           (get_insights)
  - Budget Agent            (budget)
  - Storage Agent           (save/retrieve)
"""

import json
from typing import Optional, Literal
from datetime import datetime

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger

from api.config import settings
from api.models.expense import AgentState, AgentIntent, WhatsAppMessage
from agents.logging_agent.agent import logging_agent_node
from agents.categorization_agent.agent import categorization_agent_node
from agents.insight_agent.agent import insight_agent_node
from agents.budget_agent.agent import budget_agent_node
from agents.storage_agent.agent import storage_agent_node


# ============================================================
# LLM Setup
# ============================================================

def get_llm() -> ChatBedrock:
    """Get AWS Bedrock Claude LLM"""
    return ChatBedrock(
        model_id=settings.bedrock_model_id,
        model_kwargs={
            "max_tokens": settings.bedrock_max_tokens,
            "temperature": settings.bedrock_temperature,
        },
        region_name=settings.aws_region,
    )


# ============================================================
# Intent Detection
# ============================================================

INTENT_DETECTION_PROMPT = """
You are an intelligent expense tracking assistant for ExpenseWise.
Analyze the user's WhatsApp message and classify it into ONE of these intents:

- log_expense: User wants to record an expense ("spent 200 on food", "paid 500 for uber", "bought groceries for 350")
- query_expenses: User wants to see past expenses ("show my expenses", "what did I spend yesterday")
- get_summary: User wants a summary ("today's summary", "weekly report", "how much did I spend this month")
- set_budget: User wants to set a budget ("set food budget to 5000", "monthly budget 20000")
- check_budget: User wants to check budget status ("how's my budget", "how much budget is left")
- start_event: User wants to start tracking a trip/event ("start goa trip", "begin project expenses")
- end_event: User wants to end tracking an event ("end goa trip", "close project expenses")
- get_insights: User wants AI insights ("analyze my spending", "where am I spending too much", "insights")
- help: User needs help or is new ("help", "what can you do", "how do I use this")
- unknown: Cannot determine intent

User message: {message}

Respond with JSON only:
{{
  "intent": "<intent_value>",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief reason>"
}}
"""


async def detect_intent(state: AgentState) -> AgentState:
    """Node: Detect user intent from message"""
    try:
        llm = get_llm()
        prompt = INTENT_DETECTION_PROMPT.format(message=state.user_message)
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = json.loads(response.content.strip())
        
        intent_str = result.get("intent", "unknown")
        state.intent = AgentIntent(intent_str)
        state.metadata["intent_confidence"] = result.get("confidence", 0.0)
        
        logger.info(f"Intent detected for {state.user_phone}: {state.intent} (confidence: {result.get('confidence')})")
        
    except json.JSONDecodeError:
        logger.warning(f"Could not parse intent JSON for {state.user_phone}")
        state.intent = AgentIntent.UNKNOWN
    except Exception as e:
        logger.error(f"Intent detection failed: {e}")
        state.intent = AgentIntent.UNKNOWN
    
    return state


# ============================================================
# Router
# ============================================================

def route_intent(state: AgentState) -> Literal[
    "logging", "insight", "budget", "query", "help", "event", "end"
]:
    """Route to appropriate sub-agent based on intent"""
    intent = state.intent
    
    if intent in [AgentIntent.LOG_EXPENSE]:
        return "logging"
    elif intent in [AgentIntent.GET_INSIGHTS, AgentIntent.GET_SUMMARY, AgentIntent.QUERY_EXPENSES]:
        return "insight"
    elif intent in [AgentIntent.SET_BUDGET, AgentIntent.CHECK_BUDGET]:
        return "budget"
    elif intent in [AgentIntent.START_EVENT, AgentIntent.END_EVENT]:
        return "event"
    elif intent in [AgentIntent.HELP, AgentIntent.UNKNOWN]:
        return "help"
    else:
        return "help"


# ============================================================
# Help Node
# ============================================================

HELP_MESSAGE = """*Welcome to ExpenseWise!* 💸

Here's what you can do:

*Log Expenses:*
- "Spent 250 on lunch"
- "Paid 1200 for groceries"
- "Uber 350 to airport"

*Get Reports:*
- "Today's summary"
- "Weekly report"
- "Show this month's spending"

*Budget:*
- "Set food budget 5000"
- "Check my budget"

*Events/Trips:*
- "Start Goa trip"
- "End Goa trip"

*Insights:*
- "Analyze my spending"
- "Where am I overspending?"

Type anything to get started! 🚀"""


async def help_node(state: AgentState) -> AgentState:
    """Node: Return help message"""
    state.response = HELP_MESSAGE
    return state


# ============================================================
# Event Node (stub - routes to logging agent with event context)
# ============================================================

async def event_node(state: AgentState) -> AgentState:
    """Node: Handle event/trip start and end"""
    try:
        llm = get_llm()
        intent = state.intent
        
        if intent == AgentIntent.START_EVENT:
            # Extract event name
            prompt = f"Extract the event/trip name from this message. Return just the name: '{state.user_message}'"
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            event_name = response.content.strip().strip('"').strip("'")
            
            state.response = (
                f"*{event_name}* session started! 🎉\n\n"
                f"All your expenses will now be tagged to *{event_name}*.\n"
                f"Send expenses as usual. Type 'End {event_name}' when done."
            )
            state.metadata["active_event"] = event_name
            
        elif intent == AgentIntent.END_EVENT:
            state.response = (
                "Event session ended! 🏁\n\n"
                "Generating expense summary for this session...\n"
                "Type 'summary for [event name]' to see the full breakdown."
            )
            state.metadata["active_event"] = None
            
    except Exception as e:
        logger.error(f"Event node error: {e}")
        state.response = "Could not process event. Please try again."
    
    return state


# ============================================================
# Build LangGraph
# ============================================================

def build_graph() -> StateGraph:
    """Build the ExpenseWise LangGraph agent graph"""
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("detect_intent", detect_intent)
    workflow.add_node("logging", logging_agent_node)
    workflow.add_node("categorize", categorization_agent_node)
    workflow.add_node("insight", insight_agent_node)
    workflow.add_node("budget", budget_agent_node)
    workflow.add_node("storage", storage_agent_node)
    workflow.add_node("event", event_node)
    workflow.add_node("help", help_node)
    
    # Set entry point
    workflow.set_entry_point("detect_intent")
    
    # Route after intent detection
    workflow.add_conditional_edges(
        "detect_intent",
        route_intent,
        {
            "logging": "logging",
            "insight": "insight",
            "budget": "budget",
            "query": "insight",
            "event": "event",
            "help": "help",
            "end": END,
        }
    )
    
    # After logging -> categorize -> storage -> END
    workflow.add_edge("logging", "categorize")
    workflow.add_edge("categorize", "storage")
    workflow.add_edge("storage", END)
    
    # Other agents go directly to END
    workflow.add_edge("insight", END)
    workflow.add_edge("budget", END)
    workflow.add_edge("event", END)
    workflow.add_edge("help", END)
    
    return workflow


# Compile graph with memory checkpointing
_graph = None


def get_graph():
    """Get compiled graph (singleton)"""
    global _graph
    if _graph is None:
        workflow = build_graph()
        memory = MemorySaver()
        _graph = workflow.compile(checkpointer=memory)
    return _graph


# ============================================================
# Main Entry Point
# ============================================================

async def run_agent(
    user_phone: str,
    message: WhatsAppMessage,
) -> Optional[str]:
    """
    Main function called by the webhook.
    Runs the full LangGraph agent pipeline.
    
    Args:
        user_phone: User's WhatsApp number
        message: Parsed WhatsApp message
    
    Returns:
        Response string to send back to user
    """
    try:
        graph = get_graph()
        
        # Build initial state
        initial_state = AgentState(
            user_phone=user_phone,
            user_message=message.body or "",
            metadata={
                "media_url": message.media_url,
                "media_type": message.media_type,
                "message_id": message.message_id,
                "timestamp": message.timestamp.isoformat(),
            }
        )
        
        # Use phone number as thread ID for memory continuity
        config = {"configurable": {"thread_id": user_phone}}
        
        # Run the graph
        final_state = await graph.ainvoke(initial_state.dict(), config=config)
        
        return final_state.get("response") or "I'm not sure how to help with that. Type *help* for options."
        
    except Exception as e:
        logger.error(f"Agent pipeline error for {user_phone}: {e}")
        return "Sorry, I ran into an error. Please try again shortly."
