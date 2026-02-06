import httpx
from bs4 import BeautifulSoup
from typing import Any, Optional
from .base import BaseScraper, ScraperError
from app.models.product import Product, Marketplace, ProductPrice, ProductMetadata, ProductImage

class GenericEcomScraper(BaseScraper):
    marketplace = Marketplace.CUSTOM

    def validate_url(self, url: str) -> bool:
        return "http" in url

    async def scrape(self, url: str) -> Product:
        try:
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Usamos find().get() que é suportado pela interface do BS4
            # mas acessamos de forma que o Pylance não tente validar o __getitem__
            def get_meta(prop: str) -> Optional[str]:
                tag: Any = soup.find("meta", property=prop)
                return tag.get("content") if tag else None

            name = get_meta("og:title") or "Produto Sem Nome"
            raw_price = get_meta("product:price:amount")
            image_url = get_meta("og:image")

            price_val = float(raw_price) if raw_price else 0.01

            return Product(
                name=str(name),
                description=None,
                price=ProductPrice(amount=price_val, currency="BRL"),
                images=[ProductImage(url=str(image_url))] if image_url else [],
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