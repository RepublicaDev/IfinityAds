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

    # 1. MIDDLEWARE CORS (AJUSTADO)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "https://republicadevifinityads.vercel.app", # REMOVIDA A BARRA FINAL
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # 2. ROTAS DE SAÚDE (Compatibilidade dupla)
    @app.get("/health", tags=["System"])
    @app.get("/api/v1/health", tags=["System"])
    async def health_check():
        return {"status": "healthy", "service": "ifinityads-api"}

    # 3. ROTEAMENTO
    # O Front está chamando /products/scrape. 
    # Ao incluir sem prefixo também, garantimos que funcione.
    app.include_router(api_router, prefix="/api/v1", tags=["v1"])
    app.include_router(api_router, tags=["v1-compat"]) # Suporte para chamadas sem /api/v1
    
    app.include_router(api_v2_router, prefix="/api/v2", tags=["v2"])

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # Importante: usar a variável app diretamente ou a string
    uvicorn.run(app, host="0.0.0.0", port=port)