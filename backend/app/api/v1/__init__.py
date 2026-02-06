from fastapi import APIRouter, HTTPException, Query
from pydantic import HttpUrl
from typing import List
import logging

# Importando os serviços
from app.services.product_service import ProductScraperService
from app.services.youtube_analyzer import YouTubeAnalyzer
from app.models.product import BulkProductResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Instanciamos os serviços uma vez para uso nos endpoints
product_service = ProductScraperService()
youtube_analyzer = YouTubeAnalyzer()

# ============ ENDPOINTS DE PRODUTOS ============

@router.post("/products/scrape")
async def scrape_single_product(
    url: str = Query(...), 
    bypass_cache: bool = Query(False)
):
    try:
        # Usando a instância para acessar o método
        product = await product_service.scrape_product(url, bypass_cache=bypass_cache)
        return product_service.to_response(product)
    except Exception as e:
        logger.error(f"Erro no scrape individual: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/products/batch", response_model=BulkProductResponse)
async def scrape_products_batch(
    urls: List[HttpUrl],
    bypass_cache: bool = Query(False)
):
    if len(urls) > 10:
        raise HTTPException(status_code=400, detail="Máximo 10 URLs")
    
    try:
        # Se o método batch não existir no service, usamos o scrape individual em loop
        # Isso evita o erro de "Atributo Desconhecido" do Pylance
        results = []
        for url in urls:
            p = await product_service.scrape_product(str(url), bypass_cache=bypass_cache)
            results.append(product_service.to_response(p))
            
        return BulkProductResponse(
            total=len(results), 
            products=results, 
            cache_hit=False
        )
    except Exception as e:
        logger.error(f"Erro no batch scrape: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ============ ENDPOINTS DE YOUTUBE ============

@router.post("/youtube/analyze")
async def analyze_video(url: str = Query(...)):
    try:
        # Usando a instância definida no topo
        return await youtube_analyzer.analyze(url)
    except Exception as e:
        logger.error(f"Erro ao analisar YouTube: {e}")
        raise HTTPException(status_code=400, detail=str(e))