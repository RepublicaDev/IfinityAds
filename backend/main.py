import uvicorn
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict

from app.api import router as api_root_router
from app.db.db import db_wrapper

# Configuração de Logging básica
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    try:
        await db_wrapper.connect()
        logger.info("🚀 Conexão com o MongoDB estabelecida com sucesso.")
    except Exception as e:
        logger.error(f"❌ Erro crítico na conexão com Banco: {e}")
    
    yield
    
    # SHUTDOWN
    await db_wrapper.close()
    logger.info("💤 Conexão com o banco encerrada.")

def create_app() -> FastAPI:
    app = FastAPI(
        title="IfinityAds API", 
        description="Backend centralizado para análise de produtos e anúncios",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS TOTAL (Importante para o Render + Vercel)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )

    @app.get("/health", tags=["System"])
    @app.get("/api/v1/health", tags=["System"])
    async def health() -> Dict[str, str]:
        return {
            "status": "online", 
            "environment": os.getenv("ENVIRONMENT", "production")
        }

    # Registro de Rotas
    app.include_router(api_root_router, prefix="/api")

    # Compatibilidade legada (se necessário)
    try:
        from app.api.v1 import router as v1_router
        app.include_router(v1_router, tags=["Compatibility"])
    except ImportError:
        logger.warning("Roteador v1 não encontrado para inclusão direta.")

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # 'app.main:app' garante que o uvicorn use o factory corretamente no Render
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)