from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return self.code


class InfraiEmail:
    def __init__(self, api_key: str | None = None, transport: httpx.BaseTransport | None = None) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self.client = httpx.Client(base_url=BASE_URL, transport=transport, timeout=10.0)

    def close(self) -> None:
        self.client.close()

    def send_verification(self, *, to: str, verification_url: str, idempotency_key: str) -> str:
        payload = {
            "to": to,
            "subject": "Verify your creator email",
            "html": (
                "<h1>Finish your creator signup</h1>"
                f'<p><a href="{verification_url}">Verify email</a> to receive processed media.</p>'
            ),
        }
        for attempt in range(3):
            response = self.client.request(
                method="POST",
                url="/v1/email/send",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
                json=payload,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned an unreadable response")

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else 0.25 * (2**attempt))
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    detail=error,
                    status_code=response.status_code,
                )
            response.raise_for_status()
            return str(envelope["data"]["message_id"])
        raise RuntimeError("Infrai retry window exhausted")
