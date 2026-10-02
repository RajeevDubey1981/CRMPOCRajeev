import json

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.release_build import RELEASE_BUILD
from app.services.input_security import sanitize_json
from app.routers import auth, calls, claims, complaints, couriers, dashboard, installation_callcenter, installations, item_master, market, orders, partner_agreements_public, partner_registrations, partner_registrations_public, pending_actions, projects, roles, serials, services, users
from app.routers import sarvam_api
from app.routers import site_api

app = FastAPI(title="Indcool CRM API", version="0.1.0")
settings.resolved_upload_dir.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def sanitize_json_request(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"} and "application/json" in request.headers.get("content-type", ""):
        body = await request.body()
        try:
            sanitized = json.dumps(sanitize_json(json.loads(body))).encode("utf-8")
        except (UnicodeDecodeError, json.JSONDecodeError):
            sanitized = body

        async def receive():
            return {"type": "http.request", "body": sanitized, "more_body": False}

        request._receive = receive
    return await call_next(request)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(dashboard.router)
app.include_router(complaints.router)
app.include_router(installations.router)
app.include_router(installation_callcenter.router, prefix="/api/installations")
app.include_router(calls.router)
app.include_router(serials.router)
app.include_router(projects.router)
app.include_router(item_master.router)
app.include_router(couriers.router)
app.include_router(orders.router)
app.include_router(claims.router)
app.include_router(market.router)
app.include_router(services.router)
app.include_router(pending_actions.router)
app.include_router(partner_registrations.router)
app.include_router(partner_registrations_public.router)
app.include_router(partner_agreements_public.router)
app.include_router(sarvam_api.router)
app.include_router(site_api.router)
app.mount("/uploads", StaticFiles(directory=str(settings.resolved_upload_dir)), name="uploads")


@app.on_event("startup")
def ensure_runtime_masters() -> None:
    from app.database import SessionLocal
    from app.seed import ensure_order_consignee_addresses_table
    from app.services.complaint_model_masters import ensure_complaint_model_masters

    ensure_order_consignee_addresses_table()
    with SessionLocal() as db:
        ensure_complaint_model_masters(db)


@app.get("/health")
def health():
    return {"status": "ok", "build": RELEASE_BUILD}
