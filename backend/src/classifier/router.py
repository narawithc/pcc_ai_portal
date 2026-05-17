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
    messages: list[dict]
    model: str
    user: str | None = None


class ClassifierResponse(BaseModel):
    success: bool
    action: str           # "allow" | "warn" | "block"
    classification: str   # "public" | "internal" | "confidential" | "top_secret"
    reasons: list[str]
    message: str | None = None


def _extract_text(messages: list[dict]) -> str:
    parts = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
    return " ".join(parts)


@router.post("/check", response_model=ClassifierResponse)
async def classifier_check(req: ClassifierRequest) -> ClassifierResponse:
    text = _extract_text(req.messages)
    tier, reasons = classify(text)

    if tier == "top_secret":
        # Auto-create incident asynchronously (fire-and-forget via httpx)
        await _auto_incident(
            user=req.user,
            title=f"Top Secret data detected in AI prompt (model: {req.model})",
            description=f"Classifier blocked prompt. Reasons: {reasons}. User: {req.user}",
        )
        return ClassifierResponse(
            success=False,
            action="block",
            classification=tier,
            reasons=reasons,
            message=(
                "ระบบตรวจพบสัญญาณข้อมูลระดับ Top Secret ในข้อความของคุณ\n"
                "ห้ามส่งข้อมูลประเภทนี้เข้า AI ภายนอก (ตาม AI Policy Section 4)\n"
                "ถ้าต้องการใช้กับข้อมูล Top Secret ให้ใช้ Local Ollama เท่านั้น"
            ),
        )

    if tier == "confidential":
        return ClassifierResponse(
            success=True,
            action="warn",
            classification=tier,
            reasons=reasons,
            message=(
                "ข้อความนี้อาจมีข้อมูลระดับ Confidential\n"
                "ตรวจสอบว่าคุณใช้ Enterprise AI Portal (ai.precise.co.th) เท่านั้น\n"
                "ผลลัพธ์นี้ถูกบันทึกในระบบ audit log"
            ),
        )

    return ClassifierResponse(
        success=True,
        action="allow",
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
