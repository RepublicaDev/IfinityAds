import uuid
import time
import asyncio
import logging
from app.services.scrapers import GenericEcomScraper
from app.services.youtube_analyzer import YouTubeAnalyzer
from app.services.script_engine import ScriptEngine
from app.services.heygen import HeyGenClient
from app.db import db

logger = logging.getLogger(__name__)

class AdOrchestrator:
    def __init__(self):
        # Instanciamos os clientes
        self.scraper = GenericEcomScraper()
        self.yta = YouTubeAnalyzer()
        self.engine = ScriptEngine()
        self.heygen = HeyGenClient()

    async def enqueue_job(self, product_url: str, youtube_url: str | None, style: str, user_id: str):
        """Cria o registro do job no MongoDB antes de enviar para o Celery."""
        job_id = str(uuid.uuid4())
        doc = {
            "job_id": job_id,
            "user_id": user_id,
            "status": "queued",
            "meta": {
                "product_url": product_url, 
                "youtube_url": youtube_url, 
                "style": style
            },
            "created_at": time.time(),
            "progress": [],
            "result": None,
            "error": None,
            "started_at": None,
            "finished_at": None,
        }
        if db is not None:
            await db.render_logs.insert_one(doc)
        return job_id

    async def _update_progress(self, job_id: str, step: str):
        """Helper para atualizar o progresso no banco."""
        if db is not None:
            await db.render_logs.update_one(
                {"job_id": job_id}, 
                {"$push": {"progress": {"ts": time.time(), "step": step}}}
            )

    async def process_job(self, job_id: str):
        """Fluxo principal de execução do anúncio."""
        if db is None:
            logger.error("Database connection not available")
            return

        job = await db.render_logs.find_one({"job_id": job_id})
        if not job:
            logger.error(f"Job {job_id} não encontrado no banco.")
            return

        await db.render_logs.update_one(
            {"job_id": job_id}, 
            {"$set": {"status": "processing", "started_at": time.time()}}
        )

        meta = job.get("meta", {})
        
        try:
            # Etapa 1: Scraping do Produto
            product_url = meta.get("product_url")
            product = None
            if product_url:
                await self._update_progress(job_id, "scraping")
                product = await self.scraper.scrape_with_retry(product_url)

            # Etapa 2: Análise do YouTube
            youtube_url = meta.get("youtube_url")
            analysis = None
            if youtube_url:
                await self._update_progress(job_id, "youtube_analysis")
                analysis = await self.yta.analyze(youtube_url)

            # Etapa 3: Geração de Script (Garante que rode em thread se for síncrono)
            await self._update_progress(job_id, "script_generation")
            style = meta.get("style", "charismatic_fomo")
            
            # Se o engine for síncrono, usamos run_in_executor para não travar o loop
            if asyncio.iscoroutinefunction(self.engine.generate_script):
                script = await self.engine.generate_script(product, analysis, style)
            else:
                loop = asyncio.get_event_loop()
                script = await loop.run_in_executor(
                    None, self.engine.generate_script, product, analysis, style
                )

            # Etapa 4: HeyGen Video Generation
            await self._update_progress(job_id, "video_generation")
            try:
                video_result = await self.heygen.generate_from_script(script)
            except Exception as e:
                logger.warning(f"Falha no HeyGen, usando stub: {e}")
                video_result = {"url": None, "note": "generation-stub", "script_used": script}

            # Finalização
            await db.render_logs.update_one(
                {"job_id": job_id}, 
                {
                    "$set": {
                        "status": "done", 
                        "result": video_result, 
                        "finished_at": time.time()
                    }
                }
            )

        except Exception as e:
            logger.exception(f"Erro crítico no processamento do job {job_id}")
            await db.render_logs.update_one(
                {"job_id": job_id}, 
                {
                    "$set": {
                        "status": "failed", 
                        "error": str(e), 
                        "finished_at": time.time()
                    }
                }
            )
            raise