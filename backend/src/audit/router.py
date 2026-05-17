"""Audit Post-Call Hook — AI Policy v1.0
LiteLLM success_callback calls POST /audit/post-call after every successful request.
Writes to audit_logs with classification from request metadata.
"""

import os
import uuid
from fastapi import APIRouter
from pydantic import BaseModel

import asyncpg

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "")
USD_TO_THB = float(os.getenv("USD_TO_THB", "35.0"))


async def _get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(DATABASE_URL)


class LiteLLMCallbackPayload(BaseModel):
    """Subset of LiteLLM webhook payload fields we care about."""
    model: str | None = None
    user: str | None = None
    usage: dict | None = None          # {prompt_tokens, completion_tokens, total_tokens}
    standard_logging_payload: dict | None = None
    metadata: dict | None = None       # carries classification, action from guardrails


@router.post("/post-call", status_code=204)
async def post_call_hook(payload: LiteLLMCallbackPayload) -> None:
    """Persist audit log entry from LiteLLM success/failure callback."""
    usage = payload.usage or {}
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    # Cost estimate — fallback to 0 if not provided
    slp = payload.standard_logging_payload or {}
    cost_usd = float(slp.get("response_cost", 0))
    cost_thb = cost_usd * USD_TO_THB

    metadata = payload.metadata or {}
    classification = metadata.get("classification")   # set by classifier guardrail
    action = metadata.get("guardrail_action", "allowed")
    pii_detected = bool(metadata.get("pii_detected", False))
    model = payload.model or "unknown"
    user_email = payload.user

    conn = await _get_conn()
    try:
        user_id = None
        if user_email:
            row = await conn.fetchrow("SELECT id FROM users WHERE email = $1", user_email)
            if row:
                user_id = str(row["id"])

        await conn.execute(
            """
            INSERT INTO audit_logs
                (id, user_id, model, input_tokens, output_tokens,
                 cost_usd, cost_thb, pii_detected, classification, tool, action)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            """,
            str(uuid.uuid4()),
            user_id,
            model,
            input_tokens,
            output_tokens,
            cost_usd,
            cost_thb,
            pii_detected,
            classification,
            "ai_portal",
            action,
        )
    finally:
        await conn.close()
