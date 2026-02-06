from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.auth import get_current_user
from app.services.orchestrator import AdOrchestrator
from app.core.tasks import process_job_task
from typing import Any, cast, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

class JobCreateRequest(BaseModel):
    product_url: str
    youtube_url: Optional[str] = None
    style: str = "charismatic_fomo"

@router.post("/jobs")
async def create_job(req: JobCreateRequest, user: Any = Depends(get_current_user)):
    # Tipagem explícita ajuda o Pylance
    orchestrator: AdOrchestrator = AdOrchestrator()
    
    user_id = "unknown"
    if isinstance(user, dict):
        user_id = str(user.get("uid") or user.get("id", "unknown"))
    elif hasattr(user, "uid"):
        user_id = str(user.uid)

    # Agora o Pylance encontrará o método porque o definimos no Service acima
    job_id = await orchestrator.enqueue_job(
        product_url=req.product_url, 
        youtube_url=req.youtube_url, 
        style=req.style, 
        user_id=user_id
    )

    try:
        cast(Any, process_job_task).delay(job_id)
    except Exception as e:
        logger.warning(f"Falha no Celery, tentando execução local: {e}")
        # Chamada corrigida: agora condiz com o Orchestrator
        asyncio.create_task(orchestrator.process_job(job_id=job_id))

    return {"job_id": job_id, "status": "queued"}