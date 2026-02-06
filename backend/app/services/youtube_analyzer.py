import asyncio
import re
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import sugerido pelo Pylance para evitar erro de resolução de tipos
from youtube_transcript_api._api import YouTubeTranscriptApi 

from app.models.youtube import (
    YouTubeAnalysis, Entity, TopicSegment, SentimentType,
    YouTubeAnalysisHistory, AnalysisResponse
)
from app.core.cache import cache

logger = logging.getLogger(__name__)

class YouTubeAnalyzer:
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extrai o ID do vídeo de várias formas de URL do YouTube"""
        pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(pattern, url)
        return match.group(1) if match else None

    async def analyze(self, url: str, force_reanalysis: bool = False) -> YouTubeAnalysis:
        """
        Analisa o vídeo. 
        Note: Adicionei force_reanalysis aqui para bater com o que o Front pode enviar futuramente.
        """
        start_time = time.time()
        video_id = self._extract_video_id(url)
        
        if not video_id:
            raise ValueError("URL do YouTube inválida.")

        # 1. Tentar buscar a transcrição real (Mecânica base)
        transcript_text = "Transcrição não disponível"
        try:
            # Roda em thread pool para não bloquear o loop assíncrono do FastAPI
            loop = asyncio.get_event_loop()
            transcript_list = await loop.run_in_executor(
                None, lambda: YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en'])
            )
            transcript_text = " ".join([t['text'] for t in transcript_list])
        except Exception as e:
            logger.warning(f"Não foi possível obter transcrição para {video_id}: {e}")

        # 2. Criar o objeto de análise (Aqui entrará sua chamada ao LLM/GPT futuramente)
        analysis = YouTubeAnalysis(
            video_id=video_id,
            video_url=url,
            overall_sentiment=SentimentType.NEUTRAL,
            sentiment_score=0.5,
            confidence=0.9,
            transcript=transcript_text[:1000], # Limitando para não explodir o DB
            language="pt",
            positive_aspects=[],
            negative_aspects=[],
            topics=[],
            brands_mentioned=[],
            products_mentioned=[],
            processing_time_seconds=time.time() - start_time
        )

        return analysis

    def to_response(self, analysis: YouTubeAnalysis, from_cache: bool = False) -> AnalysisResponse:
        """Converte o modelo de banco para o modelo de resposta da API"""
        
        # Garantimos que topics seja uma lista de dicionários conforme o AnalysisResponse espera
        topics_dict = [
            {
                "topic": t.topic,
                "sentiment": t.sentiment,
                "confidence": t.confidence,
                "quote": t.quote
            } for t in (analysis.topics or [])
        ]
        
        return AnalysisResponse(
            video_id=analysis.video_id,
            overall_sentiment=analysis.overall_sentiment,
            sentiment_score=analysis.sentiment_score,
            confidence=analysis.confidence,
            positive_aspects=analysis.positive_aspects or [],
            negative_aspects=analysis.negative_aspects or [],
            topics=topics_dict,
            brands_mentioned=analysis.brands_mentioned or [],
            products_mentioned=analysis.products_mentioned or [],
            from_cache=from_cache,
            processing_time_ms=int((analysis.processing_time_seconds or 0) * 1000)
        )