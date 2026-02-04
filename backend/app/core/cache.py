"""
Camada de Cache Distribuído com Redis.
Implementação type-safe com TTL configurável.
"""
import json
import logging
from typing import Optional, Generic, TypeVar, Type
from datetime import timedelta
from redis.asyncio import Redis, from_url
from pydantic import BaseModel
import os

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class CacheConfig:
    """Configuração centralizada de cache."""
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    DEFAULT_TTL = 3600  # 1 hora
    PRODUCT_TTL = 7200  # 2 horas
    SCRAPER_TTL = 1800  # 30 min
    ANALYSIS_TTL = 3600  # 1 hora


class RedisCache:
    """
    Cliente Redis type-safe com suporte a Pydantic models.
    Design: Singleton pattern com lazy initialization.
    """
    _instance: Optional['RedisCache'] = None
    _client: Optional[Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Conecta ao Redis."""
        if self._client is None:
            try:
                self._client = await from_url(CacheConfig.REDIS_URL, decode_responses=True)
                await self._client.ping()
                logger.info("✓ Redis conectado")
            except Exception as e:
                logger.error(f"Falha ao conectar Redis: {e}")
                self._client = None
    
    async def disconnect(self):
        """Desconecta do Redis."""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def get(self, key: str, model: Type[T]) -> Optional[T]:
        """
        Recupera valor do cache e desserializa para Pydantic model.
        """
        if not self._client:
            return None
        try:
            data = await self._client.get(key)
            if data:
                return model.parse_raw(data)
        except Exception as e:
            logger.warning(f"Cache GET erro para {key}: {e}")
        return None
    
    async def set(self, key: str, value: BaseModel, ttl: int = CacheConfig.DEFAULT_TTL) -> bool:
        """
        Armazena Pydantic model no cache com TTL.
        """
        if not self._client:
            return False
        try:
            await self._client.setex(key, ttl, value.json())
            return True
        except Exception as e:
            logger.warning(f"Cache SET erro para {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Deleta chave do cache."""
        if not self._client:
            return False
        try:
            result = await self._client.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache DELETE erro para {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Deleta todas as chaves matching pattern (ex: 'product:shopee:*')."""
        if not self._client:
            return 0
        try:
            keys = await self._client.keys(pattern)
            if keys:
                return await self._client.delete(*keys)
        except Exception as e:
            logger.warning(f"Cache CLEAR erro para pattern {pattern}: {e}")
        return 0
    
    async def exists(self, key: str) -> bool:
        """Verifica se chave existe."""
        if not self._client:
            return False
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache EXISTS erro para {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Retorna TTL em segundos (-1 sem expiry, -2 não existe)."""
        if not self._client:
            return -2
        try:
            return await self._client.ttl(key)
        except Exception as e:
            logger.warning(f"Cache TTL erro para {key}: {e}")
            return -2
    
    async def mget(self, keys: list[str], model: Type[T]) -> list[Optional[T]]:
        """Recupera múltiplos valores do cache."""
        if not self._client:
            return [None] * len(keys)
        try:
            values = await self._client.mget(keys)
            return [model.parse_raw(v) if v else None for v in values]
        except Exception as e:
            logger.warning(f"Cache MGET erro: {e}")
            return [None] * len(keys)
    
    @property
    def is_connected(self) -> bool:
        """Verifica se Redis está conectado."""
        return self._client is not None


# Singleton global
cache = RedisCache()


class CacheKey:
    """Builder para construir chaves de cache de forma padronizada."""
    
    @staticmethod
    def product(marketplace: str, product_id: str) -> str:
        """Chave para dados de produto."""
        return f"product:{marketplace}:{product_id}"
    
    @staticmethod
    def products_list(marketplace: str, page: int = 1) -> str:
        """Chave para listagem de produtos."""
        return f"products_list:{marketplace}:page:{page}"
    
    @staticmethod
    def yt_analysis(video_id: str) -> str:
        """Chave para análise de vídeo YouTube."""
        return f"yt_analysis:{video_id}"
    
    @staticmethod
    def job_status(job_id: str) -> str:
        """Chave para status de job."""
        return f"job_status:{job_id}"
    
    @staticmethod
    def scraper_metadata(marketplace: str) -> str:
        """Chave para metadados do scraper."""
        return f"scraper_meta:{marketplace}"
