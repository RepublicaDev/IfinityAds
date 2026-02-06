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
        try:
            # 1. Recuperação e Setup inicial
            job_doc = await self.db["jobs"].find_one({"_id": ObjectId(job_id)})
            if not job_doc: return

            await self.db["jobs"].update_one(
                {"_id": ObjectId(job_id)}, 
                {"$set": {"status": "processing", "updated_at": datetime.utcnow()}}
            )

            # 2. SCRAPER: Extração de dados
            scraper = ScraperRegistry.get_scraper_for_url(job_doc["product_url"])
            if not scraper:
                raise Exception(f"Scraper não encontrado para: {job_doc['product_url']}")
            
            product_data = await scraper.scrape(job_doc["product_url"])

            # 3. AJUSTE DE PREÇO (DataPrice Correction)
            # Se o preço vier como 0.01 (comum em bots do AliExpress), tentamos validar
            final_price = product_data.price.amount
            if final_price <= 0.1 and product_data.price.original_amount:
                final_price = product_data.price.original_amount
                logger.warning(f"Preço suspeito (bot check). Usando preço original: {final_price}")

            price_str = f"{product_data.price.currency} {final_price:.2f}".replace('.', ',')

            # 4. LLM: Preparação do Dicionário e Geração
            product_dict = {
                "name": product_data.name,
                "description": product_data.description,
                "price": price_str, # Enviamos a string formatada para a IA não errar
                "images": [img.url for img in product_data.images]
            }
            
            script_text = await self.llm.generate_ad_script(
                product_data=product_dict, 
                style=str(job_doc.get("style", "casual"))
            )

            if not script_text:
                raise Exception("Falha na geração do roteiro pelo LLM.")

            # 5. VIDEO: D-ID Integration
            # Fallback de imagem caso o scraper falhe em pegar fotos
            avatar_url = "https://cdn.pixabay.com/photo/2016/08/08/09/17/avatar-1577909_1280.png"
            if product_data.images and len(product_data.images) > 0:
                avatar_url = product_data.images[0].url
            
            talk_res = await self.did_service.create_talk(avatar_url, script_text)
            talk_id = talk_res.get("id")

            # 6. POLLING: Aguardar renderização
            result_url = await self._wait_for_video(talk_id)

            # 7. FINALIZAÇÃO: Update no Banco
            await self.db["jobs"].update_one({"_id": ObjectId(job_id)}, {
                "$set": {
                    "status": "completed", 
                    "result_url": result_url,
                    "product_name": product_data.name,
                    "final_price": final_price,
                    "updated_at": datetime.utcnow()
                }
            })
            logger.info(f"✓ Job {job_id} concluído com sucesso!")

        except Exception as e:
            logger.error(f"❌ Erro crítico no Job {job_id}: {str(e)}")
            await self.db["jobs"].update_one(
                {"_id": ObjectId(job_id)}, 
                {"$set": {"status": "failed", "error": str(e), "updated_at": datetime.utcnow()}}
            )

    async def _wait_for_video(self, talk_id: Optional[str]) -> str:
        if not talk_id:
            raise Exception("ID do vídeo (talk_id) é nulo.")

        # Polling: 40 tentativas a cada 5 segundos = ~3 minutos de espera
        for i in range(40): 
            status_data = await self.did_service.get_talk(talk_id)
            status = status_data.get("status")

            if status == "done":
                return cast(str, status_data.get("result_url"))
            elif status == "error":
                raise Exception(f"Erro no processamento do D-ID: {status_data.get('error')}")
            
            logger.info(f"Aguardando vídeo {talk_id}... Tentativa {i+1}")
            await asyncio.sleep(5)
        
        raise Exception("Timeout: O D-ID demorou mais de 3 minutos para renderizar.")