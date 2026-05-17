"""Auto-provision LiteLLM virtual key per user (called by Open-WebUI pipeline)"""

import os

import asyncpg
import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "")
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", "http://litellm:4000")
LITELLM_MASTER_KEY = os.getenv("LITELLM_MASTER_KEY", "")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "")
LITELLM_DEFAULT_TEAM_ID = os.getenv("LITELLM_DEFAULT_TEAM_ID", "")


class ProvisionRequest(BaseModel):
    email: str


class ProvisionResponse(BaseModel):
    litellm_key: str
    provisioned: bool


@router.post("/provision", response_model=ProvisionResponse, status_code=200)
async def provision_key(
    body: ProvisionRequest,
    x_internal_secret: str | None = Header(default=None, alias="x-internal-secret"),
) -> ProvisionResponse:
    if INTERNAL_SECRET and x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT litellm_key FROM user_litellm_keys WHERE email = $1",
            str(body.email),
        )
        if row:
            return ProvisionResponse(litellm_key=row["litellm_key"], provisioned=False)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{LITELLM_BASE_URL}/key/generate",
                headers={"Authorization": f"Bearer {LITELLM_MASTER_KEY}"},
                json={
                    "user_id": str(body.email),
                    "team_id": LITELLM_DEFAULT_TEAM_ID or None,
                    "key_alias": f"user:{body.email}",
                    "metadata": {"email": str(body.email)},
                },
            )

        if not resp.is_success:
            raise HTTPException(status_code=502, detail=f"LiteLLM key generation failed: {resp.text}")

        litellm_key = resp.json()["key"]

        await conn.execute(
            """
            INSERT INTO user_litellm_keys (email, litellm_key, team_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (email) DO UPDATE
                SET litellm_key = EXCLUDED.litellm_key,
                    updated_at  = NOW()
            """,
            str(body.email),
            litellm_key,
            None,
        )
    finally:
        await conn.close()

    return ProvisionResponse(litellm_key=litellm_key, provisioned=True)
