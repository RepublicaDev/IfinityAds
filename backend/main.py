import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Importamos o roteador central que unifica v1 e v2
from app.api import router as api_root_router
from app.db.db import db_wrapper

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: Conexão com o banco
    try:
        await db_wrapper.connect()
        print("🚀 Conexão com o MongoDB estabelecida com sucesso.")
    except Exception as e:
        print(f"❌ Erro crítico na conexão com Banco: {e}")
    
    yield
    
    # SHUTDOWN: Fechamento da conexão
    await db_wrapper.close()
    print("💤 Conexão com o banco encerrada.")

def create_app() -> FastAPI:
    app = FastAPI(
        title="IfinityAds API", 
        description="Backend centralizado para análise de produtos e anúncios",
        version="1.0.0",
        lifespan=lifespan
    )

    # 1. CONFIGURAÇÃO DE CORS TOTAL
    # O uso do "*" é necessário para aceitar as URLs de Preview da Vercel
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )

    # 2. ROTAS DE SAÚDE (HEALTH CHECK)
    # Registradas em múltiplos caminhos para garantir que o Render e o Front encontrem
    @app.get("/health", tags=["System"])
    @app.get("/api/v1/health", tags=["System"])
    async def health():
        return {"status": "online", "environment": os.getenv("ENVIRONMENT", "production")}

    # 3. INCLUSÃO DO ROTEADOR UNIFICADO
    # Isso registra automaticamente /api/v1/... e /api/v2/...
    app.include_router(api_root_router, prefix="/api")

    # 4. COMPATIBILIDADE EXTRA
    # Caso seu frontend esteja chamando diretamente /products/scrape sem o /api/v1
    from app.api.v1 import router as v1_router
    app.include_router(v1_router, tags=["Compatibility"])

    return app

app = create_app()

if __name__ == "__main__":
    # O Render injeta automaticamente a porta na variável de ambiente PORT
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)