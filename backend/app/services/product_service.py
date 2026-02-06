from typing import Optional, List
import logging
import asyncio
from app.models.product import Product, ProductResponse, Marketplace
from app.core.cache import cache, CacheKey, CacheConfig
from app.services.scrapers.base import ScraperRegistry, ScraperError

logger = logging.getLogger(__name__)

class ProductScraperService:
    @staticmethod
    async def scrape_product(url: str, bypass_cache: bool = False) -> Product:
        scraper = ScraperRegistry.get_scraper_for_url(url)
        if not scraper:
            available = ", ".join(m.value for m in ScraperRegistry.list_marketplaces())
            raise ScraperError(f"URL não suportada. Marketplaces ativos: {available}")
        
        product_id = scraper.extract_product_id(url)
        cache_key = f"product:{scraper.marketplace.value}:{product_id}"
        
        if not bypass_cache:
            cached = await cache.get(cache_key, Product)
            if cached:
                return cached
        
        product = await scraper.scrape_with_retry(url)
        await cache.set(cache_key, product, ttl=CacheConfig.PRODUCT_TTL)
        return product

    @staticmethod
    def to_response(product: Product) -> ProductResponse:
        return ProductResponse(
            id=product.metadata.marketplace_id,
            name=product.name,
            price=product.price,
            images=product.images,
            rating=product.rating,
            review_count=product.review_count,
            marketplace=product.metadata.marketplace,
            source_url=product.metadata.source_url,
            seller_name=product.seller_name
        )