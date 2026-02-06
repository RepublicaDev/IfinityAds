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
    try:
        await db_wrapper.connect()
    except Exception as e:
        print(f"Erro na conexão com Banco: {e}")
    yield
    await db_wrapper.close()

def create_app() -> FastAPI:
    app = FastAPI(title="IfinityAds Backend", lifespan=lifespan)

    # CONFIGURAÇÃO DE CORS TOTAL
    # Usar allow_origins=["*"] é a forma mais segura de garantir que 
    # URLs de preview da Vercel funcionem sem erro.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rotas de Saúde com suporte a múltiplos caminhos
    @app.get("/health")
    @app.get("/api/v1/health")
    async def health_check():
        return {"status": "healthy"}

    # Roteamento
    # Incluímos o router v1 com e sem prefixo para bater com as chamadas do seu front
    app.include_router(api_router, prefix="/api/v1", tags=["v1"])
    app.include_router(api_router, tags=["v1-compat"])
    app.include_router(api_v2_router, prefix="/api/v2", tags=["v2"])

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # Passamos o objeto app diretamente
    uvicorn.run(app, host="0.0.0.0", port=port)