import uvicorn
import os
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Importando os roteadores (que agora são vazios, então não dão erro)
from app.api.v1 import router as api_router
from app.api.v2 import router as api_v2_router
from app.db.db import db_wrapper

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    try:
        await db_wrapper.connect()
    except Exception as e:
        print(f"Aviso: Não foi possível conectar ao banco no startup: {e}")
    yield
    # SHUTDOWN
    await db_wrapper.close()

def create_app() -> FastAPI:
    app = FastAPI(title="IfinityAds Backend", lifespan=lifespan)

    # Rota de Health Check (Prioritária para o Render)
    @app.get("/api/v1/health")
    async def health_check():
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "healthy"}
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Incluindo os roteadores vazios
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(api_v2_router, prefix="/api/v2")

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)