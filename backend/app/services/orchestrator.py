import logging
from datetime import datetime
from typing import Optional, Any, Dict, cast
from bson import ObjectId

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
    def db(self) -> Any:
        """Retorna a base de dados do MongoDB com fallback para evitar erros de Pylance."""
        if db_wrapper.database is None:
            raise RuntimeError("Banco de dados não inicializado. Chame connect() primeiro.")
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
        
        # O Pylance pode reclamar se não fizermos o cast ou acesso dinâmico
        result = await self.db["jobs"].insert_one(job_data)
        job_id = str(result.inserted_id)
        
        logger.info(f"Job {job_id} enfileirado para o usuário {user_id}")
        return job_id

    async def process_job(self, job_id: str):
        """Orquestra o fluxo: Scraper -> LLM -> Video Service"""
        try:
            # 1. Recupera do Banco
            job_doc = await self.db["jobs"].find_one({"_id": ObjectId(job_id)})
            if not job_doc:
                logger.error(f"Job {job_id} não encontrado")
                return

            # 2. Atualiza para Processando
            await self.db["jobs"].update_one(
                {"_id": ObjectId(job_id)}, 
                {"$set": {"status": "processing", "updated_at": datetime.utcnow()}}
            )
            
            # --- FLUXO DE IA ---
            # Aqui você deve integrar com o Scraper e o Analyzer que já funcionam
            # script = await self.llm.generate_script(job_doc['product_url'], style=job_doc['style'])
            # video_data = await self.did_service.create_talk("AVATAR_URL", script)
            
            # 3. Finaliza com sucesso (Exemplo)
            await self.db["jobs"].update_one({"_id": ObjectId(job_id)}, {
                "$set": {
                    "status": "completed", 
                    "result_url": "URL_DO_VIDEO_GERADO",
                    "updated_at": datetime.utcnow()
                }
            })
            logger.info(f"✓ Job {job_id} concluído com sucesso.")
            
        except Exception as e:
            logger.error(f"❌ Falha no processamento do Job {job_id}: {e}")
            await self.db["jobs"].update_one(
                {"_id": ObjectId(job_id)}, 
                {"$set": {
                    "status": "failed", 
                    "error": str(e),
                    "updated_at": datetime.utcnow()
                }}
            )