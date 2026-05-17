"""PDPA PII Detector — ภาษาไทย + English
LiteLLM เรียก endpoint นี้ก่อนส่ง request ไป Claude (pre_call guardrail)

PII ที่ detect:
  - เลขบัตรประชาชน 13 หลัก
  - เลขโทรศัพท์ไทย (08x, 09x, 06x)
  - อีเมล
  - เลขบัญชีธนาคาร
  - ชื่อ-นามสกุลภาษาไทย (heuristic: คำขึ้นต้นด้วย นาย/นาง/นางสาว/ดร.)
"""

import os
import re
import uuid
import asyncpg
from fastapi import APIRouter, Header
from pydantic import BaseModel

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "")

# ── PII Patterns ──────────────────────────────────────────────
_PATTERNS = {
    "thai_national_id": re.compile(r"\b[0-9]{13}\b"),
    "thai_phone":       re.compile(r"\b0[689][0-9]{8}\b"),
    "email":            re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
    "bank_account":     re.compile(r"\b[0-9]{10,12}\b"),
    "thai_name_prefix": re.compile(r"(นาย|นาง(?:สาว)?|ดร\.|Mr\.|Mrs\.|Miss)\s+[\u0E00-\u0E7F]+"),
}

# Action ต่อ PII type
_ACTIONS = {
    "thai_national_id": "blocked",   # บล็อกทันที
    "thai_name_prefix": "warned",    # เตือนแต่ไม่บล็อก
    "thai_phone":       "warned",
    "email":            "warned",
    "bank_account":     "warned",
}


class GuardrailRequest(BaseModel):
    """Accepts both old format (messages) and LiteLLM generic_guardrail_api format (structured_messages/texts)."""
    messages: list[dict] | None = None
    structured_messages: list[dict] | None = None
    texts: list[str] | None = None
    model: str | None = None
    user: str | None = None
    metadata: dict | None = None


class GuardrailResponse(BaseModel):
    # LiteLLM generic_guardrail_api format: action must be "ALLOW" or "BLOCK"
    action: str           # "ALLOW" | "BLOCK"
    blocked_reason: str | None = None
    # extra fields for internal use / logging
    pii_detected: list[str] = []


def _extract_text(req: "GuardrailRequest") -> str:
    """รวม content จาก messages หรือ structured_messages หรือ texts"""
    parts: list[str] = []
    sources = req.messages or req.structured_messages or []
    for msg in sources:
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
    if req.texts:
        parts.extend(req.texts)
    return " ".join(parts)


@router.post("/pii-check", response_model=GuardrailResponse)
@router.post("/beta/litellm_basic_guardrail_api", response_model=GuardrailResponse)
async def pii_check(
    req: GuardrailRequest,
    x_user_id: str | None = Header(default=None, alias="x-user-id"),
) -> GuardrailResponse:
    text = _extract_text(req)
    detected: list[str] = []
    should_block = False

    for pii_type, pattern in _PATTERNS.items():
        if pattern.search(text):
            detected.append(pii_type)
            if _ACTIONS.get(pii_type) == "blocked":
                should_block = True

    if not detected:
        return GuardrailResponse(action="ALLOW", pii_detected=[])

    # Resolve user_id from header or request user field
    user_email = req.user or x_user_id
    await _persist_pii_event(
        user_email=user_email,
        pii_types=detected,
        action="blocked" if should_block else "warned",
    )

    if should_block:
        return GuardrailResponse(
            action="BLOCKED",
            blocked_reason="พบข้อมูลส่วนบุคคลที่มีความละเอียดอ่อน (เลขบัตรประชาชน) กรุณาลบออกก่อนส่ง",
            pii_detected=detected,
        )

    return GuardrailResponse(
        action="ALLOWED",
        blocked_reason=None,
        pii_detected=detected,
    )


async def _persist_pii_event(
    user_email: str | None,
    pii_types: list[str],
    action: str,
) -> None:
    if not DATABASE_URL:
        return
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            user_id = None
            if user_email:
                row = await conn.fetchrow("SELECT id FROM users WHERE email = $1", user_email)
                if row:
                    user_id = str(row["id"])
            import json
            await conn.execute(
                """
                INSERT INTO pii_events (id, user_id, pii_types, action)
                VALUES ($1, $2, $3, $4)
                """,
                str(uuid.uuid4()),
                user_id,
                json.dumps(pii_types),
                action,
            )
        finally:
            await conn.close()
    except Exception:
        pass  # don't block guardrail if DB write fails
