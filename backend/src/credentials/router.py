import os
import uuid
from typing import Annotated

import asyncpg
import httpx
from fastapi import APIRouter, Depends, HTTPException

from src.auth.router import UserInfo, get_current_user
from src.credentials.crypto import encrypt_json, decrypt_json
from src.credentials.models import (
    ApplyResponse,
    CredentialCreate,
    CredentialResponse,
    CredentialUpdate,
)

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "")
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", "http://litellm:4000")
LITELLM_MASTER_KEY = os.getenv("LITELLM_MASTER_KEY", "")

# LiteLLM param mapping per provider
_LITELLM_PARAM_MAP: dict[str, dict[str, str]] = {
    "aws_bedrock": {
        "access_key_id":     "aws_access_key_id",
        "secret_access_key": "aws_secret_access_key",
        "region":            "aws_region_name",
    },
    "openai": {
        "api_key": "api_key",
    },
    "azure_openai": {
        "api_key":     "api_key",
        "endpoint":    "api_base",
        "api_version": "api_version",
    },
}


def _require_admin(user: Annotated[UserInfo, Depends(get_current_user)]) -> UserInfo:
    if user.tier != "admin":
        raise HTTPException(status_code=403, detail="Admin tier required")
    return user


async def _get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(DATABASE_URL)


@router.post("", response_model=CredentialResponse, status_code=201)
async def create_credential(
    body: CredentialCreate,
    user: Annotated[UserInfo, Depends(_require_admin)],
) -> CredentialResponse:
    encrypted = encrypt_json(body.credential_data)
    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO provider_credentials (id, provider, label, credential_data, created_by)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, provider, label, is_active, created_by, created_at, updated_at
            """,
            str(uuid.uuid4()), body.provider, body.label, encrypted, user.email,
        )
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail=f"Credential '{body.label}' already exists for {body.provider}")
    finally:
        await conn.close()
    return CredentialResponse(**dict(row))


@router.get("", response_model=list[CredentialResponse])
async def list_credentials(
    user: Annotated[UserInfo, Depends(_require_admin)],
) -> list[CredentialResponse]:
    conn = await _get_conn()
    try:
        rows = await conn.fetch(
            "SELECT id, provider, label, is_active, created_by, created_at, updated_at FROM provider_credentials ORDER BY created_at DESC"
        )
    finally:
        await conn.close()
    return [CredentialResponse(**dict(r)) for r in rows]


@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: str,
    user: Annotated[UserInfo, Depends(_require_admin)],
) -> CredentialResponse:
    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            "SELECT id, provider, label, is_active, created_by, created_at, updated_at FROM provider_credentials WHERE id = $1",
            credential_id,
        )
    finally:
        await conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Credential not found")
    return CredentialResponse(**dict(row))


@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: str,
    body: CredentialUpdate,
    user: Annotated[UserInfo, Depends(_require_admin)],
) -> CredentialResponse:
    conn = await _get_conn()
    try:
        existing = await conn.fetchrow(
            "SELECT * FROM provider_credentials WHERE id = $1", credential_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Credential not found")

        new_label = body.label or existing["label"]
        if body.credential_data is not None:
            new_encrypted = encrypt_json(body.credential_data)
        else:
            new_encrypted = existing["credential_data"]

        row = await conn.fetchrow(
            """
            UPDATE provider_credentials
            SET label = $1, credential_data = $2, updated_at = NOW()
            WHERE id = $3
            RETURNING id, provider, label, is_active, created_by, created_at, updated_at
            """,
            new_label, new_encrypted, credential_id,
        )
    finally:
        await conn.close()
    return CredentialResponse(**dict(row))


@router.delete("/{credential_id}", status_code=204)
async def delete_credential(
    credential_id: str,
    user: Annotated[UserInfo, Depends(_require_admin)],
) -> None:
    conn = await _get_conn()
    try:
        result = await conn.execute(
            "UPDATE provider_credentials SET is_active = false, updated_at = NOW() WHERE id = $1",
            credential_id,
        )
    finally:
        await conn.close()
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Credential not found")


@router.post("/{credential_id}/apply", response_model=ApplyResponse)
async def apply_credential(
    credential_id: str,
    user: Annotated[UserInfo, Depends(_require_admin)],
) -> ApplyResponse:
    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM provider_credentials WHERE id = $1 AND is_active = true",
            credential_id,
        )
    finally:
        await conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Credential not found or inactive")

    cred_data = decrypt_json(row["credential_data"])
    provider = row["provider"]
    param_map = _LITELLM_PARAM_MAP.get(provider, {})
    litellm_params = {param_map.get(k, k): v for k, v in cred_data.items()}

    # GET current models from LiteLLM then update each matching model
    headers = {"Authorization": f"Bearer {LITELLM_MASTER_KEY}"}
    async with httpx.AsyncClient(base_url=LITELLM_BASE_URL, headers=headers) as client:
        info_resp = await client.get("/model/info")
        if info_resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"LiteLLM /model/info failed: {info_resp.text}")

        models = info_resp.json().get("data", [])
        provider_prefix = "bedrock/" if provider == "aws_bedrock" else (provider + "/")
        target_models = [m for m in models if m.get("model_name", "").startswith(provider_prefix) or
                         any(v.get("litellm_provider") == provider for v in [m.get("litellm_params", {})])]

        # If no models match, update all models (catch-all for generic setups)
        if not target_models:
            target_models = models

        updated_ids = []
        for model in target_models:
            model_id = model.get("model_info", {}).get("id")
            if not model_id:
                continue
            patch_body = {"model_id": model_id, "litellm_params": litellm_params}
            patch_resp = await client.post("/model/update", json=patch_body)
            if patch_resp.status_code == 200:
                updated_ids.append(model_id)

    return ApplyResponse(
        applied=True,
        credential_id=credential_id,
        provider=provider,
        litellm_response={"updated_model_ids": updated_ids},
        message=f"Applied to {len(updated_ids)} model(s)",
    )
