"""Data Classification Rules — AI Policy v1.0 Section 4

Tier hierarchy (escalate up, never down):
  public → internal → confidential → top_secret

Default: internal (anything not matching public criteria).
"""

import re

# ── Reuse PII patterns from pdpa module ──────────────────────────
# Import here to keep a single source of truth
from src.pdpa.router import _PATTERNS as _PII_PATTERNS

# ── Top Secret patterns (block immediately) ──────────────────────
_TOP_SECRET_KEYWORDS = re.compile(
    r"\b("
    r"ลับสุด|top[\s-]?secret|highly[\s-]?confidential"
    r"|M&A|merger[\s&]+acquisition|acquisition[\s-]?target|takeover[\s-]?bid"
    r"|salary[\s-]?list|payroll[\s-]?data|compensation[\s-]?structure"
    r"|executive[\s-]?compensation|บัญชีเงินเดือน"
    r")\b",
    re.IGNORECASE,
)

_TOP_SECRET_PATTERNS = {
    "api_key_secret": re.compile(
        r"(api[_-]?key|secret[_-]?key|access[_-]?token|private[_-]?key)\s*[:=]\s*\S{8,}"
        , re.IGNORECASE
    ),
    "password_field": re.compile(
        r"(password|passwd|pwd)\s*[:=]\s*\S{6,}", re.IGNORECASE
    ),
    "aws_secret": re.compile(r"\b[A-Za-z0-9/+=]{40}\b"),  # AWS secret key shape
}

# ── Confidential patterns (warn + restrict) ───────────────────────
_CONFIDENTIAL_KEYWORDS = re.compile(
    r"\b("
    r"สัญญา|contract[\s-]?no|purchase[\s-]?order|ใบเสนอราคา|quotation"
    r"|ลูกค้า[\s\S]{0,20}(?:บาท|THB|USD)|customer[\s\S]{0,20}(?:฿|\$|million|billion)"
    r"|งบประมาณ|budget[\s-]?(?:q[1-4]|fy|annual|รายปี)"
    r"|กำไร|ขาดทุน|profit|revenue|ebitda|margin"
    r"|ข้อมูลลับ|confidential|นโยบายภายใน"
    r")\b",
    re.IGNORECASE,
)

_CONTRACT_NUMBER = re.compile(r"\b[A-Z]{2,4}-\d{4,8}\b")  # e.g. PCC-20240001

# ── Public heuristic (short, no sensitive signal) ────────────────
_PUBLIC_MAX_CHARS = 80


def classify(text: str) -> tuple[str, list[str]]:
    """Return (classification_tier, reasons[]).

    Tiers: 'public' | 'internal' | 'confidential' | 'top_secret'
    """
    reasons: list[str] = []

    # 1. Top Secret — block triggers
    if _TOP_SECRET_KEYWORDS.search(text):
        m = _TOP_SECRET_KEYWORDS.search(text)
        reasons.append(f"top_secret_keyword: {m.group()[:30]}")  # type: ignore[union-attr]
        return "top_secret", reasons

    for name, pat in _TOP_SECRET_PATTERNS.items():
        if pat.search(text):
            reasons.append(f"top_secret_pattern: {name}")
            return "top_secret", reasons

    # 2. Confidential — PII or sensitive business data
    for pii_name, pat in _PII_PATTERNS.items():
        if pat.search(text):
            reasons.append(f"pii_detected: {pii_name}")
            # national_id is already blocked by PII guardrail,
            # but still flag as confidential for audit
            if "confidential" not in reasons:
                reasons.insert(0, "confidential_pii")
            return "confidential", reasons

    if _CONFIDENTIAL_KEYWORDS.search(text):
        m = _CONFIDENTIAL_KEYWORDS.search(text)
        reasons.append(f"confidential_keyword: {m.group()[:30]}")  # type: ignore[union-attr]
        return "confidential", reasons

    if _CONTRACT_NUMBER.search(text):
        reasons.append("contract_number_detected")
        return "confidential", reasons

    # 3. Public — very short, no signal
    if len(text.strip()) <= _PUBLIC_MAX_CHARS:
        return "public", ["short_prompt_no_signal"]

    # 4. Default: internal
    return "internal", []
