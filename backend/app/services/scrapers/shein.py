import httpx
import json
from bs4 import BeautifulSoup
from .base import BaseScraper, ScraperError, ScraperRegistry
from app.models.product import Product, ProductPrice, ProductMetadata, Marketplace, ProductImage

@ScraperRegistry.register(Marketplace.SHEIN)
class SheinScraper(BaseScraper):
    marketplace = Marketplace.SHEIN
    
    def validate_url(self, url: str) -> bool:
        return "shein.com" in url.lower()

    async def scrape(self, url: str) -> Product:
        async with httpx.AsyncClient(timeout=self.request_timeout, headers=self.common_headers, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
        
        soup = BeautifulSoup(r.text, "html.parser")
        ld_json = soup.find("script", type="application/ld+json")
        
        data = {}
        # Correção Pylance: Acessando o conteúdo de texto de forma segura
        json_text = ld_json.get_text() if ld_json else None
        
        if json_text:
            try:
                js_data = json.loads(json_text)
                data = js_data[0] if isinstance(js_data, list) else js_data
            except: pass

        price_val = 0.0
        if isinstance(data.get("offers"), dict):
            price_val = float(data["offers"].get("price", 0.0))

        return Product(
            name=str(data.get("name", "Produto Shein")),
            description=str(data.get("description", "")),
            price=ProductPrice(amount=price_val, currency="BRL"),
            images=[ProductImage(url=str(data.get("image")), is_primary=True)] if data.get("image") else [],
            rating=float(data.get("aggregateRating", {}).get("ratingValue", 0.0)) if isinstance(data.get("aggregateRating"), dict) else 0.0,
            review_count=int(data.get("aggregateRating", {}).get("reviewCount", 0)) if isinstance(data.get("aggregateRating"), dict) else 0,
            seller_name="SHEIN",
            seller_rating=4.8,
            metadata=ProductMetadata(
                marketplace=self.marketplace,
                source_url=url,
                marketplace_id=self.extract_product_id(url)
            )
        )