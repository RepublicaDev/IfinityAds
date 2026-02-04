"""
Scraper especializado para Shein.
Implementa interface BaseScraper com tratamento de API mobile-friendly.
"""
import httpx
from bs4 import BeautifulSoup
import json
import re
from typing import Dict, Optional, Any
from app.models.product import (
    Product, ProductPrice, ProductImage, ProductAttribute,
    ProductMetadata, Marketplace
)
from app.services.scrapers import BaseScraper, ScraperError
import logging

logger = logging.getLogger(__name__)


class SheinScraper(BaseScraper):
    """Scraper para Shein com suporte a API mobile."""
    
    marketplace = Marketplace.SHEIN
    
    def validate_url(self, url: str) -> bool:
        """Valida URLs Shein."""
        return "shein" in url.lower()
    
    async def fetch_html(self, url: str) -> str:
        """Fetch com headers de mobile."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        }
        
        async with httpx.AsyncClient(timeout=self.request_timeout, follow_redirects=True) as client:
            try:
                r = await client.get(url, headers=headers)
                r.raise_for_status()
                return r.text
            except Exception as e:
                raise ScraperError(f"Falha ao buscar Shein: {e}")
    
    def extract_json_ld(self, html: str) -> Optional[Dict]:
        """Extrai dados estruturados de LD+JSON."""
        match = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.+?)</script>', html, re.S)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "Product":
                            return item
                elif data.get("@type") == "Product":
                    return data
            except json.JSONDecodeError:
                pass
        return None
    
    def extract_from_soup(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrai de estrutura HTML Shein."""
        result = {
            "title": None,
            "price": None,
            "images": [],
            "description": None,
            "features": [],
            "rating": None,
            "review_count": 0
        }
        
        # Title
        title_el = soup.select_one("h1, .product-title, [data-testid='product-title']")
        if title_el:
            result["title"] = title_el.get_text(strip=True)
        
        # Price - Shein usa variáveis JS frequentemente
        price_match = re.search(r'[R$USD$]*\s*([\d.,]+)', soup.get_text()[:2000])
        if price_match:
            price_str = price_match.group(1).replace(',', '.')
            try:
                result["price"] = float(price_str)
            except ValueError:
                pass
        
        # Images
        for img in soup.select("img[src*='shein'], img[data-src]"):
            img_url = img.get('src') or img.get('data-src')
            if img_url and img_url not in result["images"]:
                result["images"].append(img_url)
        
        # Features/Description
        desc_el = soup.select_one(".product-description, [data-testid='description']")
        if desc_el:
            result["description"] = desc_el.get_text(strip=True)
        
        # Features from lists
        for li in soup.select("li")[:5]:
            text = li.get_text(strip=True)
            if len(text) > 5:
                result["features"].append(text)
        
        # Rating
        rating_el = soup.select_one(".rating, [data-testid='rating']")
        if rating_el:
            rating_text = rating_el.get_text()
            rating_match = re.search(r'([\d.]+)', rating_text)
            if rating_match:
                try:
                    result["rating"] = float(rating_match.group(1))
                except ValueError:
                    pass
        
        return result
    
    def extract_product_id(self, url: str) -> str:
        """Extrai ID do produto de URL Shein."""
        # Padrão: shein.com/...?id=123 ou shein.com/p/123
        match = re.search(r'[?&]id=(\d+)', url)
        if match:
            return match.group(1)
        match = re.search(r'/p/(\d+)', url)
        if match:
            return match.group(1)
        # Fallback: gera ID do slug
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    def normalize_product(self, raw: Dict[str, Any], url: str) -> Product:
        """Converte dados brutos em Product."""
        
        product_id = self.extract_product_id(url)
        
        # Preço
        price_amount = raw.get("price")
        if not price_amount:
            raise ScraperError("Preço não encontrado")
        
        # Imagens
        images = []
        for idx, img_url in enumerate((raw.get("images") or [])[:10]):
            if img_url:
                images.append(ProductImage(
                    url=img_url,
                    is_primary=(idx == 0),
                    position=idx
                ))
        
        # Features
        features = raw.get("features", [])
        if raw.get("description"):
            features = [raw["description"][:200]] + features
        
        product = Product(
            name=raw.get("title") or "Produto Shein",
            description=raw.get("description"),
            price=ProductPrice(
                amount=float(price_amount),
                currency="USD",
            ),
            images=images,
            features=features[:5],
            rating=raw.get("rating"),
            review_count=raw.get("review_count", 0),
            metadata=ProductMetadata(
                marketplace=self.marketplace,
                marketplace_id=product_id,
                source_url=url,
            ),
            raw_data=raw
        )
        
        return product
    
    async def scrape(self, url: str) -> Product:
        """Scrapa produto Shein."""
        if not self.validate_url(url):
            raise ScraperError(f"URL não é do Shein: {url}")
        
        logger.info(f"Scrapando Shein: {url}")
        
        html = await self.fetch_html(url)
        
        # Tentativa 1: LD+JSON
        raw_data = self.extract_json_ld(html)
        
        # Fallback: HTML parsing
        if not raw_data:
            soup = BeautifulSoup(html, "lxml")
            raw_data = self.extract_from_soup(soup)
        
        product = self.normalize_product(raw_data or {}, url)
        logger.info(f"✓ Produto Shein extraído: {product.display_name}")
        return product
