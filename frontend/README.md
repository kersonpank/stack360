# Stakeholder Intelligence 360 Frontend

Frontend real em Next.js para a Stakeholder Intelligence API.

## Setup

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Abra `http://localhost:3000`.

## Ambiente

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
NEXT_PUBLIC_USE_MOCKS=true
```

- `NEXT_PUBLIC_USE_MOCKS=true`: usa dados mockados locais.
- `NEXT_PUBLIC_USE_MOCKS=false`: consome a API real em `NEXT_PUBLIC_API_BASE_URL`.

## Scripts

```bash
npm run dev
npm run lint
npm run build
```

## Endpoints usados

- `GET /api/v1/health`
- `GET /api/v1/system/normalization-status`
- `GET /api/v1/stakeholders/search?q=`
- `GET /api/v1/stakeholders/{contact_id}`
- `GET /api/v1/stakeholders/{contact_id}/conversations`
- `GET /api/v1/stakeholders/{contact_id}/timeline`
- `GET /api/v1/stakeholders/{contact_id}/opportunities`
- `GET /api/v1/conversations/{conversation_id}/messages?limit=100&offset=0&order=desc`

## Arquitetura de dados

Componentes consomem apenas tipos UI. A API real passa por:

`API real -> adapters.ts -> tipos UI -> componentes`

Os tipos API ficam em `src/lib/types.ts`, os mapeamentos em `src/lib/adapters.ts`, e o client em `src/lib/api.ts`.
