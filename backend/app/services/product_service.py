from __future__ import annotations
from typing import Optional, List, Any
import logging
import asyncio

from app.models.product import Product, ProductResponse, Marketplace
from app.core.cache import cache, CacheConfig
from app.services.scrapers.base import ScraperRegistry, ScraperError

logger = logging.getLogger(__name__)

class ProductScraperService:
    @staticmethod
    async def scrape_product(url: str, bypass_cache: bool = False) -> Product:
        scraper = ScraperRegistry.get_scraper_for_url(url)
        if not scraper:
            # Acessando o dicionário interno para listar o que temos
            available = ", ".join([str(m.value) for m in ScraperRegistry._instances.keys()])
            raise ScraperError(f"URL não suportada. Marketplaces: {available}")
        
        product_id = scraper.extract_product_id(url)
        cache_key = f"product:{scraper.marketplace.value}:{product_id}"
        
        if not bypass_cache:
            try:
                cached = await cache.get(cache_key, Product)
                if cached:
                    return cached
            except Exception as e:
                logger.warning(f"Erro ao ler cache: {e}")
        
        product = await scraper.scrape_with_retry(url)
        
        try:
            await cache.set(cache_key, product, ttl=CacheConfig.PRODUCT_TTL)
        except Exception as e:
            logger.warning(f"Erro ao salvar cache: {e}")
            
        return product

    @staticmethod
    def to_response(product: Product) -> ProductResponse:
        """Converte com segurança garantindo tipos primitivos para o Pydantic"""
        # Extração segura de metadados
        m_id = "unknown"
        m_type = Marketplace.GENERIC
        s_url = ""
        
        if hasattr(product, 'metadata') and product.metadata:
            m_id = str(product.metadata.marketplace_id)
            m_type = product.metadata.marketplace
            s_url = str(product.metadata.source_url)

        return ProductResponse(
            id=m_id,
            name=str(product.name or "Produto sem nome"),
            price=product.price,  # O modelo ProductPrice já deve estar correto
            images=product.images or [],
            rating=float(product.rating or 0.0),
            review_count=int(product.review_count or 0),
            marketplace=m_type,
            source_url=s_url,
            seller_name=str(product.seller_name or "Vendedor Oculto")
        )