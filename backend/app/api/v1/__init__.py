from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

# Se o Pylance reclamar, verifique se em app/services/product_service.py 
# existe a definição: class ProductScraperService:
from app.services import product_service
from app.services.youtube_analyzer import YouTubeAnalyzer
from app.models.product import ProductResponse

logger = logging.getLogger(__name__)
router = APIRouter()

class ScrapeRequest(BaseModel):
    url: str
    bypass_cache: bool = False

class YoutubeRequest(BaseModel):
    youtube_url: str

@router.post("/products/scrape", response_model=ProductResponse)
async def scrape_single_product(data: ScrapeRequest):
    try:
        # Usando via módulo para garantir que o Pylance encontre
        product = await product_service.ProductScraperService.scrape_product(
            url=data.url, 
            bypass_cache=data.bypass_cache
        )
        return product_service.ProductScraperService.to_response(product)
    except Exception as e:
        logger.error(f"Erro no scrape: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/youtube/analyze")
async def analyze_video(data: YoutubeRequest):
    try:
        analyzer = YouTubeAnalyzer()
        result = await analyzer.analyze(data.youtube_url)
        return result
    except Exception as e:
        logger.error(f"Erro no youtube: {e}")
        raise HTTPException(status_code=400, detail=str(e))