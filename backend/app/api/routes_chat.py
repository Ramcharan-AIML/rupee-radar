"""`POST /api/chat` — conversational grounded chat endpoint.
"""

from __future__ import annotations

import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.analyst.chat import interact
from app.store.db import get_db_conn

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    used_tools: list[str]


class ChatMessage(BaseModel):
    role: str
    content: str


@router.get("/chat/{session_id}", response_model=list[ChatMessage])
def get_chat_history(session_id: str) -> list[ChatMessage]:
    """Retrieve the conversation history for a given analysis session."""
    with get_db_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()

        return [ChatMessage(role=r["role"], content=r["content"]) for r in rows]


@router.post("/chat", response_model=ChatResponse)
def post_chat_message(req: ChatRequest) -> ChatResponse:
    """Post a new message and get a grounded response from the analyst buddy."""
    # 1. Fetch current history
    history = []
    with get_db_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY id ASC",
            (req.session_id,),
        ).fetchall()
        history = [{"role": r["role"], "content": r["content"]} for r in rows]

    # 2. Call chat orchestrator
    result = interact(req.session_id, req.message, history)

    # 3. Save new messages (user and assistant) to history
    created_at = str(time.time())
    with get_db_conn() as conn:
        conn.execute(
            """
            INSERT INTO chat_history (session_id, role, content, created_at)
            VALUES (?, 'user', ?, ?)
            """,
            (req.session_id, req.message, created_at),
        )
        conn.execute(
            """
            INSERT INTO chat_history (session_id, role, content, created_at)
            VALUES (?, 'assistant', ?, ?)
            """,
            (req.session_id, result["answer"], created_at),
        )

    return ChatResponse(answer=result["answer"], used_tools=result["used_tools"])
