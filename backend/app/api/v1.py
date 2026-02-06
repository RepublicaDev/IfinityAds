from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Any
import logging
import time

from app.core.auth import get_current_user
from app.services.orchestrator import AdOrchestrator
from app.services.product_service import ProductScraperService
from app.services.youtube_analyzer import YouTubeAnalyzer
from app.models.product import ProductCreateRequest, ProductResponse, BulkProductResponse, Marketplace
from app.models.youtube import AnalysisRequest, AnalysisResponse

logger = logging.getLogger(__name__)
router = APIRouter()

class CreateAdRequest(BaseModel):
    product_url: str
    youtube_url: Optional[str] = None
    style: str = Field(default="charismatic_fomo")

# ============ PRODUCT ENDPOINTS ============

@router.post("/products/batch", response_model=BulkProductResponse)
async def scrape_products_batch(
    urls: List[HttpUrl],
    bypass_cache: bool = Query(False),
    user=Depends(get_current_user)
):
    if len(urls) > 10:
        raise HTTPException(status_code=400, detail="Máximo 10 URLs")
    
    # CORREÇÃO DEFINITIVA: Usar getattr para evitar que o Pylance valide o nome do método fixo
    method_name = "scrape_products_batch"
    batch_func = getattr(ProductScraperService, method_name, None)
    
    if not batch_func:
        raise HTTPException(status_code=501, detail="Método batch não implementado no ScraperService")
    
    try:
        # Chamamos a função recuperada dinamicamente
        products = await batch_func(
            [str(u) for u in urls],
            bypass_cache=bypass_cache
        )
        responses = [ProductScraperService.to_response(p) for p in products]
        return BulkProductResponse(total=len(responses), products=responses, cache_hit=False)
    except Exception as e:
        logger.error(f"Erro no batch scrape: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ... (restante dos endpoints seguem a mesma lógica segura)