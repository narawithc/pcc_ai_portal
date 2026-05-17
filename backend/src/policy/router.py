"""Policy Acceptance — AI Policy v1.0 Section 12

POST /policy/accept          — record user acceptance (any authenticated user)
GET  /policy/status          — check if current user has accepted current version
GET  /policy/text            — serve ai-policy.md as plain text (for TOS modal)
GET  /policy/acceptance-stats — admin: acceptance counts by version
"""

import os
import uuid
from pathlib import Path
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.auth.router import UserInfo, get_current_user
from src.credentials.router import _require_admin

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "")
CURRENT_POLICY_VERSION = os.getenv("POLICY_VERSION", "v1.0")

_POLICY_DOC_PATH = Path(__file__).parent.parent.parent.parent / "docs" / "ai-policy.md"


async def _get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(DATABASE_URL)


class AcceptRequest(BaseModel):
    policy_version: str = CURRENT_POLICY_VERSION


class PolicyStatus(BaseModel):
    accepted: bool
    policy_version: str
    accepted_at: str | None = None
    current_version: str


@router.post("/accept", status_code=201)
async def accept_policy(
    body: AcceptRequest,
    request: Request,
    user: Annotated[UserInfo, Depends(get_current_user)],
) -> dict:
    conn = await _get_conn()
    try:
        user_row = await conn.fetchrow("SELECT id FROM users WHERE email = $1", user.email)
        if not user_row:
            raise HTTPException(status_code=404, detail="User not found in DB")

        client_ip = request.client.host if request.client else None

        await conn.execute(
            """
            INSERT INTO policy_acceptance (id, user_id, policy_version, ip_address)
            VALUES ($1, $2, $3, $4::inet)
            ON CONFLICT (user_id, policy_version) DO NOTHING
            """,
            str(uuid.uuid4()),
            str(user_row["id"]),
            body.policy_version,
            client_ip,
        )
    finally:
        await conn.close()

    return {"accepted": True, "policy_version": body.policy_version, "user": user.email}


@router.get("/status", response_model=PolicyStatus)
async def policy_status(
    user: Annotated[UserInfo, Depends(get_current_user)],
) -> PolicyStatus:
    conn = await _get_conn()
    try:
        user_row = await conn.fetchrow("SELECT id FROM users WHERE email = $1", user.email)
        if not user_row:
            return PolicyStatus(accepted=False, policy_version=CURRENT_POLICY_VERSION,
                                current_version=CURRENT_POLICY_VERSION)

        row = await conn.fetchrow(
            """
            SELECT policy_version, accepted_at FROM policy_acceptance
            WHERE user_id = $1 AND policy_version = $2
            """,
            str(user_row["id"]),
            CURRENT_POLICY_VERSION,
        )
    finally:
        await conn.close()

    if row:
        return PolicyStatus(
            accepted=True,
            policy_version=str(row["policy_version"]),
            accepted_at=str(row["accepted_at"]),
            current_version=CURRENT_POLICY_VERSION,
        )
    return PolicyStatus(accepted=False, policy_version=CURRENT_POLICY_VERSION,
                        current_version=CURRENT_POLICY_VERSION)


@router.get("/text")
async def policy_text() -> dict:
    """Serve ai-policy.md content for TOS modal (Open-WebUI TERMS_OF_SERVICE_URL)."""
    if _POLICY_DOC_PATH.exists():
        return {"version": CURRENT_POLICY_VERSION, "content": _POLICY_DOC_PATH.read_text()}
    return {"version": CURRENT_POLICY_VERSION, "content": "Policy document not found."}


@router.get("/acceptance-stats")
async def acceptance_stats(
    user: Annotated[UserInfo, Depends(_require_admin)],
) -> dict:
    conn = await _get_conn()
    try:
        rows = await conn.fetch(
            """
            SELECT policy_version,
                   COUNT(*) AS accepted_count,
                   MIN(accepted_at) AS first_accepted,
                   MAX(accepted_at) AS last_accepted
            FROM policy_acceptance
            GROUP BY policy_version
            ORDER BY policy_version DESC
            """
        )
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_active = true")
    finally:
        await conn.close()

    return {
        "total_active_users": total_users,
        "by_version": [dict(r) for r in rows],
    }
