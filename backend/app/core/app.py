from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.cache import cache
from app.services.scrapers.base import ScraperRegistry
from app.services.scrapers.generic_scraper import GenericEcomScraper
from app.models.product import Marketplace
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando InfinityAd Backend...")
    await cache.connect()
    
    # Registro manual dos scrapers (Substitui o .initialize que dava erro)
    ScraperRegistry.register(Marketplace.CUSTOM, GenericEcomScraper)
    
    logger.info("✓ Backend pronto para receber requisições")
    yield
    await cache.disconnect()
    logger.info("✓ Backend finalizado")

def create_app() -> FastAPI:
    app = FastAPI(
        title="InfinityAd API",
        description="API para geração de anúncios com IA",
        version="2.0.0",
        lifespan=lifespan
    )

    origins = [
        "https://republicadevifinityads.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return app