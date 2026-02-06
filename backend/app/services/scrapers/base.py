import logging
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, Dict, Type, List
from app.models.product import Product, Marketplace
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class ScraperError(Exception):
    """Exceção base para erros de scraping."""
    pass

class BaseScraper(ABC):
    """Interface abstrata (Strategy Pattern) para scrapers."""
    
    # Usamos o Marketplace.CUSTOM como fallback se o GENERIC não estiver no seu enum
    marketplace: Marketplace = Marketplace.CUSTOM
    request_timeout: int = 20
    max_retries: int = 3
    
    @abstractmethod
    async def scrape(self, url: str) -> Product:
        pass
    
    @abstractmethod
    def validate_url(self, url: str) -> bool:
        pass

    def extract_product_id(self, url: str) -> str:
        """Extrai ID único do produto via hash da URL (fallback)."""
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
    """Fábrica de scrapers (Factory Pattern)."""
    _scrapers: Dict[Marketplace, Type[BaseScraper]] = {}
    
    @classmethod
    def register(cls, marketplace: Marketplace, scraper_class: Type[BaseScraper]):
        cls._scrapers[marketplace] = scraper_class
        logger.info(f"✓ Scraper registrado: {marketplace}")
    
    @classmethod
    def get_scraper_for_url(cls, url: str) -> Optional[BaseScraper]:
        for scraper_class in cls._scrapers.values():
            instance = scraper_class()
            if instance.validate_url(url):
                return instance
        return None

    @classmethod
    def list_marketplaces(cls) -> List[Marketplace]:
        """Retorna lista de marketplaces registrados."""
        return list(cls._scrapers.keys())