from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query

from .creator_delivery import AssetStore, CreatorDeliveryWorkflow, SignupRequest, SignupResult
from .infrai_email import InfraiEmail, InfraiError

app = FastAPI(title="Media creator signup")


@lru_cache(maxsize=1)
def build_workflow() -> CreatorDeliveryWorkflow:
    secret = os.environ.get("VERIFICATION_SIGNING_SECRET", "")
    if not secret:
        raise RuntimeError("VERIFICATION_SIGNING_SECRET is required")
    return CreatorDeliveryWorkflow(
        store=AssetStore(),
        email=InfraiEmail(),
        public_url=os.environ.get("PUBLIC_URL", "http://localhost:8000"),
        signing_secret=secret,
    )


@app.post("/signup", response_model=SignupResult, status_code=202)
def signup(request: SignupRequest) -> SignupResult:
    try:
        return build_workflow().start_signup(request)
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=caller_status, detail={"code": exc.code}) from exc


@app.get("/verify-email")
def verify_email(
    creator_id: str,
    asset_id: str,
    expires: int,
    signature: str = Query(min_length=64, max_length=64),
) -> dict[str, str]:
    try:
        asset = build_workflow().verify_email(creator_id, asset_id, expires, signature)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"asset_id": asset.asset_id, "state": asset.state.value}
