# InfinityAd AI (MVP)

Arquitetura monorepo com `backend/` (FastAPI) e `frontend/` (React + Vite).

Quick start (dev):

- Backend: cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000
- Frontend: cd frontend && npm install && npm run dev

Security: coloque `firebase-key.json` em `backend/` e configure `.env` usando `backend/.env.example`.

Estrutura:

```
infinity-ad-ai/
├── backend/                # FastAPI app
├── frontend/               # React + Vite app
├── docker-compose.yml      # Local simulation
└── README.md
```
