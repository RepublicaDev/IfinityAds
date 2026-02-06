import logging
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, Dict, Type, List, Any
from app.models.product import Product, Marketplace
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class ScraperError(Exception):
    pass

class BaseScraper(ABC):
    # ADICIONE ESTES DOIS CAMPOS ABAIXO:
    marketplace: Marketplace = Marketplace.GENERIC
    request_timeout: int = 30  # <--- Faltava este!
    max_retries: int = 3
    domains: List[str] = []

    @abstractmethod
    async def scrape(self, url: str) -> Product:
        pass
    
    @abstractmethod
    def validate_url(self, url: str) -> bool:
        pass

    def extract_product_id(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()[:12]
    
    async def scrape_with_retry(self, url: str) -> Product:
        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((ScraperError, Exception)),
            reraise=True
        )
        async def _execute():
            return await self.scrape(url)
        return await _execute()

class ScraperRegistry:
    _instances: Dict[Marketplace, BaseScraper] = {}
    
    @classmethod
    def register(cls, marketplace: Marketplace):
        def wrapper(scraper_cls: Type[BaseScraper]):
            cls._instances[marketplace] = scraper_cls()
            logger.info(f"✓ Scraper registrado: {marketplace.value}")
            return scraper_cls
        return wrapper
    
    @classmethod
    def get_scraper_for_url(cls, url: str) -> Optional[BaseScraper]:
        if not cls._instances:
            cls._bootstrap()
        for scraper in cls._instances.values():
            if scraper.validate_url(url):
                return scraper
        return None

    @classmethod
    def list_marketplaces(cls) -> List[Marketplace]:
        return list(cls._instances.keys())

    @classmethod
    def _bootstrap(cls):
        """
        CORREÇÃO: Importamos os nomes exatos dos arquivos .py
        """
        try:
            # Note que mudei de 'shopee_scraper' para 'shopee' (o nome do seu arquivo)
            from app.services.scrapers import shopee, aliexpress, shein, generic_scraper
        except ImportError as e:
            logger.error(f"Erro no bootstrap de scrapers: {e}")