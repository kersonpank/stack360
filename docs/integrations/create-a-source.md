# Como conectar uma fonte nova

**Nenhum desenvolvedor deve precisar mexer no canonical core** para adicionar uma
fonte normal. Você registra a fonte, pega uma API key e manda eventos no envelope
universal.

## 1. App própria → REST

```
sua aplicação  ──►  POST /api/v1/ingest/events  (envelope universal)  ──►  Stack360
```

```bash
python -m app.stack360.admin create-source --workspace <ws> --key minha-app --name "Minha App" --type custom
python -m app.stack360.admin create-api-key --workspace <ws> --source minha-app --name ingest --scopes ingest
```

Emita eventos `identity.observed`, `interaction.*`, `observation.recorded`,
`score.calculated`, etc. Idempotência: use um `event_id` estável por fato.

## 2. Serviço que só faz webhook (Instagram, form externo, …)

```
Instagram  ──►  webhook  ──►  [adapter]  ──►  StackEvent  ──►  POST ingest  ──►  Stack360
```

- `create-source --type instagram` + `create-webhook-endpoint --source-key ig-hook`.
- V1: adapter `passthrough` (corpo cru → `data`; `mapping.event_type` / `event_id_path`).
- Integração dedicada: registre um adapter em `adapters/` com
  `register_adapter("instagram", fn)` onde `fn(body, mapping, source_key) -> StackEvent`.
  O core não muda.

## 3. Import de arquivo / carga em lote

```
arquivo (CSV/JSON)  ──►  job  ──►  StackEvent[]  ──►  POST /api/v1/ingest/events/batch  ──►  Stack360
```

Cada linha vira um evento com `event_id` determinístico (ex. `hash(arquivo + linha)`),
garantindo replay seguro. Limite de lote: `STACK360_BATCH_MAX`.

## 4. Diagnóstico / experiência

```
python -m app.stack360.admin create-experience --workspace <ws> --key <slug> --version 1 --name "…" --type diagnostic
```

Depois envie `experience.run_started` → `experience.answer_recorded` →
`experience.identity_captured` → `experience.run_completed`. A experience
**precisa** existir antes (senão `EXPERIENCE_NOT_FOUND`).

## Escrevendo um adapter (webhook)

```python
# adapters/meu_servico.py
from adapters import register_adapter
from app.stack360.schemas.envelope import StackEvent

def meu_adapter(body: bytes, mapping: dict, source_key: str) -> StackEvent:
    import json
    p = json.loads(body)
    return StackEvent(
        schema_version="1.0",
        event_id=p["id"],
        event_type="interaction.message_received",
        occurred_at=p["ts"],
        subject={"identities": [{"type": "email", "value": p["from"]}]},
        data={"text": p.get("text")},
    )

register_adapter("meu-servico", meu_adapter)
```

Carregue o módulo (import) na inicialização do processo. **O canonical core
permanece intocado.**
