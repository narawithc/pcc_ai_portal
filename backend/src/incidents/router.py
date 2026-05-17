"""Incidents API — AI Policy v1.0 Section 10

POST /incidents              — any authenticated user (report incident)
POST /incidents/internal     — internal only (classifier auto-create, no auth)
GET  /incidents              — admin only
PATCH /incidents/{id}        — admin only (update status/resolution)
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from src.auth.router import UserInfo, get_current_user
from src.credentials.router import _require_admin
from src.incidents.models import (
    IncidentCreate,
    IncidentInternalCreate,
    IncidentResponse,
    IncidentUpdate,
)

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
INCIDENT_EMAIL = os.getenv("INCIDENT_EMAIL", "ai-report@precise.co.th")

_VALID_CATEGORIES = {"data_leak", "hallucination", "misuse", "deepfake", "other"}
_VALID_SEVERITIES = {"low", "medium", "high", "critical"}
_VALID_STATUSES = {"reported", "triaged", "contained", "resolved", "closed"}


async def _get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(DATABASE_URL)


def _row_to_response(row: asyncpg.Record) -> IncidentResponse:
    d = dict(row)
    d["id"] = str(d["id"])
    if d.get("reporter_id") is not None:
        d["reporter_id"] = str(d["reporter_id"])
    return IncidentResponse(**d)


async def _send_email(subject: str, body: str) -> None:
    if not SMTP_HOST:
        return
    try:
        import aiosmtplib
        await aiosmtplib.send(
            message=f"Subject: {subject}\nFrom: {SMTP_USER}\nTo: {INCIDENT_EMAIL}\n\n{body}",
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
    except Exception:
        pass  # email failure must not block incident creation


async def _insert_incident(
    conn: asyncpg.Connection,
    *,
    reporter_id: str | None,
    category: str,
    severity: str,
    title: str,
    description: str,
) -> asyncpg.Record:
    row = await conn.fetchrow(
        """
        INSERT INTO incidents
            (id, reporter_id, category, severity, title, description, status, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, 'reported', NOW())
        RETURNING *
        """,
        str(uuid.uuid4()),
        reporter_id,
        category,
        severity,
        title,
        description,
    )
    return row  # type: ignore[return-value]


@router.post("", response_model=IncidentResponse, status_code=201)
async def create_incident(
    body: IncidentCreate,
    user: Annotated[UserInfo, Depends(get_current_user)],
) -> IncidentResponse:
    if body.category not in _VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Invalid category. Valid: {_VALID_CATEGORIES}")
    if body.severity not in _VALID_SEVERITIES:
        raise HTTPException(status_code=422, detail=f"Invalid severity. Valid: {_VALID_SEVERITIES}")

    conn = await _get_conn()
    try:
        reporter_row = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1", user.email
        )
        reporter_id = str(reporter_row["id"]) if reporter_row else None
        row = await _insert_incident(
            conn,
            reporter_id=reporter_id,
            category=body.category,
            severity=body.severity,
            title=body.title,
            description=body.description,
        )
    finally:
        await conn.close()

    await _send_email(
        subject=f"[AI Incident] [{body.severity.upper()}] {body.title}",
        body=(
            f"Category: {body.category}\n"
            f"Severity: {body.severity}\n"
            f"Reporter: {user.email}\n\n"
            f"Description:\n{body.description}\n\n"
            f"View in portal: https://ai.precise.co.th/incidents/{row['id']}"
        ),
    )
    return _row_to_response(row)


@router.post("/internal", response_model=IncidentResponse, status_code=201)
async def create_incident_internal(body: IncidentInternalCreate) -> IncidentResponse:
    """Internal endpoint — called by classifier / pii-detector (no user auth)."""
    conn = await _get_conn()
    try:
        reporter_id = None
        if body.reporter_email:
            r = await conn.fetchrow("SELECT id FROM users WHERE email = $1", body.reporter_email)
            if r:
                reporter_id = str(r["id"])
        row = await _insert_incident(
            conn,
            reporter_id=reporter_id,
            category=body.category,
            severity=body.severity,
            title=body.title,
            description=body.description,
        )
    finally:
        await conn.close()

    await _send_email(
        subject=f"[AI Incident AUTO] [{body.severity.upper()}] {body.title}",
        body=(
            f"Auto-detected incident\n"
            f"Category: {body.category}\n"
            f"Reporter email: {body.reporter_email or 'system'}\n\n"
            f"Description:\n{body.description}"
        ),
    )
    return _row_to_response(row)


@router.get("", response_model=list[IncidentResponse])
async def list_incidents(
    user: Annotated[UserInfo, Depends(_require_admin)],
) -> list[IncidentResponse]:
    conn = await _get_conn()
    try:
        rows = await conn.fetch(
            "SELECT * FROM incidents ORDER BY created_at DESC LIMIT 200"
        )
    finally:
        await conn.close()
    return [_row_to_response(r) for r in rows]


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: str,
    body: IncidentUpdate,
    user: Annotated[UserInfo, Depends(_require_admin)],
) -> IncidentResponse:
    conn = await _get_conn()
    try:
        existing = await conn.fetchrow("SELECT * FROM incidents WHERE id = $1", incident_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Incident not found")

        updates: dict = {"updated_at": datetime.now(timezone.utc)}
        if body.status is not None:
            if body.status not in _VALID_STATUSES:
                raise HTTPException(status_code=422, detail=f"Invalid status. Valid: {_VALID_STATUSES}")
            updates["status"] = body.status
        if body.resolution is not None:
            updates["resolution"] = body.resolution
        if body.contained_at is not None:
            updates["contained_at"] = body.contained_at
        if body.investigated_at is not None:
            updates["investigated_at"] = body.investigated_at
        if body.pdpc_notified_at is not None:
            updates["pdpc_notified_at"] = body.pdpc_notified_at

        set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
        values = [incident_id] + list(updates.values())
        row = await conn.fetchrow(
            f"UPDATE incidents SET {set_clause} WHERE id = $1 RETURNING *",
            *values,
        )
    finally:
        await conn.close()
    return _row_to_response(row)  # type: ignore[arg-type]
