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
    user_id = "test_deploy_user"

    try:
        # Agora o método enqueue_job existe no orchestrator.py
        job_id = await orchestrator.enqueue_job(
            product_url=req.product_url, 
            youtube_url=req.youtube_url, 
            style=req.style, 
            user_id=user_id
        )

        try:
            # Tenta disparar via Celery
            cast(Any, process_job_task).delay(job_id)
        except Exception as e:
            logger.warning(f"Celery offline, usando Background Task: {e}")
            # Fallback para tarefa em segundo plano do Python
            asyncio.create_task(orchestrator.process_job(job_id=job_id))

        return {"job_id": job_id, "status": "queued"}
    except Exception as e:
        logger.error(f"Erro ao criar job: {e}")
        raise HTTPException(status_code=500, detail=str(e))