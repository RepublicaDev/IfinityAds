import logging
import asyncio
from datetime import datetime
from typing import Optional, Any, cast
from bson import ObjectId

from app.db.db import db_wrapper
from app.services.llm_service import LLMService
from app.services.video_did import DIDService
from app.services.scrapers.base import ScraperRegistry

logger = logging.getLogger(__name__)

class AdOrchestrator:
    def __init__(self):
        self.llm = LLMService()
        self.did_service = DIDService()

    @property
    def db(self) -> Any:
        if db_wrapper.database is None:
            raise RuntimeError("Conexão com MongoDB não estabelecida.")
        return db_wrapper.database

    async def enqueue_job(self, product_url: str, user_id: str, style: str, youtube_url: Optional[str] = None) -> str:
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
            job = await self.db["jobs"].find_one({"_id": ObjectId(job_id)})
            if not job: return

            await self.db["jobs"].update_one({"_id": ObjectId(job_id)}, {"$set": {"status": "processing"}})

            # 1. Scraping
            scraper = ScraperRegistry.get_scraper_for_url(job["product_url"])
            if not scraper:
                raise Exception(f"URL não suportada: {job['product_url']}")
            
            product = await scraper.scrape_with_retry(job["product_url"])

            # 2. LLM Script
            context = {
                "name": product.name,
                "price": f"{product.price.currency} {product.price.amount}",
                "description": product.description
            }
            raw_script = await self.llm.generate_ad_script(context, job["style"])
            
            # SOLUÇÃO PYLANCE: Garantir que script não seja None antes de enviar ao D-ID
            if not raw_script:
                raise Exception("O LLM falhou em gerar o roteiro.")
            
            script = str(raw_script) # Garantindo que é string

            # 3. Vídeo
            avatar_url = "https://cdn.pixabay.com/photo/2016/08/08/09/17/avatar-1577909_1280.png"
            if product.images and len(product.images) > 0:
                avatar_url = product.images[0].url

            talk = await self.did_service.create_talk(avatar_url, script)
            video_url = await self._wait_for_video(talk.get("id"))

            await self.db["jobs"].update_one(
                {"_id": ObjectId(job_id)}, 
                {"$set": {"status": "completed", "result_url": video_url, "updated_at": datetime.utcnow()}}
            )

        except Exception as e:
            logger.error(f"Erro no Job {job_id}: {str(e)}")
            await self.db["jobs"].update_one(
                {"_id": ObjectId(job_id)}, 
                {"$set": {"status": "failed", "error": str(e), "updated_at": datetime.utcnow()}}
            )

    async def _wait_for_video(self, talk_id: Optional[str]) -> str:
        if not talk_id: raise Exception("ID do D-ID ausente.")
        for _ in range(60):
            res = await self.did_service.get_talk(talk_id)
            if res.get("status") == "done":
                return cast(str, res.get("result_url"))
            if res.get("status") == "error":
                raise Exception("Erro no processamento do vídeo.")
            await asyncio.sleep(5)
        raise Exception("Timeout")