# backend/app/services/scrapers/__init__.py

from .base import BaseScraper, ScraperRegistry, ScraperError
from .generic_scraper import GenericEcomScraper # Certifique-se que o arquivo existe!

# Exporta explicitamente para o orchestrator encontrar
__all__ = ['BaseScraper', 'ScraperRegistry', 'ScraperError', 'GenericEcomScraper']