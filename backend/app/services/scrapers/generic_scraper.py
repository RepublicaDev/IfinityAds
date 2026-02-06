import httpx
from bs4 import BeautifulSoup
from .base import BaseScraper, ScraperError
from app.models.product import Product, Marketplace, ProductPrice, ProductMetadata, ProductImage

class GenericEcomScraper(BaseScraper):
    """Scraper genérico para E-commerce via BeautifulSoup."""
    
    marketplace = Marketplace.CUSTOM

    def validate_url(self, url: str) -> bool:
        return "http" in url

    async def scrape(self, url: str) -> Product:
        try:
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extração segura
            og_title = soup.find("meta", property="og:title")
            og_price = soup.find("meta", property="product:price:amount")
            og_image = soup.find("meta", property="og:image")

            name = str(og_title["content"]) if og_title and og_title.get("content") else "Produto Sem Nome"
            price_val = float(og_price["content"]) if og_price and og_price.get("content") else 0.01

            # Montagem do objeto respeitando o product.py
            return Product(
                name=name,
                description=None,
                price=ProductPrice(amount=price_val, currency="BRL"),
                images=[ProductImage(url=str(og_image["content"]))] if og_image else [],
                metadata=ProductMetadata(
                    marketplace=self.marketplace,
                    marketplace_id=self.extract_product_id(url),
                    source_url=url
                ),
                rating=0.0,
                review_count=0,
                seller_rating=0.0,
                is_available=True
            )
        except Exception as e:
            raise ScraperError(f"Falha ao extrair dados de {url}: {str(e)}")