# Autenticação — Stack360

## API keys

- Formato: `st_` + 32 bytes url-safe aleatórios.
- Armazenamento: **`key_hash` = `sha256(key)` (UNIQUE)** + `key_prefix` (primeiros
  12 chars, **não único** — só p/ exibição/listagem/revogação assistida).
- A **plaintext é exibida uma única vez** pelo `create-api-key` e **nunca é
  persistida nem logada**.
- Lookup de autenticação: `sha256(chave_apresentada)` → `WHERE key_hash = :h`.
  **Não depende** de unicidade de `key_prefix`.

## Scopes

| Scope | Concede | Regra |
|---|---|---|
| `ingest` | `POST /ingest/*`, `POST /webhooks/*`, MCP `ingest_event`/`record_*` | **Key DEVE estar vinculada a exatamente uma `data_source`** (`--source` obrigatório no `create-api-key`). |
| `read` | todos os `GET` | pode ser workspace-level (sem source) |
| `mcp` | ferramentas do servidor MCP | pode ser workspace-level |

## Workspace

O `workspace_id` vem **sempre** da key. Nenhum endpoint ou tool aceita
`workspace_id` do cliente. Toda leitura é isolada por workspace; recursos de
outro workspace retornam `404`.

## Ciclo de vida

```bash
python -m app.stack360.admin create-api-key --workspace <slug> [--source <key>] --name <n> --scopes ingest,read,mcp
python -m app.stack360.admin list-api-keys
python -m app.stack360.admin revoke-api-key --prefix st_xxxxxxxx   # (ou --id <uuid>)
```

Revogação: `status='revoked'` + `revoked_at`. Keys revogadas → `401 AUTH_INVALID`.

## Webhooks

O endpoint `POST /api/v1/webhooks/{source_key}` aceita **API key source-bound**
(validando `workspace_id` **e** `data_source_id` == os do endpoint — uma key da
Source A não publica na Source B) **ou** assinatura **HMAC** quando configurada
(segredo cifrado at-rest com AES-GCM, master key `STACK360_WEBHOOK_SECRET_KEY`).
Sem master key/`cryptography`, só o modo API key é suportado. Ver
[webhooks.md](webhooks.md).
