# Stack360 REST API

Base URL local: `http://localhost:8010`  ·  Versão de API: **`/api/v1`**
OpenAPI/Swagger: `GET /docs` (tags `Ingestion`, `People`, `Companies`,
`Interactions`, `Experiences`, `Sources`, `Resolution`, `Webhooks`).

## Autenticação

Header `Authorization: Bearer st_...` (ou `X-API-Key: st_...`).
O **workspace vem sempre da key** — o cliente nunca o envia. Ver
[authentication.md](authentication.md).

| Scope | Uso |
|---|---|
| `ingest` | `POST /ingest/*`, `POST /webhooks/*`. **Exige key vinculada a UMA source.** |
| `read` | todos os `GET` |
| `mcp` | ferramentas do servidor MCP |

## Envelope universal de evento

```jsonc
{
  "schema_version": "1.0",              // obrigatório. MAJOR != 1 -> SCHEMA_UNSUPPORTED
  "event_id": "id-unico-na-source",     // obrigatório. idempotência = (source, event_id)
  "event_type": "family.action",        // string livre, validada por família
  "occurred_at": "2026-09-01T12:00:00Z",// obrigatório (ISO-8601 UTC)
  "subject":  { "identities": [ { "type": "email", "value": "...", "verified": false } ] },
  "company":  { "cnpj": "...", "domain": "...", "name": "...", "external_id": "..." },
  "data":     { },                      // validado conforme event_type
  "context":  { "visitor_id": "...", "experience_key": "...", "experience_version": "1",
                "external_run_id": "...", "channel": "...", "direction": "..." },
  "attribution": { "utm_source": "...", "utm_medium": "...", "utm_campaign": "...",
                   "utm_content": "...", "utm_term": "...", "referrer": "...", "landing_url": "..." }
}
```

Tipos de evento: ver [event-catalog.md](event-catalog.md).

## Idempotência (requisito de 1ª classe)

Chave: **`(data_source_id, external_event_id)`**. Nunca dependa só de timestamp.

- **Mesmo `event_id` + mesmo payload** (mesmo `payload_hash`, mesmo `event_type`,
  mesmo MAJOR de `schema_version`), já processado → `200 {"status":"duplicate","duplicate":true}`.
- **Mesmo `event_id` + payload/contrato DIFERENTE** → `409 {"error":{"code":"EVENT_ID_CONFLICT"}, ...}`.
  É conflito de **contrato da source**: o `ingestion_event` **original permanece
  intacto** (payload, status e `retry_count` inalterados; nenhum raw novo é criado),
  e é aberto **um** `resolution_case` (`case_type="event_id_conflict"`; repetir o
  payload conflitante **não** cria casos novos). `error.details` traz só o auditável:
  `event_id`, `source`, `event_type`, `existing_payload_hash`, `incoming_payload_hash`.
  Corrija o `event_id` na origem (ou o payload) e reenvie.
- Evento em conflito de **identidade** → `409 {"error":{"code":"IDENTITY_CONFLICT"}, "resolution_case_id":"..."}`
  (conflito **diferente** de `EVENT_ID_CONFLICT`).
- Outro worker processando o MESMO evento agora → `200 {"status":"processing","processing":true}`
  (não é "evento inexistente"; não processa em paralelo).

O `ingestion_event` bruto é persistido numa transação própria e **sobrevive**
a qualquer falha do processamento (replay via `admin reprocess-event`).

## Endpoints

### Ingestão (`ingest`)

| Método | Path | Notas |
|---|---|---|
| POST | `/api/v1/ingest/events` | um envelope |
| POST | `/api/v1/ingest/events/batch` | `{ "events": [...] }`, limite `STACK360_BATCH_MAX` (100). Status por item. |
| POST | `/api/v1/webhooks/{source_key}` | ver [webhooks.md](webhooks.md) |

### Leitura (`read`) — paginação por cursor obrigatória (`?limit=` ≤ 200, `?cursor=`)

| Método | Path |
|---|---|
| GET | `/api/v1/people` — `?query=&identity_type=&identity_value=` |
| GET | `/api/v1/people/{id}` |
| GET | `/api/v1/people/{id}/context` — `?limit=&since=&include=identities,companies,recent_interactions,observations,experience_runs,results,scores` |
| GET | `/api/v1/companies` — `?query=&domain=&cnpj=` |
| GET | `/api/v1/companies/{id}` · `/api/v1/companies/{id}/context` |
| GET | `/api/v1/interactions` — `?person_id=&company_id=&type=&since=` |
| GET | `/api/v1/experiences` · `/api/v1/experiences/{id}/runs` · `/api/v1/runs/{id}` |
| GET | `/api/v1/sources` · `/api/v1/sources/health` |
| GET | `/api/v1/resolution-cases` — `?status=&case_type=&severity=&source=&created_since=` |
| GET | `/api/v1/resolution-cases/{id}` |

**Workspace isolation**: toda query filtra pelo workspace da key. Acesso cross-workspace → `404` (não vaza existência).

## Contrato de erro

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "…", "details": {} } }
```

| code | HTTP |
|---|---|
| `AUTH_INVALID` | 401 |
| `SCOPE_DENIED` | 403 |
| `SOURCE_DISABLED` | 403 |
| `SCHEMA_UNSUPPORTED` | 400 |
| `VALIDATION_ERROR` | 422 |
| `EXPERIENCE_NOT_FOUND` | 422 — experience não registrada (raw fica `failed`) |
| `IDENTITY_CONFLICT` | 409 — raw preservado + `resolution_case` |
| `RATE_LIMITED` | 429 |
| `NOT_FOUND` | 404 |
| `INTERNAL_ERROR` | 500 — sem stack trace |

`EVENT_ALREADY_PROCESSED` aparece só como status de item no batch.

## Rate limit

Best-effort **em memória**, por `api_key.id` (`STACK360_RATE_LIMIT_PER_MIN`, default 600).
Não é distribuído. `429` inclui `Retry-After`.

## Versionamento

- Envelope: `schema_version` obrigatório; só MAJOR `1` suportado hoje.
- API: `/api/v1`. Mudanças **aditivas**; nada de quebra silenciosa de payload.

## CURL

```bash
# criar evento
curl -X POST $BASE/api/v1/ingest/events -H "Authorization: Bearer $INGEST" \
  -H 'content-type: application/json' -d '{"schema_version":"1.0","event_id":"e1",
  "event_type":"identity.observed","occurred_at":"2026-09-01T12:00:00Z",
  "subject":{"identities":[{"type":"email","value":"a@b.com"}]}}'

# buscar pessoa por identidade
curl "$BASE/api/v1/people?identity_type=email&identity_value=a@b.com" -H "Authorization: Bearer $READ"

# buscar empresa
curl "$BASE/api/v1/companies?cnpj=12345678000199" -H "Authorization: Bearer $READ"

# contexto
curl "$BASE/api/v1/people/$PID/context?include=identities,companies&limit=10" -H "Authorization: Bearer $READ"
```
