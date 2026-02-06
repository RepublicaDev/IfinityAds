import uvicorn
import os
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.v1 import router as api_router
from app.api.v2 import router as api_v2_router
from app.db.db import db_wrapper

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: Conecta ao banco antes de aceitar requisições
    await db_wrapper.connect()
    yield
    # SHUTDOWN: Limpa a conexão ao desligar
    await db_wrapper.close()

def create_app() -> FastAPI:
    app = FastAPI(
        title="IfinityAds Backend",
        version="2.0.0",
        lifespan=lifespan
    )

    # Health Check para o Render (Resolve o erro 404 e Timeout)
    @app.get("/api/v1/health", tags=["System"])
    async def health_check():
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "healthy", "service": "ifinityads-api"}
        )

    # Rota raiz para evitar 404 caso alguém acesse a URL limpa
    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "IfinityAds API is running"}

    # Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Inclusão de Rotas
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(api_v2_router, prefix="/api/v2")

    return app

app = create_app()

if __name__ == "__main__":
    # No Render, a porta é passada via variável de ambiente $PORT
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)