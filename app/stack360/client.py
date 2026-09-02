"""Cliente Python mínimo do Stack360 (NÃO é pacote público).

Usado em testes e nos exemplos da documentação.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx


class Stack360Client:
    def __init__(self, base_url: str, api_key: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self._h = {"Authorization": f"Bearer {api_key}"}
        self._c = httpx.Client(timeout=timeout)

    def ingest_event(self, envelope: dict[str, Any]) -> dict:
        r = self._c.post(f"{self.base_url}/api/v1/ingest/events", json=envelope, headers=self._h)
        return r.json()

    def ingest_batch(self, events: list[dict[str, Any]]) -> dict:
        r = self._c.post(
            f"{self.base_url}/api/v1/ingest/events/batch", json={"events": events}, headers=self._h
        )
        return r.json()

    def get_person_context(self, person_id: str, **params) -> dict:
        r = self._c.get(
            f"{self.base_url}/api/v1/people/{person_id}/context", params=params, headers=self._h
        )
        return r.json()

    def get_company_context(self, company_id: str, **params) -> dict:
        r = self._c.get(
            f"{self.base_url}/api/v1/companies/{company_id}/context", params=params, headers=self._h
        )
        return r.json()

    def find_person_by_identity(self, identity_type: str, identity_value: str) -> Optional[dict]:
        r = self._c.get(
            f"{self.base_url}/api/v1/people",
            params={"identity_type": identity_type, "identity_value": identity_value},
            headers=self._h,
        )
        items = r.json().get("items", [])
        return items[0] if items else None

    def close(self) -> None:
        self._c.close()
