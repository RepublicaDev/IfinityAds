from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, HttpUrl
from app.core.auth import get_current_user
from app.services.orchestrator import AdOrchestrator
from app.services.product_service import ProductScraperService
from app.services.youtube_analyzer import YouTubeAnalyzer
from app.models.product import ProductCreateRequest, ProductResponse, BulkProductResponse
from app.models.youtube import AnalysisRequest, AnalysisResponse
import logging
import time

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateAdRequest(BaseModel):
    product_url: str
    youtube_url: str | None = None
    style: str | None = "charismatic_fomo"


# ============ PRODUCT ENDPOINTS ============

@router.post("/products/scrape", response_model=ProductResponse)
async def scrape_product(
    req: ProductCreateRequest,
    bypass_cache: bool = Query(False),
    user=Depends(get_current_user)
):
    """
    Scrapa informações detalhadas de um produto.
    Suporta: Shopee, AliExpress, Shein.
    
    - **url**: URL completa do produto
    - **bypass_cache**: Ignora cache e busca dados frescos
    """
    try:
        product = await ProductScraperService.scrape_product(
            req.url, 
            bypass_cache=bypass_cache
        )
        return ProductScraperService.to_response(product)
    except Exception as e:
        logger.error(f"Erro ao scrapear: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/products/batch", response_model=BulkProductResponse)
async def scrape_products_batch(
    urls: list[HttpUrl],
    bypass_cache: bool = Query(False),
    user=Depends(get_current_user)
):
    """
    Scrapa múltiplos produtos em paralelo.
    Máximo de 10 URLs por requisição.
    """
    if len(urls) > 10:
        raise HTTPException(status_code=400, detail="Máximo 10 URLs por requisição")
    
    try:
        products = await ProductScraperService.scrape_products_batch(
            [str(u) for u in urls],
            bypass_cache=bypass_cache
        )
        
        responses = [ProductScraperService.to_response(p) for p in products]
        return BulkProductResponse(
            total=len(responses),
            products=responses,
            cache_hit=False
        )
    except Exception as e:
        logger.error(f"Erro ao scrapear batch: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/cache/{marketplace}")
async def clear_cache(
    marketplace: str,
    user=Depends(get_current_user)
):
    """Limpa cache para um marketplace específico ou 'all' para tudo."""
    try:
        from app.models.product import Marketplace
        
        if marketplace.lower() == "all":
            await ProductScraperService.invalidate_cache()
            return {"message": "Cache total removido"}
        
        mp = Marketplace(marketplace.lower())
        await ProductScraperService.invalidate_cache(mp)
        return {"message": f"Cache removido para {marketplace}"}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Marketplace inválido: {marketplace}")


# ============ YOUTUBE ANALYSIS ENDPOINTS ============

@router.post("/youtube/analyze", response_model=AnalysisResponse)
async def analyze_youtube_video(
    req: AnalysisRequest,
    user=Depends(get_current_user)
):
    """
    Analisa vídeo YouTube com NLP avançado.
    
    - **youtube_url**: URL completa do vídeo
    - **force_reanalysis**: Se True, ignora cache anterior
    
    Retorna:
    - Sentimento geral (positivo/negativo/neutro)
    - Score de sentimento (-1 a +1)
    - Tópicos identificados
    - Entidades (marcas, produtos)
    - Aspectos positivos e negativos
    - Recomendações para anúncio
    """
    try:
        analyzer = YouTubeAnalyzer()
        start = time.time()
        
        analysis = await analyzer.analyze(
            req.youtube_url,
            force_reanalysis=req.force_reanalysis
        )
        
        # Salva no histórico para ML
        try:
            await analyzer.save_to_history(analysis, tags=["api_analysis"])
        except Exception as e:
            logger.warning(f"Falha ao salvar histórico: {e}")
        
        processing_time = int((time.time() - start) * 1000)
        response = analyzer.to_response(analysis)
        response.processing_time_ms = processing_time
        
        logger.info(f"✓ Análise YouTube concluída: {analysis.video_id} em {processing_time}ms")
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao analisar YouTube: {e}")
        raise HTTPException(status_code=500, detail="Erro ao analisar vídeo")


@router.get("/youtube/analysis/{video_id}")
async def get_analysis_history(
    video_id: str,
    user=Depends(get_current_user)
):
    """Recupera análise anterior de um vídeo do histórico."""
    from app.db import db
    
    if not db:
        raise HTTPException(status_code=503, detail="Database não disponível")
    
    try:
        history = await db.youtube_analyses.find_one(
            {"analysis.video_id": video_id},
            sort=[("created_at", -1)]
        )
        
        if not history:
            raise HTTPException(status_code=404, detail="Análise não encontrada")
        
        return {
            "video_id": video_id,
            "analysis": history.get("analysis"),
            "created_at": history.get("created_at"),
            "tags": history.get("tags", [])
        }
    except Exception as e:
        logger.error(f"Erro ao recuperar histórico: {e}")
        raise HTTPException(status_code=500, detail="Erro ao recuperar análise")


# ============ AD CREATION ENDPOINTS ============

@router.post("/ads/create")
async def create_ad(
    req: CreateAdRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user)
):
    """
    Cria um anúncio baseado em URL de produto e vídeo YouTube.
    
    - **product_url**: URL do produto (Shopee, AliExpress, Shein)
    - **youtube_url**: URL de vídeo análogo (opcional)
    - **style**: Estilo do anúncio ("charismatic_fomo", "urgency", etc.)
    """
    orchestrator = AdOrchestrator()
    job_id = await orchestrator.enqueue_job(
        req.product_url,
        req.youtube_url,
        req.style,
        user_id=user.get('uid')
    )
    background_tasks.add_task(orchestrator.process_job, job_id)
    return {"status": "processing", "job_id": job_id, "owner": user.get('uid')}


@router.get("/ads/status/{job_id}")
async def status(job_id: str, user=Depends(get_current_user)):
    """Obtém status de um job de criação de anúncio."""
    return {"job_id": job_id, "status": "queued"}


# ============ HEALTH CHECK ============

@router.get("/health")
async def health():
    """Health check endpoint."""
    from app.core.cache import cache
    redis_status = "connected" if cache.is_connected else "disconnected"
    return {
        "status": "ok",
        "redis": redis_status,
        "version": "2.0.0"
    }
