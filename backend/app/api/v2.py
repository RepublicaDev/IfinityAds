from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.auth import get_current_user
from app.services.orchestrator import AdOrchestrator
from app.tasks import process_job_task
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class JobCreateRequest(BaseModel):
    product_url: str
    youtube_url: str | None = None
    style: str | None = "charismatic_fomo"


@router.post("/jobs")
async def create_job(req: JobCreateRequest, user=Depends(get_current_user)):
    orchestrator = AdOrchestrator()
    job_id = await orchestrator.enqueue_job(req.product_url, req.youtube_url, req.style, user.get("uid"))

    # Enfileira tarefa no Celery
    try:
        process_job_task.delay(job_id)
    except Exception as e:
        logger.warning(f"Falha ao enfileirar no Celery, tentando execução local: {e}")
        # Fallback: execute localmente em background
        import asyncio
        asyncio.create_task(orchestrator.process_job(job_id))

    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, user=Depends(get_current_user)):
    from app.db import db
    if not db:
        raise HTTPException(status_code=503, detail="Database não disponível")

    doc = await db.render_logs.find_one({"job_id": job_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    return {"job_id": job_id, "status": doc.get("status"), "result": doc.get("result")}
