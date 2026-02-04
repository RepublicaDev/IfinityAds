"""
InfinityAd Backend - Main Entry Point
FastAPI application with lifespan management and advanced architecture
"""
from app.core.app import create_app
from app.api.v1 import router as api_router
from app.api.v2 import router as api_v2_router

# Criar aplicação com gerenciamento de lifespan
app = create_app()

# Incluir routers
app.include_router(api_router, prefix="/api/v1", tags=["v1"])
app.include_router(api_v2_router, prefix="/api/v2", tags=["v2"])

# CORS (opcional, descomentar se frontend em domínio diferente)
# from fastapi.middleware.cors import CORSMiddleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173", "https://seu-frontend.com"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
