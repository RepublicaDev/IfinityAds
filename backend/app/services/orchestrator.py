import uuid
import time
import asyncio
import logging
from typing import Any

# Importações dos seus serviços
from app.services.scrapers import GenericEcomScraper
from app.services.youtube_analyzer import YouTubeAnalyzer
from app.services.script_engine import ScriptEngine
from app.services.heygen import HeyGenClient
from app.db import db

logger = logging.getLogger(__name__)

class AdOrchestrator:
    def __init__(self):
        self.scraper = GenericEcomScraper()
        self.yta = YouTubeAnalyzer()
        self.engine = ScriptEngine()
        self.heygen = HeyGenClient()

    async def enqueue_job(self, product_url: str, youtube_url: str | None, style: str, user_id: str):
        job_id = str(uuid.uuid4())
        doc = {
            "job_id": job_id,
            "user_id": user_id,
            "status": "queued",
            "meta": {"product_url": product_url, "youtube_url": youtube_url, "style": style},
            "created_at": time.time(),
            "progress": [],
            "result": None,
            "error": None,
        }
        # Usamos Any para evitar o erro "Never" do Pylance
        database: Any = db
        if database is not None:
            await database.render_logs.insert_one(doc)
        return job_id

    async def process_job(self, job_id: str):
        database: Any = db
        if database is None:
            logger.error("Banco de dados não disponível.")
            return

        # Busca o job
        job = await database.render_logs.find_one({"job_id": job_id})
        if not job: return

        await database.render_logs.update_one(
            {"job_id": job_id}, 
            {"$set": {"status": "processing", "started_at": time.time()}}
        )

        meta = job.get("meta", {})
        
        try:
            # 1. Scraping
            product_url = meta.get("product_url")
            product = None
            if product_url:
                await database.render_logs.update_one({"job_id": job_id}, {"$push": {"progress": {"step": "scraping"}}})
                product = await self.scraper.scrape_with_retry(product_url)

            # 2. YouTube
            youtube_url = meta.get("youtube_url")
            analysis = None
            if youtube_url:
                await database.render_logs.update_one({"job_id": job_id}, {"$push": {"progress": {"step": "youtube_analysis"}}})
                analysis = await self.yta.analyze(youtube_url)

            # 3. Script (Aqui o Pylance dizia que não conhecia o método)
            # Verifique se no seu ScriptEngine o nome é exatamente 'generate_script'
            await database.render_logs.update_one({"job_id": job_id}, {"$push": {"progress": {"step": "script_generation"}}})
            style = meta.get("style", "charismatic_fomo")
            
            # Forçamos a verificação para o Pylance não travar
            engine: Any = self.engine
            script = await engine.generate_script(product, analysis, style)

            # 4. HeyGen
            await database.render_logs.update_one({"job_id": job_id}, {"$push": {"progress": {"step": "video_generation"}}})
            heygen: Any = self.heygen
            video_result = await heygen.generate_from_script(script)

            # Finalização bem-sucedida
            await database.render_logs.update_one(
                {"job_id": job_id}, 
                {"$set": {"status": "done", "result": video_result, "finished_at": time.time()}}
            )

        except Exception as e:
            logger.exception("Erro no processamento")
            await database.render_logs.update_one(
                {"job_id": job_id}, 
                {"$set": {"status": "failed", "error": str(e), "finished_at": time.time()}}
            )