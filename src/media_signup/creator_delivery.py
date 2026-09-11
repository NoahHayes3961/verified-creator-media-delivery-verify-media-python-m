from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Protocol
from urllib.parse import urlencode, urlparse

@dataclass(frozen=True)
class SignupRequest:
    creator_id: str
    email: str
    asset_id: str
    source_url: str

    def __post_init__(self) -> None:
        for name in ("creator_id", "asset_id"):
            value = getattr(self, name)
            if not 1 <= len(value) <= 80:
                raise ValueError(f"{name} must contain between 1 and 80 characters")
        if "@" not in self.email or self.email.startswith("@") or self.email.endswith("@"):
            raise ValueError("email must be a valid address")
        parsed_url = urlparse(self.source_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("source_url must be an HTTP URL")


@dataclass(frozen=True)
class SignupResult:
    creator_id: str
    asset_id: str
    state: str
    email_message_id: str

    def model_dump_json(self, *, indent: int | None = None) -> str:
        return json.dumps(asdict(self), indent=indent)


class VerificationEmail(Protocol):
    def send_verification(self, *, to: str, verification_url: str, idempotency_key: str) -> str: ...


class AssetState(str, Enum):
    PROCESSING = "processing"
    VERIFICATION_REQUIRED = "verification_required"
    CREATOR_DELIVERY = "creator_delivery"


@dataclass(frozen=True)
class MediaAsset:
    creator_id: str
    asset_id: str
    source_url: str
    state: AssetState
    email_verified: bool = False
    processing_complete: bool = False


class AssetStore:
    def __init__(self) -> None:
        self._assets: dict[str, MediaAsset] = {}

    def put(self, asset: MediaAsset) -> None:
        self._assets[asset.asset_id] = asset

    def get(self, asset_id: str) -> MediaAsset:
        return self._assets[asset_id]


class CreatorDeliveryWorkflow:
    def __init__(self, store: AssetStore, email: VerificationEmail, public_url: str, signing_secret: str) -> None:
        self.store = store
        self.email = email
        self.public_url = public_url.rstrip("/")
        self.signing_secret = signing_secret.encode()

    def start_signup(self, request: SignupRequest) -> SignupResult:
        asset = MediaAsset(
            creator_id=request.creator_id,
            asset_id=request.asset_id,
            source_url=str(request.source_url),
            state=AssetState.PROCESSING,
        )
        self.store.put(asset)
        expires_at = int(time.time()) + 1800
        signature = self._signature(request.creator_id, request.asset_id, expires_at)
        query = urlencode({"creator_id": request.creator_id, "asset_id": request.asset_id, "expires": expires_at, "signature": signature})
        message_id = self.email.send_verification(
            to=str(request.email),
            verification_url=f"{self.public_url}/verify-email?{query}",
            idempotency_key=f"verify-{request.creator_id}-{request.asset_id}",
        )
        self.store.put(replace(asset, state=AssetState.VERIFICATION_REQUIRED))
        return SignupResult(
            creator_id=request.creator_id,
            asset_id=request.asset_id,
            state=AssetState.VERIFICATION_REQUIRED.value,
            email_message_id=message_id,
        )

    def complete_processing(self, asset_id: str) -> MediaAsset:
        asset = self.store.get(asset_id)
        state = AssetState.CREATOR_DELIVERY if asset.email_verified else AssetState.VERIFICATION_REQUIRED
        updated = replace(asset, processing_complete=True, state=state)
        self.store.put(updated)
        return updated

    def verify_email(self, creator_id: str, asset_id: str, expires: int, signature: str) -> MediaAsset:
        if expires < int(time.time()) or not hmac.compare_digest(signature, self._signature(creator_id, asset_id, expires)):
            raise ValueError("invalid or expired verification link")
        asset = self.store.get(asset_id)
        if asset.creator_id != creator_id:
            raise ValueError("verification link does not match creator")
        state = AssetState.CREATOR_DELIVERY if asset.processing_complete else AssetState.PROCESSING
        updated = replace(asset, email_verified=True, state=state)
        self.store.put(updated)
        return updated

    def _signature(self, creator_id: str, asset_id: str, expires: int) -> str:
        message = f"{creator_id}:{asset_id}:{expires}".encode()
        return hmac.new(self.signing_secret, message, hashlib.sha256).hexdigest()
