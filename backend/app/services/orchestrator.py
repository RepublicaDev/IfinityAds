import logging
import asyncio
from datetime import datetime
from typing import Optional, Any, Dict, cast
from bson import ObjectId

from app.db.db import db_wrapper
from app.services.llm_service import LLMService
from app.services.video_did import DIDService
from app.services.video_sadtalker import SadTalkerService
from app.services.scrapers.base import ScraperRegistry

logger = logging.getLogger(__name__)

class AdOrchestrator:
    def __init__(self):
        self.llm = LLMService()
        self.did_service = DIDService()
        self.sadtalker_service = SadTalkerService()

    @property
    def db(self) -> Any:
        """Acesso seguro ao banco de dados para o Pylance."""
        if db_wrapper.database is None:
            raise RuntimeError("Conexão com MongoDB não iniciada.")
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
        
        result = await self.db["jobs"].insert_one(job_data)
        return str(result.inserted_id)

    async def process_job(self, job_id: str):
        """Executa o pipeline: Scraper -> LLM -> D-ID Video."""
        try:
            # 1. Busca os dados do Job
            job_doc = await self.db["jobs"].find_one({"_id": ObjectId(job_id)})
            if not job_doc:
                logger.error(f"Job {job_id} não encontrado no banco.")
                return

            # 2. Atualiza Status
            await self.db["jobs"].update_one(
                {"_id": ObjectId(job_id)}, 
                {"$set": {"status": "processing", "updated_at": datetime.utcnow()}}
            )

            # 3. SCRAPER: Extração de dados
            scraper = ScraperRegistry.get_scraper_for_url(job_doc["product_url"])
            if not scraper:
                raise Exception(f"Nenhum scraper encontrado para: {job_doc['product_url']}")
            
            product_data = await scraper.scrape(job_doc["product_url"])

            # 4. LLM: Geração de Roteiro (Script)
            # Convertendo o objeto Product para dicionário para satisfazer o LLMService
            product_dict = {
                "name": product_data.name,
                "description": product_data.description,
                "price": product_data.price,
                "images": [img.url for img in product_data.images]
            }
            
            script_text = await self.llm.generate_ad_script(
                product_data=product_dict, 
                style=str(job_doc.get("style", "casual"))
            )

            # 5. Validação do Script (Evita o erro de "str | None" no Pylance)
            if not script_text:
                raise Exception("O LLM falhou ao gerar o roteiro do anúncio.")

            # 6. VIDEO: Envia para D-ID
            # Seleciona avatar: Imagem do produto ou fallback padrão
            avatar_url = "https://cdn.pixabay.com/photo/2016/08/08/09/17/avatar-1577909_1280.png"
            if product_data.images and len(product_data.images) > 0:
                avatar_url = product_data.images[0].url
            
            # Agora script_text é garantidamente str
            talk_res = await self.did_service.create_talk(avatar_url, script_text)
            talk_id = talk_res.get("id")

            # 7. POLLING: Espera o vídeo renderizar
            result_url = await self._wait_for_video(talk_id)

            # 8. FINALIZAÇÃO
            await self.db["jobs"].update_one({"_id": ObjectId(job_id)}, {
                "$set": {
                    "status": "completed", 
                    "result_url": result_url,
                    "product_name": product_data.name,
                    "updated_at": datetime.utcnow()
                }
            })
            logger.info(f"✓ Job {job_id} finalizado com sucesso!")

        except Exception as e:
            logger.error(f"❌ Erro ao processar Job {job_id}: {str(e)}")
            await self.db["jobs"].update_one(
                {"_id": ObjectId(job_id)}, 
                {"$set": {
                    "status": "failed", 
                    "error": str(e), 
                    "updated_at": datetime.utcnow()
                }}
            )

    async def _wait_for_video(self, talk_id: Optional[str]) -> str:
        """Faz polling na API do D-ID até o vídeo estar pronto."""
        if not talk_id:
            raise Exception("ID do vídeo não gerado pelo serviço D-ID.")

        for _ in range(30): 
            status_data = await self.did_service.get_talk(talk_id)
            status = status_data.get("status")

            if status == "done":
                return cast(str, status_data.get("result_url"))
            elif status == "error":
                raise Exception(f"Erro no D-ID: {status_data.get('error')}")
            
            logger.info(f"Vídeo {talk_id} em processamento ({status})...")
            await asyncio.sleep(5)
        
        raise Exception("Timeout: O vídeo demorou demais para ser gerado.")