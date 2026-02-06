from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, cast
import logging
import asyncio

from app.services.orchestrator import AdOrchestrator
from app.core.tasks import process_job_task

logger = logging.getLogger(__name__)
router = APIRouter()

class JobCreateRequest(BaseModel):
    product_url: str
    youtube_url: Optional[str] = None
    style: str = "charismatic_fomo"

@router.post("/jobs")
async def create_job(req: JobCreateRequest):
    orchestrator = AdOrchestrator()
    
    # User ID fixo para teste de infraestrutura
    user_id = "test_deploy_user"

    try:
        job_id = await orchestrator.enqueue_job(
            product_url=req.product_url, 
            youtube_url=req.youtube_url, 
            style=req.style, 
            user_id=user_id
        )

        # Tenta disparar via Celery, se falhar, usa background task do FastAPI
        try:
            cast(Any, process_job_task).delay(job_id)
        except Exception as e:
            logger.warning(f"Celery offline, processando via background task: {e}")
            asyncio.create_task(orchestrator.process_job(job_id=job_id))

        return {"job_id": job_id, "status": "queued"}
    except Exception as e:
        logger.error(f"Erro ao criar job: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao enfileirar job")