from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
import hashlib

class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class Entity(BaseModel):
    text: str
    entity_type: str
    confidence: float = Field(ge=0, le=1)
    mentions_count: int = Field(default=1, ge=1)

class TopicSegment(BaseModel):
    topic: str
    sentiment: SentimentType
    timestamps: List[int] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    quote: Optional[str] = None

class YouTubeAnalysis(BaseModel):
    # ESSENCIAL: Resolve o erro de UserWarning do Pydantic no Render
    model_config = ConfigDict(
        protected_namespaces=(),
        json_encoders={datetime: lambda v: v.isoformat()}
    )

    video_id: str
    video_url: str
    video_title: Optional[str] = None
    channel_name: Optional[str] = None
    overall_sentiment: SentimentType
    sentiment_score: float = Field(ge=-1, le=1)
    confidence: float = Field(ge=0, le=1)
    entities: List[Entity] = Field(default_factory=list)
    brands_mentioned: List[str] = Field(default_factory=list)
    products_mentioned: List[str] = Field(default_factory=list)
    topics: List[TopicSegment] = Field(default_factory=list)
    transcript: str
    language: str = Field(default="pt")
    positive_aspects: List[str] = Field(default_factory=list)
    negative_aspects: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    model_version: str = Field(default="1.0")
    processing_time_seconds: float = Field(default=0, ge=0)
    raw_nlp_output: Optional[Dict[str, Any]] = None

    @property
    def cache_key(self) -> str:
        return f"yt_analysis:{self.video_id}"

class YouTubeAnalysisHistory(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str = Field(default_factory=lambda: hashlib.md5(str(datetime.utcnow()).encode()).hexdigest()[:16])
    analysis: YouTubeAnalysis
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)
    feedback: Optional[Dict[str, Any]] = None

class AnalysisRequest(BaseModel):
    youtube_url: str
    force_reanalysis: bool = False

class AnalysisResponse(BaseModel):
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