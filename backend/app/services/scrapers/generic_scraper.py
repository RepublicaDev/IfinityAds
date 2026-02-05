import httpx
from bs4 import BeautifulSoup
from .base import BaseScraper, ScraperError
from app.models.product import Product, Marketplace

class GenericEcomScraper(BaseScraper):
    """Scraper genérico para E-commerce via BeautifulSoup."""
    
    def validate_url(self, url: str) -> bool:
        # Aceita qualquer URL para fins de teste, ou refine a lógica
        return "http" in url

    async def scrape(self, url: str) -> Product:
        try:
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Lógica básica de extração (meta tags)
            title = soup.find("meta", property="og:title")
            price = soup.find("meta", property="product:price:amount")
            image = soup.find("meta", property="og:image")

            return Product(
                title=title["content"] if title else "Produto sem título",
                price=float(price["content"]) if price else 0.0,
                image_url=image["content"] if image else "",
                original_url=url,
                marketplace=Marketplace.GENERIC
            )
        except Exception as e:
            raise ScraperError(f"Falha ao extrair dados de {url}: {str(e)}")