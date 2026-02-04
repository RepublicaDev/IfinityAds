InfinityAd AI - Backend

This folder contains the FastAPI backend for InfinityAd AI.


# InfinityAd Backend - Deploy & Run

Rápido guia para executar o backend localmente e em produção.

## Variáveis de ambiente (mínimas)
- `MONGO_URI` - MongoDB connection string
- `REDIS_URL` - Redis URL (ex: redis://localhost:6379/0)
- `CELERY_BROKER_URL` - (opcional) broker para Celery, por padrão usa `REDIS_URL`
- `CELERY_RESULT_BACKEND` - (opcional) result backend para Celery, por padrão usa `REDIS_URL`
- `HEYGEN_API_KEY`, `QWEN_API_KEY` - chaves de serviços de IA (se usadas)
- `VITE_BACKEND_URL` - URL do backend para o frontend

## Setup local (venv)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Rodar a API (desenvolvimento)

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

A API v1 ficará em `/api/v1` e a v2 em `/api/v2`.

## Rodar Celery Worker

Certifique-se de ter `REDIS_URL` (ou `CELERY_BROKER_URL`) apontando para um Redis acessível.

```bash
# a partir de backend/
# opção 1: comando direto (recomendado)
celery -A app.core.celery_app.celery_app worker --loglevel=info

# alternativa usando python -m
python -m celery -A app.core.celery_app.celery_app worker --loglevel=info
```

## Comandos úteis

Limpar cache Redis (via endpoint API): `DELETE /api/v1/cache/{marketplace}`
Criar job (v2): `POST /api/v2/jobs` com body JSON `{ "product_url": "...", "youtube_url": "..." }`
Consultar job: `GET /api/v2/jobs/{job_id}`

## Docker / docker-compose

Você pode apontar um `docker-compose.yml` para usar serviços Redis e MongoDB, e executar o worker como serviço separado. Exemplo resumido:

```yaml
services:
	backend:
		build: ./backend
		ports: ["8000:8000"]
		env_file: ./backend/.env
	redis:
		image: redis:7
		ports: ["6379:6379"]
	worker:
		build: ./backend
		command: celery -A app.core.celery_app.celery_app worker --loglevel=info
		depends_on:
			- redis
```

## Observações
- Defina variáveis sensíveis em seu provedor de deploy (Vercel, Render, Railway, etc.).
- Em produção, use um broker Redis gerenciado e configure segurança (autenticação/ACL, TLS).
- Monitore filas e tarefas (ex.: Flower, Prometheus) para produção.

Shopee Scraper

A site-specific Shopee scraper está em `app/services/shopee_scraper.py`. Ela tenta parsear structured data (`application/ld+json`), objetos JS embutidos e faz fallback para OpenGraph/meta tags.

Há testes unitários em `backend/tests/test_shopee_scraper.py` usando o fixture `backend/tests/fixtures/shopee_sample.html`.


Shopee Scraper

A site-specific Shopee scraper was added at `app/services/shopee_scraper.py`. It attempts to parse structured data (`application/ld+json`), embedded JS product objects, and falls back to OpenGraph/meta tags.

There are unit tests in `backend/tests/test_shopee_scraper.py` using an example fixture `backend/tests/fixtures/shopee_sample.html`.
