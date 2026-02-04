"""
YouTube Analyzer com NLP avançado - Sentimentos, Entidades, Tópicos.
Integração com cache e histórico para ML.
"""
import asyncio
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from youtube_transcript_api import YouTubeTranscriptApi
from app.models.youtube import (
    YouTubeAnalysis, Entity, TopicSegment, SentimentType,
    YouTubeAnalysisHistory, AnalysisResponse
)
from app.core.cache import cache, CacheKey, CacheConfig

logger = logging.getLogger(__name__)


class SimpleNLPEngine:
    """
    Motor NLP leve usando regex e padrões (sem dependências pesadas).
    Pode ser substituído por spaCy/BERT em produção.
    """
    
    # Dicionários de palavras-chave para análise
    POSITIVE_WORDS = {
        'pt': ['ótimo', 'bom', 'excelente', 'adorei', 'perfeito', 'recomendo',
               'amei', 'sensacional', 'maravilhoso', 'qualidade', 'legal', 'show',
               'incrível', 'fantástico', 'lindo', 'surpreendente', 'vale muito a pena'],
        'en': ['great', 'excellent', 'amazing', 'perfect', 'love', 'recommend',
               'awesome', 'wonderful', 'best', 'fantastic', 'incredible']
    }
    
    NEGATIVE_WORDS = {
        'pt': ['ruim', 'péssimo', 'horrível', 'fraco', 'problema', 'defeito',
               'decepcionante', 'não gostei', 'falha', 'não recomendo', 'caro',
               'decepção', 'pior', 'prejudicial', 'odeio', 'terrível'],
        'en': ['bad', 'terrible', 'horrible', 'awful', 'problem', 'defect',
               'disappointing', 'not recommended', 'fail', 'worse', 'hate']
    }
    
    # Tópicos e palavras-chave
    TOPICS = {
        'Qualidade': ['qualidade', 'durável', 'resistente', 'acabamento', 'confecção'],
        'Preço': ['preço', 'caro', 'barato', 'valor', 'custa', 'investimento'],
        'Entrega': ['entrega', 'rápido', 'demora', 'embalagem', 'chegou'],
        'Produto': ['produto', 'item', 'coisa', 'artigo', 'objeto'],
        'Atendimento': ['atendimento', 'vendedor', 'suporte', 'resposta', 'contato'],
        'Aparência': ['aparência', 'cores', 'design', 'visual', 'esteticamente'],
        'Funcionalidade': ['funciona', 'funcional', 'prático', 'útil', 'serve'],
    }
    
    @staticmethod
    def calculate_sentiment_score(text: str, language: str = 'pt') -> tuple[float, float]:
        """
        Calcula score de sentimento: -1 (negativo) a +1 (positivo).
        Retorna: (score, confidence)
        """
        text_lower = text.lower()
        
        positive_count = sum(1 for word in SimpleNLPEngine.POSITIVE_WORDS.get(language, [])
                            if word in text_lower)
        negative_count = sum(1 for word in SimpleNLPEngine.NEGATIVE_WORDS.get(language, [])
                            if word in text_lower)
        
        if positive_count == 0 and negative_count == 0:
            return 0.0, 0.3  # Neutral, low confidence
        
        total = positive_count + negative_count
        score = (positive_count - negative_count) / total
        confidence = min(total / 20, 1.0)  # Mais palavras = mais confiança
        
        return score, confidence
    
    @staticmethod
    def extract_entities(text: str) -> List[Entity]:
        """Extrai entidades nomeadas com padrões simples."""
        entities = []
        
        # Padrões regex para detectar tipos
        brand_pattern = r'\b(?:Apple|Samsung|LG|Sony|Nike|Adidas|Coca|Pepsi|Amazon|Shopee|Shein|AliExpress)\b'
        brands = re.findall(brand_pattern, text, re.I)
        
        for brand in set(brands):
            entities.append(Entity(
                text=brand,
                entity_type="BRAND",
                confidence=0.95,
                mentions_count=brands.count(brand)
            ))
        
        # Padrões para produtos
        product_pattern = r'(?:produto|item|coisa|artigo):\s*([^.,\n]+)'
        products = re.findall(product_pattern, text, re.I)
        
        for product in set(products):
            entities.append(Entity(
                text=product.strip(),
                entity_type="PRODUCT",
                confidence=0.80,
                mentions_count=products.count(product)
            ))
        
        return entities
    
    @staticmethod
    def extract_topics(text: str) -> List[TopicSegment]:
        """Extrai tópicos principais e sentimento por tópico."""
        topics = []
        text_lower = text.lower()
        
        for topic_name, keywords in SimpleNLPEngine.TOPICS.items():
            # Verifica se tópico existe no texto
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches == 0:
                continue
            
            # Calcula sentimento para esse tópico
            # Busca sentença contendo palavras do tópico
            sentences = re.split(r'[.!?]+', text)
            topic_sentences = [s for s in sentences if any(kw in s.lower() for kw in keywords)]
            
            if topic_sentences:
                topic_text = ' '.join(topic_sentences)
                score, conf = SimpleNLPEngine.calculate_sentiment_score(topic_text)
                
                sentiment = SentimentType.POSITIVE if score > 0.2 else (
                    SentimentType.NEGATIVE if score < -0.2 else SentimentType.NEUTRAL
                )
                
                # Extrai quote
                quote = topic_sentences[0].strip()[:100] if topic_sentences else None
                
                topics.append(TopicSegment(
                    topic=topic_name,
                    sentiment=sentiment,
                    confidence=conf,
                    quote=quote
                ))
        
        return topics


class YouTubeAnalyzer:
    """
    Analisador completo de vídeos YouTube com NLP, cache e histórico.
    """
    
    def __init__(self):
        self.nlp = SimpleNLPEngine()
    
    async def fetch_transcript(self, video_id: str) -> str:
        """Busca transcrição do YouTube com async."""
        def _get_transcript():
            try:
                captions = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en'])
                return ' '.join([item['text'] for item in captions])
            except Exception as e:
                logger.warning(f"Transcrição não disponível para {video_id}: {e}")
                return ""
        
        return await asyncio.to_thread(_get_transcript)
    
    def extract_video_id(self, url: str) -> str:
        """Extrai ID do vídeo da URL YouTube."""
        # Padrões: youtube.com/watch?v=ID, youtu.be/ID
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Não foi possível extrair ID de: {url}")
    
    async def analyze(self, youtube_url: str, force_reanalysis: bool = False) -> YouTubeAnalysis:
        """
        Analisa vídeo YouTube completo.
        
        Args:
            youtube_url: URL do vídeo
            force_reanalysis: Se True, ignora cache
            
        Returns:
            YouTubeAnalysis com análise completa
        """
        start_time = datetime.utcnow()
        
        # Extrai ID
        video_id = self.extract_video_id(youtube_url)
        cache_key = CacheKey.yt_analysis(video_id)
        
        # Tenta cache
        if not force_reanalysis:
            cached = await cache.get(cache_key, YouTubeAnalysis)
            if cached:
                logger.info(f"✓ Cache HIT: {cache_key}")
                return cached
        
        logger.info(f"Analisando YouTube: {video_id}")
        
        # Busca transcrição
        transcript = await self.fetch_transcript(video_id)
        if not transcript:
            raise ValueError(f"Não foi possível obter transcrição para {video_id}")
        
        # Análise de Sentimento
        sentiment_score, confidence = self.nlp.calculate_sentiment_score(transcript)
        
        # Determina sentimento geral
        if sentiment_score > 0.2:
            overall_sentiment = SentimentType.POSITIVE
        elif sentiment_score < -0.2:
            overall_sentiment = SentimentType.NEGATIVE
        else:
            overall_sentiment = SentimentType.NEUTRAL
        
        # Extrai entidades
        entities = self.nlp.extract_entities(transcript)
        brands = [e.text for e in entities if e.entity_type == "BRAND"]
        products = [e.text for e in entities if e.entity_type == "PRODUCT"]
        
        # Extrai tópicos
        topics = self.nlp.extract_topics(transcript)
        
        # Extrai aspectos positivos e negativos
        positive_pattern = r'(?:adorei|gostei|excelente|ótimo):\s*([^.!?]+)'
        positive_aspects = [m.strip() for m in re.findall(positive_pattern, transcript, re.I)]
        
        negative_pattern = r'(?:problema|falha|ruim|decepcionante):\s*([^.!?]+)'
        negative_aspects = [m.strip() for m in re.findall(negative_pattern, transcript, re.I)]
        
        # Se não encontrou padrões específicos, extrai das sentenças
        if not positive_aspects:
            positive_aspects = self._extract_sentiment_sentences(transcript, 'positive')
        if not negative_aspects:
            negative_aspects = self._extract_sentiment_sentences(transcript, 'negative')
        
        # Cria análise
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        analysis = YouTubeAnalysis(
            video_id=video_id,
            video_url=youtube_url,
            overall_sentiment=overall_sentiment,
            sentiment_score=sentiment_score,
            confidence=confidence,
            entities=entities,
            brands_mentioned=brands,
            products_mentioned=products,
            topics=topics,
            transcript=transcript,
            positive_aspects=positive_aspects[:5],
            negative_aspects=negative_aspects[:5],
            recommendations=self._generate_recommendations(overall_sentiment, topics),
            processing_time_seconds=processing_time,
            model_version="1.0"
        )
        
        # Armazena no cache
        try:
            await cache.set(cache_key, analysis, ttl=CacheConfig.ANALYSIS_TTL)
            logger.info(f"✓ Cache SET: {cache_key}")
        except Exception as e:
            logger.warning(f"Falha ao cachear análise: {e}")
        
        logger.info(f"✓ Análise YouTube concluída: {video_id} ({processing_time:.2f}s)")
        return analysis
    
    def _extract_sentiment_sentences(self, text: str, sentiment_type: str) -> List[str]:
        """Extrai sentenças com sentimento específico."""
        sentences = re.split(r'[.!?]+', text)
        
        if sentiment_type == 'positive':
            keywords = self.nlp.POSITIVE_WORDS.get('pt', [])
        else:
            keywords = self.nlp.NEGATIVE_WORDS.get('pt', [])
        
        relevant = [s.strip() for s in sentences
                   if any(kw in s.lower() for kw in keywords)]
        
        return relevant[:5]
    
    def _generate_recommendations(self, sentiment: SentimentType, topics: List[TopicSegment]) -> List[str]:
        """Gera recomendações de anúncio baseado em análise."""
        recommendations = []
        
        if sentiment == SentimentType.POSITIVE:
            recommendations.append("✓ Foco em recomendações entusiastas")
            recommendations.append("✓ Destaque satisfação do cliente")
        else:
            recommendations.append("⚠ Abordar objeções principais")
            recommendations.append("⚠ Enfatizar melhorias/soluções")
        
        # Recomendações por tópico
        for topic in topics[:3]:
            if topic.sentiment == SentimentType.POSITIVE:
                recommendations.append(f"✓ Destacar {topic.topic.lower()}: {topic.quote[:50] if topic.quote else ''}")
            else:
                recommendations.append(f"⚠ Melhorar {topic.topic.lower()}")
        
        return recommendations[:5]
    
    async def save_to_history(self, analysis: YouTubeAnalysis, tags: List[str] = None) -> YouTubeAnalysisHistory:
        """Salva análise no histórico para ML."""
        from app.db import db
        
        history = YouTubeAnalysisHistory(
            analysis=analysis,
            tags=tags or []
        )
        
        if db:
            try:
                await db.youtube_analyses.insert_one(history.dict())
                logger.info(f"✓ Análise salva no histórico: {analysis.video_id}")
            except Exception as e:
                logger.warning(f"Falha ao salvar histórico: {e}")
        
        return history
    
    def to_response(self, analysis: YouTubeAnalysis, from_cache: bool = False) -> AnalysisResponse:
        """Converte YouTubeAnalysis para AnalysisResponse."""
        return AnalysisResponse(
            video_id=analysis.video_id,
            overall_sentiment=analysis.overall_sentiment,
            sentiment_score=analysis.sentiment_score,
            confidence=analysis.confidence,
            positive_aspects=analysis.positive_aspects,
            negative_aspects=analysis.negative_aspects,
            topics=[{
                'name': t.topic,
                'sentiment': t.sentiment,
                'confidence': t.confidence,
                'quote': t.quote
            } for t in analysis.topics],
            brands_mentioned=analysis.brands_mentioned,
            products_mentioned=analysis.products_mentioned,
            from_cache=from_cache,
            processing_time_ms=int(analysis.processing_time_seconds * 1000)
        )
