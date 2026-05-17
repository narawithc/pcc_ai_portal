from datetime import datetime
from pydantic import BaseModel


class IncidentCreate(BaseModel):
    category: str   # data_leak | hallucination | misuse | deepfake | other
    severity: str   # low | medium | high | critical
    title: str
    description: str


class IncidentInternalCreate(BaseModel):
    """Used by internal auto-create (classifier, pii-detector)."""
    category: str
    severity: str
    title: str
    description: str
    reporter_email: str | None = None


class IncidentUpdate(BaseModel):
    status: str | None = None
    resolution: str | None = None
    contained_at: datetime | None = None
    investigated_at: datetime | None = None
    pdpc_notified_at: datetime | None = None


class IncidentResponse(BaseModel):
    id: str
    reporter_id: str | None
    category: str
    severity: str
    title: str
    description: str
    status: str
    contained_at: datetime | None
    investigated_at: datetime | None
    pdpc_notified_at: datetime | None
    resolution: str | None
    created_at: datetime
    updated_at: datetime
