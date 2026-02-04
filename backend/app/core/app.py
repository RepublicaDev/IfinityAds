"""
Configuração centralizada e startup/shutdown do app FastAPI com suporte a CORS.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Importação vital
from app.core.cache import cache
from app.services.product_service import ProductScraperService
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia startup e shutdown da aplicação."""
    logger.info("🚀 Iniciando InfinityAd Backend...")
    
    # Conecta ao Redis
    await cache.connect()
    
    # Registra scrapers
    ProductScraperService.initialize()
    
    logger.info("✓ Backend pronto para receber requisições")
    yield
    
    logger.info("🛑 Encerrando Backend...")
    await cache.disconnect()
    logger.info("✓ Backend finalizado")

def create_app() -> FastAPI:
    """Factory para criar aplicação FastAPI."""
    app = FastAPI(
        title="InfinityAd API",
        description="API para geração de anúncios com IA",
        version="2.0.0",
        lifespan=lifespan
    )

    # ===== CONFIGURAÇÃO DE CORS =====
    # Lista de domínios que podem acessar esta API
    origins = [
        "https://republicadevifinityads.vercel.app", # Seu domínio de produção
        "http://localhost:3000",                     # Desenvolvimento local (React)
        "http://localhost:5173",                     # Desenvolvimento local (Vite)
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,             # Permite apenas os domínios da lista
        allow_credentials=True,
        allow_methods=["*"],                # Permite todos os métodos (GET, POST, etc)
        allow_headers=["*"],                # Permite todos os headers
    )
    # ================================

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return app