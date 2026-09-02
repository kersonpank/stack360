# Exemplos

Base local: `http://localhost:8010`. Nenhum secret real.

## Ingerir identidade + empresa

**Request**
```json
POST /api/v1/ingest/events
{
  "schema_version": "1.0",
  "event_id": "crm-42",
  "event_type": "identity.observed",
  "occurred_at": "2026-09-01T12:00:00Z",
  "subject": { "identities": [
    { "type": "email", "value": "carlos@empresa.com" },
    { "type": "phone", "value": "+55 11 98888-7777" }
  ]},
  "company": { "cnpj": "12.345.678/0001-99", "name": "Empresa ABC Ltda", "domain": "empresa.com" }
}
```
**Response `200`**
```json
{ "accepted": true, "event_id": "crm-42", "status": "accepted",
  "entities": { "person_id": "…", "company_id": "…", "identities_linked": 2 } }
```
Reenviar → `{ "accepted": true, "status": "duplicate", "duplicate": true }`.

## Conflito de identidade

Dois eventos prévios criaram Person P1 (email x@y.com) e Person P2 (phone +55…001).
Um evento que traz **os dois** → `409`:
```json
{ "error": { "code": "IDENTITY_CONFLICT",
    "message": "identidades fortes do evento apontam para Persons diferentes",
    "details": { "candidate_person_ids": ["…P1…","…P2…"] } },
  "event_id": "…", "resolution_case_id": "…" }
```
O `ingestion_event` fica `status='conflict'` (preservado) e há **1**
`resolution_case(identity_conflict)`. Reenviar não duplica o caso.

## Observação (evidência temporal)

```json
POST /api/v1/ingest/events
{ "schema_version":"1.0","event_id":"obs-jan","event_type":"observation.recorded",
  "occurred_at":"2026-01-15T00:00:00Z",
  "subject":{"identities":[{"type":"email","value":"carlos@empresa.com"}]},
  "data":{"key":"ma_shipping_frequency","value":"weekly","confidence":0.8,"source_kind":"declared"} }
```
Um evento igual em agosto (`event_id":"obs-aug"`) → **2 observations** (histórico
preservado). O mesmo `event_id` reenviado → 1 observation.

## Diagnóstico (run anônima → identificada → resultado)

```json
1) {"event_type":"experience.run_started","context":{"experience_key":"diagnostico-expansao-ma","experience_version":"1","external_run_id":"RUN-42","visitor_id":"v-9"},"attribution":{"utm_source":"meta","utm_campaign":"ma-2026"}, ...}
2) {"event_type":"experience.answer_recorded","data":{"question_key":"ma_recipients","value":"21_50"}, "context":{...}, ...}
3) {"event_type":"experience.identity_captured","subject":{"identities":[{"type":"email","value":"joao@empresaabc.com.br"}]},"company":{"cnpj":"12345678000199"}, "context":{...}, ...}
4) {"event_type":"experience.run_completed","data":{"result":{"tier":"A"},"score":87,"verdict":"go"}, "context":{...}, ...}
```
`GET /api/v1/runs/RUN-42-uuid` → `status:"completed"`, `answers_latest`, `results[0].score = 87`.
`GET /api/v1/people/{person}/context` → o run e o result aparecem.

## Contexto (recorte)

```
GET /api/v1/people/{id}/context?include=identities,companies,scores&limit=10&since=2026-06-01T00:00:00Z
```

## Cliente Python

```python
from app.stack360.client import Stack360Client
c = Stack360Client("http://localhost:8010", api_key=INGEST_KEY)
print(c.ingest_event({...}))
r = Stack360Client("http://localhost:8010", api_key=READ_KEY)
print(r.find_person_by_identity("email", "carlos@empresa.com"))
print(r.get_person_context(pid, include="identities,companies"))
```
