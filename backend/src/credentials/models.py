from pydantic import BaseModel, model_validator
from typing import Any
from datetime import datetime

PROVIDER_REQUIRED_KEYS: dict[str, set[str]] = {
    "aws_bedrock":  {"access_key_id", "secret_access_key", "region"},
    "openai":       {"api_key"},
    "azure_openai": {"api_key", "endpoint", "api_version"},
}


class CredentialCreate(BaseModel):
    provider: str
    label: str
    credential_data: dict[str, Any]

    @model_validator(mode="after")
    def validate_provider_keys(self) -> "CredentialCreate":
        required = PROVIDER_REQUIRED_KEYS.get(self.provider)
        if required is None:
            raise ValueError(f"Unknown provider: {self.provider}. Valid: {list(PROVIDER_REQUIRED_KEYS)}")
        missing = required - set(self.credential_data.keys())
        if missing:
            raise ValueError(f"Missing required keys for {self.provider}: {sorted(missing)}")
        return self


class CredentialUpdate(BaseModel):
    label: str | None = None
    credential_data: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_at_least_one(self) -> "CredentialUpdate":
        if self.label is None and self.credential_data is None:
            raise ValueError("At least one of label or credential_data must be provided")
        return self


class CredentialResponse(BaseModel):
    id: str
    provider: str
    label: str
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


class ApplyResponse(BaseModel):
    applied: bool
    credential_id: str
    provider: str
    litellm_response: dict[str, Any] | None = None
    message: str
