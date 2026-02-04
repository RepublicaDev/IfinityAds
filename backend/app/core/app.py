"""
Configuração centralizada e startup/shutdown do app FastAPI.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.cache import cache
from app.services.product_service import ProductScraperService
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia startup e shutdown da aplicação.
    """
    # Startup
    logger.info("🚀 Iniciando InfinityAd Backend...")
    
    # Conecta ao Redis
    await cache.connect()
    
    # Registra scrapers
    ProductScraperService.initialize()
    
    logger.info("✓ Backend pronto para receber requisições")
    
    yield
    
    # Shutdown
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
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return app
