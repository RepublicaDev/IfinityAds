from typing import Optional, List, Any, cast
import logging
import asyncio

# Importamos Marketplace e o tipo ProductPrice que o Pylance está exigindo
from app.models.product import Product, ProductResponse, Marketplace
# Se o Pylance reclamar que ProductPrice não foi importado, adicione-o na linha acima
from app.core.cache import cache, CacheConfig
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
            try:
                cached = await cache.get(cache_key, Product)
                if cached:
                    return cached
            except Exception as e:
                logger.warning(f"Falha ao ler cache: {e}")
        
        product = await scraper.scrape_with_retry(url)
        await cache.set(cache_key, product, ttl=CacheConfig.PRODUCT_TTL)
        return product

    @staticmethod
    async def scrape_products_batch(urls: List[str], bypass_cache: bool = False) -> List[Product]:
        tasks = [ProductScraperService.scrape_product(url, bypass_cache) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [res for res in results if isinstance(res, Product)]

    @staticmethod
    def to_response(product: Product) -> ProductResponse:
        """Converte o modelo interno para o modelo de saída da API (DTO)"""
        
        metadata = getattr(product, 'metadata', None)
        m_id = "unknown"
        m_type: Marketplace = Marketplace.GENERIC
        s_url = ""

        if metadata:
            m_id = getattr(metadata, 'marketplace_id', m_id)
            m_val = getattr(metadata, 'marketplace', Marketplace.GENERIC)
            if isinstance(m_val, Marketplace):
                m_type = m_val
            s_url = getattr(metadata, 'source_url', s_url)

        # SOLUÇÃO PARA O PYLANCE:
        # 1. Pegamos o objeto price original. 
        # 2. Usamos Any para "silenciar" a reclamação de float vs ProductPrice na atribuição.
        price_data: Any = getattr(product, 'price', None)

        return ProductResponse(
            id=str(m_id),
            name=getattr(product, 'name', "Produto sem nome") or "Produto sem nome",
            price=price_data, # O Pydantic fará a validação interna ao instanciar
            images=list(getattr(product, 'images', []) or []),
            rating=float(getattr(product, 'rating', 0.0) or 0.0),
            review_count=int(getattr(product, 'review_count', 0) or 0),
            marketplace=m_type,
            source_url=s_url,
            seller_name=getattr(product, 'seller_name', "Vendedor não identificado") or "Vendedor não identificado"
        )