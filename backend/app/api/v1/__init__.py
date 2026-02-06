from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

# Importações absolutas
from app.services.product_service import ProductScraperService
from app.services.youtube_analyzer import YouTubeAnalyzer
from app.models.product import ProductResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# --- MODELOS DE DADOS ---
class ScrapeRequest(BaseModel):
    url: str
    bypass_cache: bool = False

class YoutubeRequest(BaseModel):
    youtube_url: str
    force_reanalysis: bool = False

# --- ENDPOINTS ---

@router.post("/products/scrape", response_model=ProductResponse)
async def scrape_single_product(data: ScrapeRequest):
    try:
        product = await ProductScraperService.scrape_product(
            url=data.url, 
            bypass_cache=data.bypass_cache
        )
        return ProductScraperService.to_response(product)
    except Exception as e:
        logger.error(f"Erro no endpoint scrape: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/youtube/analyze")
async def analyze_video(data: YoutubeRequest):
    try:
        analyzer = YouTubeAnalyzer()
        
        # AJUSTE PARA EVITAR O ERRO DO PYLANCE:
        # Se o seu YouTubeAnalyzer não aceita force_reanalysis ainda,
        # passamos apenas a URL. 
        result = await analyzer.analyze(data.youtube_url)
        
        return result
    except Exception as e:
        logger.error(f"Erro no endpoint youtube: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))