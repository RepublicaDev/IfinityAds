import logging
from datetime import datetime
from typing import Optional, Any, Dict
from bson import ObjectId

# Importamos o wrapper em vez da variável 'db' solta
from app.db.db import db_wrapper
from app.services.llm_service import LLMService
from app.services.video_did import DIDService
from app.services.video_sadtalker import SadTalkerService

logger = logging.getLogger(__name__)

class AdOrchestrator:
    def __init__(self):
        self.llm = LLMService()
        self.did_service = DIDService()
        self.sadtalker_service = SadTalkerService()

    @property
    def db(self):
        """Acesso dinâmico ao banco de dados através do wrapper."""
        return db_wrapper.database

    async def enqueue_job(self, product_url: str, youtube_url: Optional[str], style: str, user_id: str) -> str:
        job_data = {
            "user_id": user_id,
            "product_url": product_url,
            "youtube_url": youtube_url,
            "style": style,
            "status": "queued",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Uso do self.db (que aponta para db_wrapper.database)
        result = await self.db.jobs.insert_one(job_data)
        job_id = str(result.inserted_id)
        
        logger.info(f"Job {job_id} persistido para o usuário {user_id}")
        return job_id

    async def process_job(self, job_id: str, product_url: Optional[str] = None):
        try:
            # 1. Recupera do Banco
            job_doc = await self.db.jobs.find_one({"_id": ObjectId(job_id)})
            if not job_doc:
                logger.error(f"Job {job_id} não encontrado")
                return

            # 2. Atualiza status
            await self.db.jobs.update_one(
                {"_id": ObjectId(job_id)}, 
                {"$set": {"status": "processing", "updated_at": datetime.utcnow()}}
            )
            
            # --- Lógica de IA aqui ---
            # Ex: script = await self.llm.generate(...)

            # 3. Finaliza com sucesso
            await self.db.jobs.update_one({"_id": ObjectId(job_id)}, {
                "$set": {
                    "status": "completed", 
                    "result_url": "URL_FINAL_AQUI",
                    "updated_at": datetime.utcnow()
                }
            })
            
        except Exception as e:
            logger.error(f"Falha no processamento: {e}")
            await self.db.jobs.update_one(
                {"_id": ObjectId(job_id)}, 
                {"$set": {"status": "failed", "error": str(e)}}
            )