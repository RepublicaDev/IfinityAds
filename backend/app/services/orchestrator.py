import logging
from datetime import datetime
from typing import Optional, Any, Dict
from bson import ObjectId  # Certifique-se de ter 'pymongo' ou 'motor' instalado

from app.db import db  # Sua instância do banco
# Importe seus outros serviços aqui (LLM, Video, etc)
from app.services.llm_service import LLMService
from app.services.video_did import DIDService
from app.services.video_sadtalker import SadTalkerService

# DEFINIÇÃO DO LOGGER (Resolve o erro "logger" não definido)
logger = logging.getLogger(__name__)

class AdOrchestrator:
    def __init__(self):
        self.llm = LLMService()
        self.did_service = DIDService()
        self.sadtalker_service = SadTalkerService()

    async def enqueue_job(self, product_url: str, youtube_url: Optional[str], style: str, user_id: str) -> str:
        """Salva os parâmetros reais e retorna o ID para o Worker."""
        # Verificação de segurança para o DB
        if db is None:
            raise RuntimeError("Database não inicializado")

        job_data = {
            "user_id": user_id,
            "product_url": product_url,
            "youtube_url": youtube_url,
            "style": style,
            "status": "queued",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insere no MongoDB (usando motor/pymongo)
        result = await db.jobs.insert_one(job_data)
        job_id = str(result.inserted_id)
        
        logger.info(f"Job {job_id} persistido para o usuário {user_id}")
        return job_id

    async def process_job(self, job_id: str, product_url: Optional[str] = None):
        """Busca os dados reais salvos no enqueue_job e executa."""
        if db is None:
            logger.error("Database offline durante process_job")
            return

        # 1. Recupera do Banco usando o ObjectId
        try:
            job_doc = await db.jobs.find_one({"_id": ObjectId(job_id)})
        except Exception as e:
            logger.error(f"ID de Job inválido {job_id}: {e}")
            return

        if not job_doc:
            logger.error(f"Job {job_id} não encontrado no DB")
            return

        # 2. Atualiza para 'processing'
        await db.jobs.update_one(
            {"_id": ObjectId(job_id)}, 
            {"$set": {"status": "processing", "updated_at": datetime.utcnow()}}
        )
        
        try:
            # Pega os dados reais vindos do documento do banco
            p_url = job_doc.get("product_url", product_url)
            style = job_doc.get("style", "charismatic_fomo")
            
            # --- FLUXO DE EXECUÇÃO ---
            # Exemplo: script = await self.llm.generate_ad_script({"url": p_url}, style)
            
            # 3. Sucesso: Atualiza o status final
            await db.jobs.update_one({"_id": ObjectId(job_id)}, {
                "$set": {
                    "status": "completed", 
                    "result_url": "link_do_video_final",
                    "updated_at": datetime.utcnow()
                }
            })
            logger.info(f"Job {job_id} concluído com sucesso")

        except Exception as e:
            logger.error(f"Erro ao processar Job {job_id}: {e}")
            await db.jobs.update_one(
                {"_id": ObjectId(job_id)}, 
                {"$set": {"status": "failed", "error": str(e), "updated_at": datetime.utcnow()}}
            )
            raise e