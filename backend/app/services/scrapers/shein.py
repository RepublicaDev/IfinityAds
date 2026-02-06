import httpx
import json
import hashlib
from bs4 import BeautifulSoup
from typing import Dict, Any
from app.models.product import (
    Product, ProductPrice, ProductMetadata, Marketplace
)
from . import BaseScraper, ScraperError
import logging

logger = logging.getLogger(__name__)

class SheinScraper(BaseScraper):
    marketplace = Marketplace.SHEIN
    
    def validate_url(self, url: str) -> bool:
        return "shein" in url.lower()

    def normalize_product(self, raw: Dict[str, Any], url: str) -> Product:
        # Garantia de tipos para o Pylance
        name = str(raw.get("name") or raw.get("title") or "Produto Shein")
        price_val = float(raw.get("price") or 0.0)
        
        return Product(
            name=name,
            description=str(raw.get("description") or ""),
            price=ProductPrice(amount=price_val, currency="USD"),
            images=[],
            features=[],
            attributes=[],
            rating=float(raw.get("rating") or 0.0),
            review_count=int(raw.get("review_count") or 0),
            seller_name="Shein Official",
            seller_rating=4.5,
            metadata=ProductMetadata(
                marketplace=self.marketplace,
                marketplace_id=hashlib.md5(url.encode()).hexdigest()[:12],
                source_url=url,
            ),
            raw_data=raw
        )

    async def scrape(self, url: str) -> Product:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(timeout=self.request_timeout, headers=headers) as client:
            r = await client.get(url)
            soup = BeautifulSoup(r.text, "html.parser")
        
        # Tenta pegar dados estruturados (JSON-LD)
        ld_json = soup.find("script", type="application/ld+json")
        raw_data = {}
        if ld_json and ld_json.string:
            try:
                data = json.loads(ld_json.string)
                # LD+JSON pode ser uma lista ou um objeto único
                product_data = data[0] if isinstance(data, list) else data
                raw_data = {
                    "name": product_data.get("name"),
                    "description": product_data.get("description"),
                    "price": product_data.get("offers", {}).get("price")
                }
            except: pass

        product = self.normalize_product(raw_data, url)
        logger.info(f"✓ Shein: {product.name}")
        return product