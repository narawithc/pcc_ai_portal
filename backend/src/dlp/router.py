from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel

from src.classifier.rules import classify
from src.pdpa.router import _PATTERNS, _ACTIONS, _persist_pii_event
from src.dlp.extractor import extract_text

router = APIRouter()


class DLPScanResult(BaseModel):
    action: str
    classification: str
    pii_detected: list[str]
    reasons: list[str]
    filename: str


@router.post("/scan-file", response_model=DLPScanResult)
async def scan_file(file: UploadFile) -> DLPScanResult:
    content = await file.read()

    try:
        text = extract_text(file.filename or "", content)
    except ValueError as e:
        raise HTTPException(status_code=415, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract file content: {e}")

    classification, reasons = classify(text)

    pii_detected: list[str] = []
    should_block = False

    for pii_type, pattern in _PATTERNS.items():
        if pattern.search(text):
            pii_detected.append(pii_type)
            if _ACTIONS.get(pii_type) == "blocked":
                should_block = True

    if classification == "top_secret":
        should_block = True

    if pii_detected:
        await _persist_pii_event(
            user_email=None,
            pii_types=pii_detected,
            action="blocked" if should_block else "warned",
        )

    action = "BLOCK" if should_block else "ALLOW"

    return DLPScanResult(
        action=action,
        classification=classification,
        pii_detected=pii_detected,
        reasons=reasons,
        filename=file.filename or "",
    )
