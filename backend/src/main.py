"""PCC AI Portal — Custom Backend
FastAPI app: auth middleware + PII detector + billing service
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from src.auth.router import router as auth_router
from src.pdpa.router import router as pdpa_router
from src.billing.router import router as billing_router
from src.credentials.router import router as credentials_router
from src.classifier.router import router as classifier_router
from src.incidents.router import router as incidents_router
from src.audit.router import router as audit_router
from src.policy.router import router as policy_router
from src.dlp.router import router as dlp_router
from src.provision.router import router as provision_router

app = FastAPI(title="PCC AI Portal Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # open-webui
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics — exposes /metrics endpoint
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/health", "/metrics"],
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
).instrument(app).expose(app, include_in_schema=False, tags=["monitoring"])

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(pdpa_router, prefix="/guardrails", tags=["pdpa"])
app.include_router(billing_router, prefix="/billing", tags=["billing"])
app.include_router(credentials_router, prefix="/api/v1/admin/credentials", tags=["credentials"])
app.include_router(classifier_router, prefix="/classifier", tags=["classifier"])
app.include_router(incidents_router, prefix="/incidents", tags=["incidents"])
app.include_router(audit_router, prefix="/audit", tags=["audit"])
app.include_router(policy_router, prefix="/policy", tags=["policy"])
app.include_router(dlp_router, prefix="/dlp", tags=["dlp"])
app.include_router(provision_router, prefix="/auth", tags=["auth"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhooks/budget-alert")
async def budget_alert(payload: dict):
    """รับ webhook จาก LiteLLM เมื่อ budget ถึง threshold"""
    # TODO: ส่ง LINE Notify / email
    return {"received": True, "payload": payload}
