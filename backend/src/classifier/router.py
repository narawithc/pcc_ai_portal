"""Data Classifier Guardrail — AI Policy v1.0 Section 4
LiteLLM calls this as pre_call guardrail (after thai-pii-detector).

Top Secret → block (400) + auto-create incident.
Confidential → warn (allow but flag in response).
Internal / Public → allow.
"""

import os
from fastapi import APIRouter
from pydantic import BaseModel

from src.classifier.rules import classify

router = APIRouter()

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")


class ClassifierRequest(BaseModel):
    messages: list[dict] | None = None
    structured_messages: list[dict] | None = None
    texts: list[str] | None = None
    model: str | None = None
    user: str | None = None


class ClassifierResponse(BaseModel):
    # LiteLLM generic_guardrail_api format
    action: str           # "ALLOW" | "BLOCK"
    blocked_reason: str | None = None
    # extra fields for audit/logging
    classification: str = "internal"
    reasons: list[str] = []


def _extract_text(req: "ClassifierRequest") -> str:
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


@router.post("/check", response_model=ClassifierResponse)
@router.post("/beta/litellm_basic_guardrail_api", response_model=ClassifierResponse)
async def classifier_check(req: ClassifierRequest) -> ClassifierResponse:
    text = _extract_text(req)
    tier, reasons = classify(text)

    if tier == "top_secret":
        await _auto_incident(
            user=req.user,
            title=f"Top Secret data detected in AI prompt (model: {req.model})",
            description=f"Classifier blocked prompt. Reasons: {reasons}. User: {req.user}",
        )
        return ClassifierResponse(
            action="BLOCKED",
            blocked_reason=(
                "ระบบตรวจพบสัญญาณข้อมูลระดับ Top Secret ในข้อความของคุณ "
                "ห้ามส่งข้อมูลประเภทนี้เข้า AI ภายนอก (ตาม AI Policy Section 4) "
                "ถ้าต้องการใช้กับข้อมูล Top Secret ให้ใช้ Local Ollama เท่านั้น"
            ),
            classification=tier,
            reasons=reasons,
        )

    # confidential: allow but log (audit_logs.classification = confidential)
    return ClassifierResponse(
        action="ALLOWED",
        classification=tier,
        reasons=reasons,
    )


async def _auto_incident(user: str | None, title: str, description: str) -> None:
    try:
        import httpx
        async with httpx.AsyncClient(base_url=BACKEND_BASE_URL, timeout=5.0) as client:
            await client.post(
                "/incidents/internal",
                json={
                    "category": "misuse",
                    "severity": "high",
                    "title": title,
                    "description": description,
                    "reporter_email": user,
                },
            )
    except Exception:
        pass  # don't block the guardrail if incident creation fails
