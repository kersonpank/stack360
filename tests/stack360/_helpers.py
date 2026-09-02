from __future__ import annotations

import uuid


def ev(event_type: str, *, identities=None, company=None, data=None, context=None, attribution=None, event_id=None, occurred_at="2026-01-01T12:00:00Z"):
    e: dict = {
        "schema_version": "1.0",
        "event_id": event_id or f"e-{uuid.uuid4().hex[:10]}",
        "event_type": event_type,
        "occurred_at": occurred_at,
    }
    if identities is not None:
        e["subject"] = {"identities": identities}
    if company is not None:
        e["company"] = company
    if data is not None:
        e["data"] = data
    if context is not None:
        e["context"] = context
    if attribution is not None:
        e["attribution"] = attribution
    return e


def email(v):
    return [{"type": "email", "value": v}]


class Caller:
    def __init__(self, client, key):
        self.client = client
        self.h = {"Authorization": f"Bearer {key}"}

    def ingest(self, event):
        return self.client.post("/api/v1/ingest/events", json=event, headers=self.h)

    def batch(self, events):
        return self.client.post("/api/v1/ingest/events/batch", json={"events": events}, headers=self.h)

    def get(self, path, **params):
        return self.client.get(path, params=params, headers=self.h)
