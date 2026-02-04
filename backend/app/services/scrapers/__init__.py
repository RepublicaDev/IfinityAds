import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Type

# Importações de modelo (Certifique-se que esses caminhos existem)
from app.models.product import Product, Marketplace

# Use a lib real. Adicione 'tenacity' no requirements.txt
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class ScraperError(Exception):
    """Exceção base para erros de scraping."""
    pass

class BaseScraper(ABC):
    """
    Interface abstrata para todos os scrapers.
    Design: Strategy Pattern.
    """
    
    marketplace: Marketplace = None
    request_timeout: int = 20
    max_retries: int = 3
    
    @abstractmethod
    async def scrape(self, url: str) -> Product:
        """Implementação específica de cada marketplace."""
        pass
    
    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """Valida se a URL pertence ao marketplace."""
        pass
    
    async def scrape_with_retry(self, url: str) -> Product:
        """
        Executa o scrape com lógica de retry. 
        Note que o decorador agora é aplicado via chamada funcional 
        para aceitar parâmetros dinâmicos de 'self'.
        """
        
        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((ScraperError, Exception)),
            reraise=True
        )
        async def _execute_with_retry():
            return await self.scrape(url)
        
        try:
            return await _execute_with_retry()
        except Exception as e:
            logger.error(f"Falha crítica no marketplace {self.marketplace}: {e}")
            raise ScraperError(f"Erro ao processar {url} após retentativas.")

class ScraperRegistry:
    """
    Registro centralizado (Factory Pattern).
    """
    # Corrigido o type hint para ser mais explícito
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