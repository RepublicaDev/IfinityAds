import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Importando routers e o db_wrapper
from app.api.v1 import router as api_router
from app.api.v2 import router as api_v2_router
from app.db.db import db_wrapper

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    await db_wrapper.connect()
    yield
    # SHUTDOWN
    await db_wrapper.close()

def create_app() -> FastAPI:
    app = FastAPI(
        title="IfinityAds Backend",
        lifespan=lifespan
    )

    # Configuração de CORS para Vercel e Local
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # Troque pelas URLs reais no deploy
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rotas
    app.include_router(api_router, prefix="/api/v1", tags=["v1"])
    app.include_router(api_v2_router, prefix="/api/v2", tags=["v2"])

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)