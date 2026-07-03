"""[11] Conversational Chat Orchestration.

Uses code-driven ReAct/tool-use prompts to select query tools,
runs them over SQLite database, and formulates grounded answers.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.config import get_settings
from app.analyst import tools

if TYPE_CHECKING:
    from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


def interact(
    session_id: str,
    message: str,
    history: list[dict[str, str]],
) -> dict[str, any]:
    """Orchestrate the chat session.

    1. Select query tool.
    2. Execute tool query.
    3. Generate final answer.
    """
    settings = get_settings()

    if not settings.llm_enabled or not settings.llm_enable_chat:
        return {
            "answer": "I'm currently offline. Please configure your LLM provider api key to enable chat.",
            "used_tools": [],
            "tokens_spent": 0,
        }

    # Resolve LLM provider
    from app.llm.factory import get_llm_provider
    provider = get_llm_provider()
    if provider is None:
        return {
            "answer": "LLM provider is unavailable. Please check settings.",
            "used_tools": [],
            "tokens_spent": 0,
        }

    # 1. Step: Tool Selection
    selected_tool = "none"
    args = {}
    tool_output = ""

    system_tool_prompt = (
        "You are an API orchestrator. Based on the user's question and history, you must choose exactly "
        "ONE tool to call to retrieve the necessary financial data from the database, or choose \"none\" "
        "if the question can be answered directly.\n\n"
        "Available Tools:\n"
        "- get_metrics: Get overall metrics (totals, savings rate). Use for high-level summaries.\n"
        "- get_category_breakdown: Spending grouped by category. Use for category distribution queries.\n"
        "- get_recurring: Subscriptions, EMIs, rent, and SIPs.\n"
        "- get_top_transactions: Get the top largest debit transactions.\n"
        "- search_transactions: Search raw merchant descriptions or categories for matching strings. "
        "Arguments: {\"query\": \"keyword\"}. Use when the user asks about specific companies, places, or transactions.\n\n"
        "You MUST respond in JSON exactly matching this format:\n"
        '{\n  "tool": "tool_name",\n  "arguments": {"arg_name": "arg_value"}\n}\n'
        'If no tool is needed, respond with:\n'
        '{\n  "tool": "none",\n  "arguments": {}\n}\n'
        "Only return the JSON. No explanations."
    )

    history_str = "\n".join(f"{h['role'].upper()}: {h['content']}" for h in history[-6:])
    user_prompt = f"History:\n{history_str}\n\nUser Question: {message}"

    try:
        raw_select = provider.complete(user_prompt, system_prompt=system_tool_prompt)
        parsed_select = json.loads(_clean_json_text(raw_select))
        selected_tool = parsed_select.get("tool", "none")
        args = parsed_select.get("arguments", {})
    except Exception as err:
        logger.warning("Tool selection prompt failed, falling back to 'none': %s", err)
        selected_tool = "none"

    # 2. Step: Run Tool
    used_tools = []
    if selected_tool != "none":
        try:
            if selected_tool == "get_metrics":
                tool_output = tools.get_metrics(session_id)
                used_tools.append("get_metrics")
            elif selected_tool == "get_category_breakdown":
                tool_output = tools.get_category_breakdown(session_id)
                used_tools.append("get_category_breakdown")
            elif selected_tool == "get_recurring":
                tool_output = tools.get_recurring(session_id)
                used_tools.append("get_recurring")
            elif selected_tool == "get_top_transactions":
                limit = int(args.get("limit", 5))
                tool_output = tools.get_top_transactions(session_id, limit)
                used_tools.append(f"get_top_transactions(limit={limit})")
            elif selected_tool == "search_transactions":
                query = str(args.get("query", ""))
                if query:
                    tool_output = tools.search_transactions(session_id, query)
                    used_tools.append(f"search_transactions(query='{query}')")
                else:
                    tool_output = "No search query provided."
        except Exception as err:
            logger.error("Tool execution failed: %s", err)
            tool_output = f"Error querying database: {err}"

    # 3. Step: Generate Final Answer
    system_answer_prompt = (
        "You are RupeeRadar, a helpful personal finance analyst buddy. "
        "Answer the user's question using the provided context from the user's bank statement.\n"
        "Rules:\n"
        "- All numerical facts, dates, and amounts MUST be strictly grounded in the context.\n"
        "- Do NOT perform any math calculations. Rely on what is written.\n"
        "- If the context doesn't contain the information, tell the user clearly.\n"
        "- Keep the tone professional, friendly, and concise."
    )

    answer_prompt = (
        f"Context from database:\n{tool_output}\n\n"
        f"User Question: {message}"
    )

    # Compile the final chat messages (with past capped history)
    chat_messages = [{"role": "system", "content": system_answer_prompt}]
    for h in history[-6:]:
        chat_messages.append({"role": h["role"], "content": h["content"]})
    chat_messages.append({"role": "user", "content": answer_prompt})

    try:
        final_answer = provider.chat(chat_messages)
    except Exception as err:
        logger.error("Final chat response generation failed: %s", err)
        final_answer = "I'm sorry, I encountered an error while processing your request."

    return {
        "answer": final_answer,
        "used_tools": used_tools,
        "tokens_spent": 0,  # recorded internally post-calls in provider.py
    }


def _clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
