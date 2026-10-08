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

> **Sua VPS já roda Traefik** (outros sites/stacks numa rede overlay externa)?
> Esse Caddy embutido vai brigar pela porta 80/443. Use a [seção 10](#10-alternativa--vps-com-traefik-já-configurado-swarm)
> em vez deste fluxo — mesma API, mesmo banco, só troca o proxy pelo Traefik que já existe.

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

## 10. Alternativa — VPS com Traefik já configurado (Swarm)

Se a VPS já roda **Traefik** (Docker Swarm) cuidando de HTTPS/roteamento para outros
sites, não suba o Caddy deste repo — ele ia disputar as portas 80/443 com o Traefik
existente. Use `deploy/docker-stack.swarm.yml` em vez de `docker-compose.prod.yml`.

Diferença principal: Swarm **não builda imagem local** (`build:` não é suportado em
stacks Swarm) — a imagem da API vem pré-buildada do GHCR, publicada automaticamente
pelo workflow `.github/workflows/deploy-stack360.yml` a cada push em `main`.

### 10.1 Habilitar o build automático

1. No GitHub do seu fork: **Settings → Actions → General → Workflow permissions** →
   marque "Read and write permissions" (necessário pro workflow publicar no GHCR).
2. Dê um `git push` em `main` — o workflow builda e publica
   `ghcr.io/<seu-usuario-github>/stack360-api:latest`.
3. Por padrão o pacote fica **privado** no GHCR. Ou torne-o público
   (GitHub → seu perfil → Packages → stack360-api → Package settings → Change visibility),
   ou configure no Portainer uma credencial de registry (Settings → Registries) apontando
   pro GHCR com um Personal Access Token (escopo `read:packages`).

### 10.2 Descobrir os nomes já usados pelo seu Traefik

Antes de criar a stack, confirme (olhando outra stack já rodando, ou com o CLI na VPS):

```bash
docker network ls --filter driver=overlay   # nome da rede externa do Traefik
docker service inspect <algum-servico-com-traefik> --format '{{json .Spec.Labels}}'
# ou olhe os labels de outra stack no Portainer (Stacks > ... > Editor)
```

Você precisa saber: nome da **rede overlay externa**, nome do **certresolver**, e o
**entrypoint** HTTPS (geralmente `websecure`).

### 10.3 Criar a stack no Portainer

**Stacks → Add stack → Repository**, mesmo repositório, mas:
- Compose path: `deploy/docker-stack.swarm.yml`
- **Environment variables**:

  ```
  STACK360_IMAGE=ghcr.io/<seu-usuario-github>/stack360-api:latest
  TRAEFIK_NETWORK=<rede overlay externa do Traefik>
  TRAEFIK_CERTRESOLVER=<certresolver já configurado>
  TRAEFIK_ENTRYPOINT=websecure
  DOMAIN=stack360.seudominio.com.br
  POSTGRES_PASSWORD=<senha forte>
  STACK360_DOCS_HTPASSWD=<ver abaixo>
  STACK360_CORS_ORIGINS=
  STACK360_WEBHOOK_SECRET_KEY=
  ```

  Gere `STACK360_DOCS_HTPASSWD` (hash bcrypt no formato `usuario:hash` que o Traefik
  entende):

  ```bash
  docker run --rm httpd:2.4-alpine htpasswd -nbB admin 'suaSenhaForte'
  ```

- **Deploy the stack.**

### 10.4 Verificar e fazer bootstrap

```bash
curl -s https://stack360.seudominio.com.br/api/v1/health
# -> {"status":"ok","service":"stack360-core"}

CID=$(docker ps --filter "name=stack360_api" --format "{{.ID}}" | head -1)
docker exec "$CID" python -m app.stack360.admin create-workspace --slug stack360-empresas --name "Stack360 Empresas"
docker exec "$CID" python -m app.stack360.admin create-source --workspace stack360-empresas --key minha-app --name "Minha App" --type custom
docker exec "$CID" python -m app.stack360.admin create-api-key --workspace stack360-empresas --source minha-app --name ingest --scopes ingest
docker exec "$CID" python -m app.stack360.admin create-api-key --workspace stack360-empresas --name read --scopes read,mcp
```

### 10.5 Redeploy automático (opcional)

No Portainer: Stacks → `stack360` → copie a URL de **Webhook**. Cole como secret
`PORTAINER_WEBHOOK_URL` no GitHub (Settings → Secrets and variables → Actions) —
cada push em `main` builda, publica no GHCR **e** chama o webhook pra redeployar.
Sem o secret configurado, esse passo é simplesmente pulado (sem erro).
