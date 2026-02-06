import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any
from app.models.product import (
    Product, ProductPrice, ProductMetadata, Marketplace
)
from .base import BaseScraper, ScraperError, ScraperRegistry # <--- IMPORTANTE
import logging

logger = logging.getLogger(__name__)

@ScraperRegistry.register(Marketplace.SHOPEE)
class ShopeeScraper(BaseScraper):
    marketplace = Marketplace.SHOPEE
    
    def validate_url(self, url: str) -> bool:
        return "shopee" in url.lower()

    async def scrape(self, url: str) -> Product:
        async with httpx.AsyncClient(timeout=self.request_timeout, follow_redirects=True) as client:
            try:
                r = await client.get(url)
                r.raise_for_status()
                html = r.text
            except Exception as e:
                raise ScraperError(f"Falha ao acessar Shopee: {e}")
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Pylance Fix: Garantir que title_tag e content não sejam None
        title_tag = soup.select_one("meta[property='og:title']")
        name = str(title_tag.get("content")) if title_tag and title_tag.get("content") else "Produto Shopee"
        
        price_tag = soup.select_one("meta[property='product:price:amount']")
        try:
            # Converte com fallback seguro para 0.0
            price_val = float(str(price_tag.get("content"))) if price_tag and price_tag.get("content") else 0.0
        except (ValueError, TypeError):
            price_val = 0.0
        
        return Product(
            name=name,
            description="",
            price=ProductPrice(amount=price_val, currency="BRL"),
            images=[],
            features=[],
            attributes=[],
            rating=5.0,
            review_count=0,
            seller_name="Vendedor Shopee",
            seller_rating=5.0,
            metadata=ProductMetadata(
                marketplace=self.marketplace,
                marketplace_id="shopee_id",
                source_url=url,
            ),
            raw_data={}
        )