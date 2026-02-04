"""
Interface abstrata para Scrapers de Produtos.
Design: Strategy Pattern com type hints forte.
"""
from abc import ABC, abstractmethod
from typing import Optional
from app.models.product import Product, Marketplace
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Interface abstrata para todos os scrapers.
    Define contrato que cada marketplace deve implementar.
    """
    
    marketplace: Marketplace = None
    request_timeout: int = 20
    max_retries: int = 3
    
    @abstractmethod
    async def scrape(self, url: str) -> Product:
        """
        Scrapa um único produto da URL.
        
        Args:
            url: URL absoluta do produto
            
        Returns:
            Product: Objeto unificado de produto
            
        Raises:
            ScraperError: Falha na extração
        """
        pass
    
    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """Valida se URL pertence a este marketplace."""
        pass
    
    async def scrape_with_retry(self, url: str) -> Product:
        """
        Scrapa com retry automático e backoff exponencial.
        """
        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10)
        )
        async def _scrape():
            return await self.scrape(url)
        
        try:
            return await _scrape()
        except Exception as e:
            logger.error(f"Scrape falhou após {self.max_retries} tentativas: {e}")
            raise


class ScraperError(Exception):
    """Exceção base para erros de scraping."""
    pass


class ScraperRegistry:
    """
    Registro centralizado de scrapers por marketplace.
    Design: Factory pattern.
    """
    _scrapers: dict[Marketplace, type[BaseScraper]] = {}
    
    @classmethod
    def register(cls, marketplace: Marketplace, scraper_class: type[BaseScraper]):
        """Registra um novo scraper."""
        cls._scrapers[marketplace] = scraper_class
        logger.info(f"✓ Scraper registrado: {marketplace.value}")
    
    @classmethod
    def get_scraper(cls, marketplace: Marketplace) -> Optional[BaseScraper]:
        """Obtém instância do scraper para um marketplace."""
        if marketplace not in cls._scrapers:
            return None
        return cls._scrapers[marketplace]()
    
    @classmethod
    def get_scraper_for_url(cls, url: str) -> Optional[BaseScraper]:
        """Encontra e retorna scraper apropriado para URL."""
        for scraper_class in cls._scrapers.values():
            scraper = scraper_class()
            if scraper.validate_url(url):
                return scraper
        return None
    
    @classmethod
    def list_marketplaces(cls) -> list[Marketplace]:
        """Lista todos os marketplaces registrados."""
        return list(cls._scrapers.keys())
