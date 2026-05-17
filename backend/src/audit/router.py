"""Audit Post-Call Hook — AI Policy v1.0
LiteLLM success_callback calls POST /audit/post-call after every successful request.
Writes to audit_logs with classification from request metadata.
"""

import os
import uuid
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

import asyncpg

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "")
USD_TO_THB = float(os.getenv("USD_TO_THB", "35.0"))
LITELLM_CALLBACK_SECRET = os.getenv("LITELLM_CALLBACK_SECRET", "")


async def _get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(DATABASE_URL)


class LiteLLMCallbackPayload(BaseModel):
    """Subset of LiteLLM webhook payload fields we care about.

    LiteLLM v1.82.6 webhook POST body key names:
      - model, user, usage  (top-level)
      - standard_logging_object  (NOT standard_logging_payload — that was incorrect)
      - litellm_params.metadata  carries classifier/guardrail metadata
    We accept both old and new field names for forward-compat.
    """
    model: str | None = None
    user: str | None = None
    usage: dict | None = None          # {prompt_tokens, completion_tokens, total_tokens}
    # LiteLLM sends this as "standard_logging_object" (v1.x); accept both names
    standard_logging_object: dict | None = None
    standard_logging_payload: dict | None = None  # kept for direct-call compat
    metadata: dict | None = None       # carries classification, action from guardrails
    litellm_params: dict | None = None # nested; metadata lives here in webhook payloads
    response_cost: float | None = None # some versions send cost at top level


@router.post("/post-call", status_code=204)
async def post_call_hook(
    payload: LiteLLMCallbackPayload,
    x_callback_secret: str | None = Header(default=None, alias="x-callback-secret"),
) -> None:
    """Persist audit log entry from LiteLLM success/failure callback."""
    if LITELLM_CALLBACK_SECRET and x_callback_secret != LITELLM_CALLBACK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    usage = payload.usage or {}
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    # Cost estimate — check multiple locations depending on LiteLLM version:
    # v1.82.6 webhook: response_cost at top level
    # standard_logging_object (webhook) or standard_logging_payload (direct call)
    slp = payload.standard_logging_object or payload.standard_logging_payload or {}
    if payload.response_cost is not None:
        cost_usd = float(payload.response_cost)
    else:
        cost_usd = float(slp.get("response_cost", 0))
    cost_thb = cost_usd * USD_TO_THB

    # Metadata resolution: LiteLLM webhook puts metadata inside litellm_params;
    # direct POST to /audit/post-call sends metadata at top level.
    litellm_params = payload.litellm_params or {}
    metadata = payload.metadata or litellm_params.get("metadata") or {}
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
