import asyncio
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
# Pylance fix: Importar de ._api conforme sugerido pelo erro
from youtube_transcript_api._api import YouTubeTranscriptApi 

from app.models.youtube import (
    YouTubeAnalysis, Entity, TopicSegment, SentimentType,
    YouTubeAnalysisHistory, AnalysisResponse
)
from app.core.cache import cache

logger = logging.getLogger(__name__)

class YouTubeAnalyzer:
    async def analyze(self, url: str) -> YouTubeAnalysis:
        """Adicionado o método que faltava para o orchestrator"""
        # Lógica simplificada para exemplo, implemente sua extração aqui
        video_id = url.split("v=")[-1]
        return YouTubeAnalysis(
            video_id=video_id,
            video_url=url,
            overall_sentiment=SentimentType.NEUTRAL,
            sentiment_score=0.0,
            confidence=1.0,
            transcript="Transcrição placeholder",
            language="pt"
        )

    async def save_to_history(self, analysis: YouTubeAnalysis, tags: Optional[List[str]] = None) -> YouTubeAnalysisHistory:
        from app.db import db
        
        # Pylance fix: Garantir que passamos uma lista, nunca None
        safe_tags = tags if tags is not None else []
        
        history = YouTubeAnalysisHistory(
            analysis=analysis,
            tags=safe_tags
        )
        
        if db is not None:
            try:
                await db.youtube_analyses.insert_one(history.model_dump())
            except Exception as e:
                logger.error(f"Erro ao salvar DB: {e}")
        
        return history

    def to_response(self, analysis: YouTubeAnalysis, from_cache: bool = False) -> AnalysisResponse:
        topics_dict = [
            {
                "topic": t.topic,
                "sentiment": t.sentiment,
                "confidence": t.confidence,
                "quote": t.quote
            } for t in analysis.topics
        ]
        
        return AnalysisResponse(
            video_id=analysis.video_id,
            overall_sentiment=analysis.overall_sentiment,
            sentiment_score=analysis.sentiment_score,
            confidence=analysis.confidence,
            positive_aspects=analysis.positive_aspects,
            negative_aspects=analysis.negative_aspects,
            topics=topics_dict,
            brands_mentioned=analysis.brands_mentioned,
            products_mentioned=analysis.products_mentioned,
            from_cache=from_cache,
            processing_time_ms=int(analysis.processing_time_seconds * 1000)
        )