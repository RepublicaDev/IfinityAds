"""
Modelos de Análise YouTube com suporte a histórico e ML.
Design: Extensível para futuras análises de IA.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import hashlib


class SentimentType(str, Enum):
    """Tipos de sentimento detectados."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class Entity(BaseModel):
    """Entidade nomeada (marca, produto, pessoa, etc)."""
    text: str
    entity_type: str  # "PRODUCT", "BRAND", "PERSON", "LOCATION", etc
    confidence: float = Field(ge=0, le=1)
    mentions_count: int = Field(default=1, ge=1)


class TopicSegment(BaseModel):
    """Segmento de tópico identificado no vídeo."""
    topic: str  # "Qualidade", "Preço", "Entrega", "Produto", etc
    sentiment: SentimentType
    timestamps: List[int] = Field(default_factory=list, description="Segundos aproximados")
    confidence: float = Field(ge=0, le=1)
    quote: Optional[str] = None


class YouTubeAnalysis(BaseModel):
    """Análise completa de um vídeo YouTube."""
    # Identificação
    video_id: str
    video_url: str
    video_title: Optional[str] = None
    channel_name: Optional[str] = None
    
    # Análise de Sentimento
    overall_sentiment: SentimentType
    sentiment_score: float = Field(ge=-1, le=1, description="Score de -1 (negativo) a +1 (positivo)")
    confidence: float = Field(ge=0, le=1)
    
    # Extração de Entidades
    entities: List[Entity] = Field(default_factory=list)
    brands_mentioned: List[str] = Field(default_factory=list)
    products_mentioned: List[str] = Field(default_factory=list)
    
    # Análise de Tópicos
    topics: List[TopicSegment] = Field(default_factory=list)
    
    # Transcrição e Texto
    transcript: str = Field(..., description="Transcrição completa do vídeo")
    language: str = Field(default="pt", description="Código ISO 639-1")
    
    # Insights para Criação de Anúncio
    positive_aspects: List[str] = Field(default_factory=list, description="Pontos positivos mencionados")
    negative_aspects: List[str] = Field(default_factory=list, description="Pontos negativos/críticas")
    recommendations: List[str] = Field(default_factory=list, description="Recomendações derivadas")
    
    # Metadados
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    model_version: str = Field(default="1.0", description="Versão do modelo de análise")
    processing_time_seconds: float = Field(default=0, ge=0)
    
    # Dados brutos (para auditoria/retraining)
    raw_nlp_output: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
    
    @property
    def cache_key(self) -> str:
        """Chave para cache Redis."""
        return f"yt_analysis:{self.video_id}"
    
    @property
    def is_high_quality(self) -> bool:
        """Análise é confiável?"""
        return self.confidence >= 0.75 and len(self.transcript) > 100
    
    @property
    def engagement_score(self) -> float:
        """Score de engajamento baseado em análise (0-1)."""
        score = abs(self.sentiment_score)  # Sentimento extremo = engajamento
        score += min(len(self.topics) / 10, 0.3)  # Mais tópicos = mais engajamento
        score += min(len(self.entities) / 20, 0.2)  # Mais entidades = mais informação
        return min(score, 1.0)


class YouTubeAnalysisHistory(BaseModel):
    """Registro de histórico de análises para ML."""
    id: str = Field(default_factory=lambda: hashlib.md5(str(datetime.utcnow()).encode()).hexdigest()[:16])
    analysis: YouTubeAnalysis
    
    # Metadados de coleta
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Tags para categorização
    tags: List[str] = Field(default_factory=list)
    
    # Feedback (para melhorar modelo)
    feedback: Optional[Dict[str, Any]] = None
    
    # Métricas de qualidade
    was_useful: Optional[bool] = None
    manual_corrections: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AnalysisRequest(BaseModel):
    """Request para análise de vídeo YouTube."""
    youtube_url: str
    force_reanalysis: bool = Field(default=False, description="Ignora análises anteriores")


class AnalysisResponse(BaseModel):
    """Response com análise do vídeo."""
    video_id: str
    overall_sentiment: SentimentType
    sentiment_score: float
    confidence: float
    positive_aspects: List[str]
    negative_aspects: List[str]
    topics: List[Dict[str, Any]]
    brands_mentioned: List[str]
    products_mentioned: List[str]
    from_cache: bool = False
    processing_time_ms: int = 0
