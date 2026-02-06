import httpx
from bs4 import BeautifulSoup
from .base import BaseScraper, ScraperError, ScraperRegistry
from app.models.product import Product, ProductPrice, ProductImage, ProductMetadata, Marketplace

@ScraperRegistry.register(Marketplace.ALIEXPRESS)
class AliExpressScraper(BaseScraper):
    marketplace = Marketplace.ALIEXPRESS
    
    def validate_url(self, url: str) -> bool:
        return "aliexpress" in url.lower()
    
    async def scrape(self, url: str) -> Product:
        async with httpx.AsyncClient(timeout=self.request_timeout, headers=self.common_headers, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
            
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Extração Meta com cast para String para satisfazer o Pylance
        title_tag = soup.select_one("meta[property='og:title']")
        name = str(title_tag.get("content", "Produto AliExpress")) if title_tag else "Produto AliExpress"
        
        price_tag = soup.select_one("meta[property='product:price:amount']")
        try:
            price_val = float(str(price_tag.get("content", "0"))) if price_tag else 0.0
        except (ValueError, TypeError):
            price_val = 0.0

        image_tag = soup.select_one("meta[property='og:image']")
        img_url = str(image_tag.get("content", "")) if image_tag else ""
        images = [ProductImage(url=img_url, is_primary=True, position=0)] if img_url else []

        return Product(
            name=name,
            description="",
            price=ProductPrice(amount=price_val, currency="BRL"),
            images=images,
            rating=0.0,
            review_count=0,
            seller_name="AliExpress Seller",
            seller_rating=0.0,
            metadata=ProductMetadata(
                marketplace=self.marketplace, 
                source_url=url, 
                marketplace_id=self.extract_product_id(url)
            )
        )