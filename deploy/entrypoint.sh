#!/bin/sh
# Entrypoint do container da API Stack360:
#   1. espera o Postgres aceitar conexão
#   2. aplica a migration canônica (idempotente — só na 1a vez faz o `stamp`)
#   3. sobe o uvicorn
set -e

echo "[entrypoint] aguardando Postgres..."
python - <<'PY'
import os, sys, time
import psycopg2

url = os.environ["STACK360_DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
for attempt in range(60):
    try:
        psycopg2.connect(url).close()
        print("[entrypoint] Postgres OK")
        break
    except Exception as exc:  # noqa: BLE001
        if attempt == 0:
            print(f"[entrypoint] ainda indisponível: {exc}")
        time.sleep(2)
else:
    sys.exit("[entrypoint] Postgres nunca respondeu")
PY

echo "[entrypoint] migrations..."
# Banco vazio: marca o baseline legado SEM rodar as migrations legadas
# (a cadeia legada não sobe em DB vazio — ver docs/DEPLOY.md).
if ! alembic current 2>/dev/null | grep -q .; then
    echo "[entrypoint] alembic stamp 13b31f818410 (baseline)"
    alembic stamp 13b31f818410
fi
echo "[entrypoint] alembic upgrade aa47386e4e9f (schema stack360)"
alembic upgrade aa47386e4e9f

echo "[entrypoint] iniciando uvicorn..."
exec uvicorn app.stack360.main:app \
    --host 0.0.0.0 --port 8000 \
    --workers "${WEB_CONCURRENCY:-2}" \
    --proxy-headers --forwarded-allow-ips '*'
