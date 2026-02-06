import httpx
import json
import hashlib
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from app.models.product import Product, ProductPrice, ProductMetadata, Marketplace
from . import BaseScraper, ScraperError

logger = logging.getLogger(__name__)

class SheinScraper(BaseScraper):
    marketplace = Marketplace.SHEIN
    
    def validate_url(self, url: str) -> bool:
        return "shein" in url.lower()

    def normalize_product(self, raw: Dict[str, Any], url: str) -> Product:
        name = str(raw.get("name") or "Produto Shein")
        price_val = float(raw.get("price") or 0.0)
        
        return Product(
            name=name,
            description=str(raw.get("description") or ""),
            price=ProductPrice(amount=price_val, currency="USD"),
            images=[],
            rating=float(raw.get("rating") or 0.0),
            review_count=int(raw.get("review_count") or 0),
            seller_rating=4.5,
            metadata=ProductMetadata(
                marketplace=self.marketplace,
                marketplace_id=hashlib.md5(url.encode()).hexdigest()[:12],
                source_url=url,
            )
        )

    async def scrape(self, url: str) -> Product:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(timeout=self.request_timeout, headers=headers) as client:
            r = await client.get(url)
            soup = BeautifulSoup(r.text, "html.parser")
        
        # Acessamos como Any para o Pylance parar de reclamar de .string e .text
        ld_json: Any = soup.find("script", type="application/ld+json")
        raw_data: Dict[str, Any] = {}
        
        if ld_json and hasattr(ld_json, 'string') and ld_json.string:
            try:
                data = json.loads(str(ld_json.string))
                product_data = data[0] if isinstance(data, list) else data
                
                offers = product_data.get("offers", {})
                price = offers.get("price") if isinstance(offers, dict) else 0.0
                
                raw_data = {
                    "name": product_data.get("name"),
                    "description": product_data.get("description"),
                    "price": price
                }
            except Exception:
                logger.warning("Falha ao parsear JSON-LD da Shein")

        product = self.normalize_product(raw_data, url)
        return product