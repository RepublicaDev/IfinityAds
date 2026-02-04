from fastapi import FastAPI
from app.api.v1 import router as api_router

app = FastAPI(title="InfinityAd AI - Backend")
app.include_router(api_router, prefix="/api/v1")

# For development: uvicorn backend.main:app --reload --port 8000
