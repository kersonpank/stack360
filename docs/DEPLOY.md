# Deploy do Stack360 (VPS + Docker)

O que sobe é o **Stack360 Canonical Core** (`uvicorn app.stack360.main:app`): uma API
FastAPI que precisa de um processo sempre ligado + PostgreSQL dedicado. **Não roda em
Vercel/serverless** (sem processo persistente, sem Postgres local, sem o servidor MCP,
sem o CLI admin). Vercel serve, no máximo, o frontend Next.js (ver o fim deste doc).

O `docker compose` abaixo sobe 3 containers:

| serviço | o quê |
|---|---|
| `db` | PostgreSQL 16, schema `stack360` (21 tabelas), volume persistente |
| `api` | `uvicorn app.stack360.main:app` — **só na rede interna** |
| `caddy` | reverse proxy, HTTPS automático (Let's Encrypt), Basic Auth no `/docs` |

---

## 1. Pré-requisitos na VPS

- Docker Engine + plugin `docker compose` (v2).
- Portas **80** e **443** abertas no firewall. **5432 fechada** para a internet.
- (Para HTTPS) um domínio com registro **DNS A** apontando para o IP da VPS
  — ex.: `api.seudominio.com`.

## 2. Clonar

```bash
git clone git@github.com:kersonpank/stack360.git
cd stack360
```

## 3. Configurar

```bash
cp deploy/.env.prod.example deploy/.env.prod
nano deploy/.env.prod
```

Preencha (ver comentários no arquivo):

- `POSTGRES_PASSWORD` — senha longa aleatória. **Use a mesma** nas 3 URLs
  (`STACK360_DATABASE_URL`, `DATABASE_URL`, `NORMALIZER_DATABASE_URL`).
- `STACK360_CORS_ORIGINS` — domínio do frontend, se houver (senão deixe vazio).
- `DOMAIN` / `ACME_EMAIL` — seu domínio e e-mail para o certificado.
  Para testar **sem domínio**, use `DOMAIN=:80` (só HTTP).
- `BASIC_AUTH_USER` e `BASIC_AUTH_HASH` — gate do `/docs`. Gere o hash:

  ```bash
  docker run --rm caddy:2-alpine caddy hash-password --plaintext 'suaSenhaForte'
  ```

- `STACK360_WEBHOOK_SECRET_KEY` — opcional (HMAC de webhook). Gere:

  ```bash
  python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
  ```

## 4. Subir

```bash
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml up -d --build
```

O container `api` no boot:

1. espera o Postgres;
2. na **primeira vez**, faz `alembic stamp 13b31f818410` (marca o baseline legado
   **sem** rodar as migrations legadas — a cadeia legada não sobe em banco vazio);
3. faz `alembic upgrade aa47386e4e9f` (cria o schema `stack360`);
4. sobe o uvicorn.

Boots seguintes: só o `alembic upgrade` (no-op) e o uvicorn.

### Verificar

```bash
docker compose -f deploy/docker-compose.prod.yml ps
curl -s https://api.seudominio.com/api/v1/health
# -> {"status":"ok","service":"stack360-core"}
```

`https://api.seudominio.com/docs` deve pedir usuário/senha (Basic Auth).

## 5. Bootstrap dos dados (workspace, source, API keys)

Toda rota exige `Authorization: Bearer st_...`. Crie as chaves pelo CLI admin
**dentro do container**:

```bash
DC="docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml"

$DC exec api python -m app.stack360.admin create-workspace \
  --slug stack360-empresas --name "Stack360 Empresas"

$DC exec api python -m app.stack360.admin create-source \
  --workspace stack360-empresas --key minha-app --name "Minha App" --type custom

# key de ESCRITA (ingestão) — SEMPRE amarrada a uma source
$DC exec api python -m app.stack360.admin create-api-key \
  --workspace stack360-empresas --source minha-app --name ingest --scopes ingest

# key de LEITURA (e MCP) — workspace-level
$DC exec api python -m app.stack360.admin create-api-key \
  --workspace stack360-empresas --name read --scopes read,mcp
```

Cada `create-api-key` imprime a chave `st_...` **uma única vez** — guarde.

Teste ponta a ponta seguindo [integrations/quickstart.md](integrations/quickstart.md)
(a partir do passo 3), trocando a base URL por `https://api.seudominio.com`.

## 6. Operação

```bash
DC="docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml"

$DC logs -f api            # logs da API
$DC logs -f caddy          # logs do proxy / TLS
$DC restart api            # reiniciar a API
$DC down                   # parar tudo (dados ficam no volume)
```

### Atualizar para uma versão nova

```bash
git pull
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml up -d --build
```

### Backup do banco

```bash
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml \
  exec db pg_dump -U stack360 -d stack360 | gzip > stack360-$(date +%F).sql.gz
```

Agende no cron. O volume `pgdata` já persiste entre restarts, mas **não** substitui backup.

## 7. Segurança — o que já está no lugar

- **API key obrigatória** em toda rota (`Authorization: Bearer st_...`), com scopes
  (`ingest` / `read` / `mcp`) e chave de ingestão amarrada a uma source.
  Revogar: `python -m app.stack360.admin revoke-api-key --prefix st_xxxxx`.
- **`/docs`, `/redoc`, `/openapi.json`** atrás de Basic Auth (Caddy).
- **API não exposta direto** — só o Caddy publica 80/443; `api` e `db` ficam na
  rede interna do compose.
- **HTTPS automático** via Caddy/Let's Encrypt.
- **Isolamento de workspace** aplicado em toda query (cross-workspace → 404).

O que **não** existe ainda (e não é necessário para colocar no ar): login por usuário,
OAuth/JWT, rate limit distribuído. Se um dia houver dashboard com login humano, é uma
camada fina à parte (cookie de sessão / Cloudflare Access na frente) — não bloqueia o deploy.

## 8. MCP (agentes de IA)

O servidor MCP é **stdio**, não é um serviço de rede — roda **junto do agente**, não no
compose. Aponte-o para o Postgres do deploy:

```bash
STACK360_API_KEY=st_...  \
STACK360_DATABASE_URL=postgresql+psycopg2://stack360:SENHA@HOST:5432/stack360 \
python -m app.stack360.mcp.server
```

Se o agente roda fora da VPS, exponha o Postgres **só** por túnel SSH/VPN (não abra
5432 na internet). Transporte HTTP do MCP é follow-up documentado, não implementado.

## 9. Frontend Next.js (`frontend/`)

Hoje o frontend consome a **API legada** (`/api/v1/stakeholders`…), **não** o Stack360.
Antes de servir para algo real, `frontend/src/lib/` precisa ser reapontado para os
endpoints do Stack360 (`/api/v1/people`, `/context`, …).

Quando estiver pronto, o caminho mais simples é **Vercel**:

- import do repo → root directory `frontend/`;
- env `NEXT_PUBLIC_API_BASE_URL=https://api.seudominio.com`;
- adicione o domínio da Vercel em `STACK360_CORS_ORIGINS` (deploy/.env.prod) e
  `docker compose ... up -d` de novo.

Alternativa: adicionar um serviço `web` (Node) ao `docker-compose.prod.yml` e uma
rota no `Caddyfile` — só vale a pena se você não quiser depender da Vercel.
