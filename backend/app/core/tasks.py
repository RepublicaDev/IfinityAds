from app.core.celery_app import celery_app
from celery.utils.log import get_task_logger
from app.services.orchestrator import AdOrchestrator
import asyncio

logger = get_task_logger(__name__)

@celery_app.task(bind=True)
def process_job_task(self, job_id: str):
    logger.info(f"[celery] Iniciando job {job_id}")
    orchestrator = AdOrchestrator()
    try:
        # Usamos asyncio.run que é mais limpo para scripts/tasks
        asyncio.run(orchestrator.process_job(job_id=job_id))
        
        logger.info(f"[celery] Job concluído {job_id}")
        return {"job_id": job_id, "status": "done"}
    except Exception as e:
        logger.error(f"[celery] Erro no job {job_id}: {e}")
        raise