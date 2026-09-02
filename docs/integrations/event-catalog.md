# Event Catalog

`event_type` é **string livre** resolvida por família (`family.action`). Novos
tipos = novo handler em código, **zero migration**. Catálogo mantido enxuto.

Campos comuns do envelope: ver [rest-api.md](rest-api.md). `subject.identities`
resolve/cria a Person; `company` resolve/cria a Company (CNPJ > domínio
inequívoco > nome inequívoco; sem fuzzy, sem merge).

---

## `identity.*`

### `identity.observed`
- **Finalidade:** registrar que uma identidade (email/telefone/…) foi vista.
- **payload `data`:** opcional `{ "name": "..." }` (dica p/ `canonical_name`).
- **Entidades:** `people`, `person_identities`, `workspace_people`,
  (se `company`) `companies` + `person_company_relationships`.
- **Exemplo:**
  ```json
  {"schema_version":"1.0","event_id":"i1","event_type":"identity.observed",
   "occurred_at":"2026-09-01T12:00:00Z",
   "subject":{"identities":[{"type":"email","value":"a@b.com"},{"type":"phone","value":"+5511999998888"}]}}
  ```

## `interaction.*`  (`message_received`, `message_sent`, `email_opened`, `form_submitted`, …)
- **Finalidade:** registrar algo que aconteceu (append).
- **`data`:** livre (vira `interactions.metadata`); `external_interaction_id` opcional.
- **`context`:** `channel`, `direction`.
- **Entidades:** `interactions` (+ resolução de person/company).
- **Exemplo:**
  ```json
  {"schema_version":"1.0","event_id":"m1","event_type":"interaction.message_received",
   "occurred_at":"2026-09-01T12:00:00Z","subject":{"identities":[{"type":"email","value":"a@b.com"}]},
   "context":{"channel":"whatsapp","direction":"inbound"},"data":{"text":"olá"}}
  ```

## `observation.*`

### `observation.recorded`
- **Finalidade:** algo aprendido/inferido sobre a pessoa/empresa. **Append-only.**
- **`data`:** `{ "key": "...", "value": <json>, "confidence": 0.9, "source_kind": "declared|inferred|imported",
  "source_ref": "...", "extractor": "...", "extractor_version": "..." }`
- **Dedup:** só do **mesmo `ingestion_event`** — o **mesmo valor num evento novo
  gera nova observation** (evidência temporal preservada).
- **Entidades:** `observations`.

## `experience.*`  — a experience precisa estar **registrada** (senão `EXPERIENCE_NOT_FOUND`)

`context` obrigatório: `experience_key`, `experience_version`, `external_run_id`
(idempotência da run = `data_source_id + experience_id + external_run_id`).

| tipo | `data` | efeito |
|---|---|---|
| `experience.run_started` | – | cria `experience_runs` (visitor anônimo permitido); grava `attribution.utm_*` |
| `experience.answer_recorded` | `{ "question_key", "value", "context"? }` | `answers` (append; resposta alterada = novo fato) |
| `experience.identity_captured` | `{ "name"? }` + `subject.identities` (+ `company`) | resolve/liga Person; backfill `run.person_id`/`company_id` |
| `experience.run_completed` | `{ "result"?: {}, "score"?, "verdict"?, "score_band"?, "dimensions"?, "engine_name"?, "engine_version"? }` | fecha a run; se houver result/score → `results` |

## `score.*`

### `score.calculated`
- **`data`:** `{ "score_key", "score_value", "score_band"?, "reason_codes"?, "engine_name"?, "engine_version"?, "source_ref"? }`
- **Entidades:** `score_history` (append; sem score universal Stack360 — histórico por chave/fonte).

## `company.*`

### `company.observed`
- **`company`:** `{ cnpj?, domain?, name?, external_id? }`
- **`data`:** opcional `{ "key", "value", "confidence", "source_kind" }` → `observations` da empresa.
- **Entidades:** `companies`, `workspace_companies`.

---

## Casos de resolução (`resolution_cases`)

| situação | case_type | efeito |
|---|---|---|
| 2 identidades fortes (email/phone) apontam p/ Persons diferentes | `identity_conflict` | evento `409`, raw `conflict`, **sem merge**, 1 caso |
| mesmo `(data_source, external_event_id)` reenviado com **payload/`event_type`/MAJOR incompatível** | `event_id_conflict` | evento `409 EVENT_ID_CONFLICT`; `ingestion_event` **original intacto** (sem sobrescrita); 1 caso (repetir não duplica) |
| domínio bate com 2+ companies distintas | `possible_duplicate_company` | evento processa sem company_id; caso aberto |
| nome de empresa ambíguo | `company_conflict` | idem |
| handler falha (ex. experience ausente) | `ingestion_error` | raw `failed`; caso opcional |

> `case_type` é coluna **TEXT livre** — novos valores não exigem migration.
