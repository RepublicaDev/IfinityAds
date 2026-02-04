"""
Serviço unificado de Scraping com integração de Cache.
Design: Facade pattern sobre registry de scrapers.
"""
from typing import Optional
from app.models.product import Product, ProductResponse, Marketplace
from app.core.cache import cache, CacheKey, CacheConfig
from app.services.scrapers import ScraperRegistry, ScraperError, BaseScraper
from app.services.scrapers.shopee import ShopeeScraper
from app.services.scrapers.aliexpress import AliExpressScraper
from app.services.scrapers.shein import SheinScraper
import logging

logger = logging.getLogger(__name__)


class ProductScraperService:
    """
    Serviço centralizado de scraping com cache distribuído.
    Gerencia múltiplos scrapers e cache transparentemente.
    """
    
    # Inicialização de scrapers (executar uma vez na startup)
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Registra todos os scrapers disponíveis."""
        if cls._initialized:
            return
        
        ScraperRegistry.register(Marketplace.SHOPEE, ShopeeScraper)
        ScraperRegistry.register(Marketplace.ALIEXPRESS, AliExpressScraper)
        ScraperRegistry.register(Marketplace.SHEIN, SheinScraper)
        
        logger.info(f"✓ {len(ScraperRegistry.list_marketplaces())} scrapers registrados")
        cls._initialized = True
    
    @staticmethod
    async def scrape_product(url: str, bypass_cache: bool = False) -> Product:
        """
        Scrapa um produto, usando cache se disponível.
        
        Args:
            url: URL absoluta do produto
            bypass_cache: Se True, ignora cache e atualiza
            
        Returns:
            Product: Objeto unificado com dados completos
            
        Raises:
            ScraperError: Falha na extração ou marketplace não suportado
        """
        # Tenta encontrar scraper apropriado
        scraper = ScraperRegistry.get_scraper_for_url(url)
        if not scraper:
            raise ScraperError(
                f"Marketplace não suportado para URL: {url}\n"
                f"Marketplaces disponíveis: {', '.join(m.value for m in ScraperRegistry.list_marketplaces())}"
            )
        
        # Tenta extrair chave de cache
        try:
            # Faz parsing preliminar para pegar IDs
            product_id = scraper.extract_product_id(url)
            cache_key = CacheKey.product(scraper.marketplace.value, product_id)
        except Exception as e:
            logger.warning(f"Não foi possível construir chave de cache: {e}")
            cache_key = None
        
        # Tenta recuperar do cache
        if cache_key and not bypass_cache and await cache.exists(cache_key):
            try:
                cached_product = await cache.get(cache_key, Product)
                if cached_product:
                    logger.info(f"✓ Cache HIT: {cache_key}")
                    return cached_product
            except Exception as e:
                logger.warning(f"Erro ao recuperar do cache: {e}")
        
        # Scrapa com retry
        try:
            product = await scraper.scrape_with_retry(url)
            
            # Armazena no cache
            if cache_key:
                try:
                    await cache.set(cache_key, product, ttl=CacheConfig.PRODUCT_TTL)
                    logger.info(f"✓ Cache SET: {cache_key} (TTL: {CacheConfig.PRODUCT_TTL}s)")
                except Exception as e:
                    logger.warning(f"Falha ao cachear: {e}")
            
            return product
        
        except ScraperError as e:
            logger.error(f"Erro ao scrapear {url}: {e}")
            raise
    
    @staticmethod
    async def scrape_products_batch(urls: list[str], bypass_cache: bool = False) -> list[Product]:
        """
        Scrapa múltiplos produtos em paralelo com cache.
        
        Args:
            urls: Lista de URLs para scrapear
            bypass_cache: Se True, ignora cache para todos
            
        Returns:
            Lista de Products (mantém ordem)
        """
        import asyncio
        
        tasks = [
            ProductScraperService.scrape_product(url, bypass_cache)
            for url in urls
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        products = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Falha ao scrapear {urls[idx]}: {result}")
                continue
            products.append(result)
        
        return products
    
    @staticmethod
    async def invalidate_cache(marketplace: Optional[Marketplace] = None):
        """
        Invalida cache para um marketplace específico ou todos.
        
        Args:
            marketplace: Marketplace específico ou None para limpar tudo
        """
        if marketplace:
            pattern = f"product:{marketplace.value}:*"
            count = await cache.clear_pattern(pattern)
            logger.info(f"✓ {count} itens removidos do cache para {marketplace.value}")
        else:
            count = await cache.clear_pattern("product:*")
            logger.info(f"✓ {count} itens removidos do cache total")
    
    @staticmethod
    def to_response(product: Product) -> ProductResponse:
        """Converte Product para ProductResponse para API."""
        return ProductResponse(
            id=product.metadata.marketplace_id,
            name=product.display_name,
            price=product.price,
            images=product.images,
            rating=product.rating,
            review_count=product.review_count,
            marketplace=product.metadata.marketplace,
            source_url=product.metadata.source_url,
            seller_name=product.seller_name
        )
