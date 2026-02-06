import httpx
from bs4 import BeautifulSoup
from .base import BaseScraper, ScraperError, ScraperRegistry
from app.models.product import Product, ProductPrice, ProductMetadata, Marketplace, ProductImage

@ScraperRegistry.register(Marketplace.SHOPEE)
class ShopeeScraper(BaseScraper):
    marketplace = Marketplace.SHOPEE
    
    def validate_url(self, url: str) -> bool:
        return "shopee.com" in url.lower()

    async def scrape(self, url: str) -> Product:
        async with httpx.AsyncClient(timeout=self.request_timeout, headers=self.common_headers, follow_redirects=True) as client:
            try:
                r = await client.get(url)
                r.raise_for_status()
            except Exception as e:
                raise ScraperError(f"Shopee Block: {e}")
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        title_tag = soup.select_one("meta[property='og:title']")
        name = str(title_tag.get("content", "Produto Shopee")) if title_tag else "Produto Shopee"
        
        price_tag = soup.select_one("meta[property='product:price:amount']")
        try:
            price_val = float(str(price_tag.get("content", "0"))) if price_tag else 0.0
        except:
            price_val = 0.0
        
        img_tag = soup.select_one("meta[property='og:image']")
        img_url = str(img_tag.get("content", "")) if img_tag else ""
        images = [ProductImage(url=img_url, is_primary=True, position=0)] if img_url else []

        return Product(
            name=name,
            description="",
            price=ProductPrice(amount=price_val, currency="BRL"),
            images=images,
            rating=0.0,         # Campo obrigatório
            review_count=0,     # Campo obrigatório
            seller_name="Vendedor Shopee",
            seller_rating=0.0,  # Campo obrigatório
            metadata=ProductMetadata(
                marketplace=self.marketplace, 
                source_url=url, 
                marketplace_id=self.extract_product_id(url)
            )
        )