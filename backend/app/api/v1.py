from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.core.auth import get_current_user
from app.services.orchestrator import AdOrchestrator

router = APIRouter()

class CreateAdRequest(BaseModel):
    product_url: str
    youtube_url: str | None = None
    style: str | None = "charismatic_fomo"

@router.post("/ads/create")
async def create_ad(req: CreateAdRequest, background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    orchestrator = AdOrchestrator()
    job_id = await orchestrator.enqueue_job(req.product_url, req.youtube_url, req.style, user_id=user.get('uid'))
    # Use background task to execute worker
    background_tasks.add_task(orchestrator.process_job, job_id)
    return {"status": "processing", "job_id": job_id, "owner": user.get('uid')}

@router.get("/ads/status/{job_id}")
async def status(job_id: str):
    return {"job_id": job_id, "status": "queued"}

@router.get("/health")
async def health():
    return {"status": "ok"}
