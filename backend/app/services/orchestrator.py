import uuid
import time
import asyncio
from app.services.scrapers import GenericEcomScraper
from app.services.youtube_analyzer import YouTubeAnalyzer
from app.services.script_engine import ScriptEngine
from app.services.heygen import HeyGenClient
from app.db import db

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
            "started_at": None,
            "finished_at": None,
        }
        if db:
            await db.render_logs.insert_one(doc)
        return job_id

    async def process_job(self, job_id: str):
        # Marca processamento e registra timestamps; busca meta do job
        job = None
        if db:
            job = await db.render_logs.find_one({"job_id": job_id})
            await db.render_logs.update_one({"job_id": job_id}, {"$set": {"status": "processing", "started_at": time.time()}})

        if not job:
            # se não encontrou, registra um documento mínimo
            job = {
                "job_id": job_id,
                "meta": {},
            }

        meta = job.get("meta") or {}

        try:
            # Exemplo de fluxo: scrape produto -> analisar youtube (opcional) -> gerar script -> gerar vídeo
            product_url = meta.get("product_url")
            youtube_url = meta.get("youtube_url")
            style = meta.get("style") or "charismatic_fomo"

            # Etapa 1: scrape
            if product_url:
                await db.render_logs.update_one({"job_id": job_id}, {"$push": {"progress": {"ts": time.time(), "step": "scraping"}}})
                product = await self.scraper.scrape_with_retry(product_url)
            else:
                product = None

            # Etapa 2: youtube analysis (opcional)
            analysis = None
            if youtube_url:
                await db.render_logs.update_one({"job_id": job_id}, {"$push": {"progress": {"ts": time.time(), "step": "youtube_analysis"}}})
                analysis = await self.yta.analyze(youtube_url)

            # Etapa 3: script generation (engine pode ser sync/async)
            await db.render_logs.update_one({"job_id": job_id}, {"$push": {"progress": {"ts": time.time(), "step": "script_generation"}}})
            try:
                script = await self.engine.generate_script(product, analysis, style)
            except TypeError:
                # caso generate_script seja síncrono
                script = self.engine.generate_script(product, analysis, style)

            # Etapa 4: call HeyGen (simulado se falhar)
            await db.render_logs.update_one({"job_id": job_id}, {"$push": {"progress": {"ts": time.time(), "step": "video_generation"}}})
            try:
                video_result = await self.heygen.generate_from_script(script)
            except Exception:
                # fallback: apenas registra um stub
                video_result = {"url": None, "note": "generation-stub"}

            # Finaliza com sucesso
            if db:
                await db.render_logs.update_one({"job_id": job_id}, {"$set": {"status": "done", "result": video_result, "finished_at": time.time()}})

        except Exception as e:
            if db:
                await db.render_logs.update_one({"job_id": job_id}, {"$set": {"status": "failed", "error": str(e), "finished_at": time.time()}})
            raise
