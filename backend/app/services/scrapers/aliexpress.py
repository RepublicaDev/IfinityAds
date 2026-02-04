"""
Scraper especializado para AliExpress.
Implementa interface BaseScraper com suporte a API dinâmica.
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


class AliExpressScraper(BaseScraper):
    """Scraper para AliExpress com parsing de JS dinâmico."""
    
    marketplace = Marketplace.ALIEXPRESS
    
    def validate_url(self, url: str) -> bool:
        """Valida URLs AliExpress."""
        return any(domain in url.lower() for domain in [
            "aliexpress.com",
            "aliexpress.co",
            "m.aliexpress.com"
        ])
    
    async def fetch_html(self, url: str) -> str:
        """Fetch com headers simulando navegador."""
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Referer": "https://www.aliexpress.com/",
            "Accept": "text/html,application/xhtml+xml",
        }
        
        async with httpx.AsyncClient(timeout=self.request_timeout, follow_redirects=True) as client:
            try:
                r = await client.get(url, headers=headers)
                r.raise_for_status()
                return r.text
            except Exception as e:
                raise ScraperError(f"Falha ao buscar AliExpress: {e}")
    
    def extract_data_from_window(self, html: str) -> Optional[Dict]:
        """Extrai dados de window.__data ou window.pageData."""
        patterns = [
            r"window\.__data\s*=\s*(\{.+?\});",
            r"window\.pageData\s*=\s*(\{.+?\});",
            r"\"tradePriceList\"\s*:\s*(\[.+?\])",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.S | re.DOTALL)
            if match:
                try:
                    # Tenta fazer parse JSON
                    text = match.group(1)
                    # Remove possíveis comentários
                    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
                    return json.loads(text)
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON parse erro: {e}")
        return None
    
    def extract_from_meta(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Fallback: extrai de meta tags."""
        result = {
            "title": None,
            "price": None,
            "images": [],
            "description": None,
            "features": []
        }
        
        # OpenGraph
        title_el = soup.select_one("meta[property='og:title']")
        if title_el:
            result["title"] = title_el.get('content')
        
        desc_el = soup.select_one("meta[property='og:description']")
        if desc_el:
            result["description"] = desc_el.get('content')
        
        img_el = soup.select_one("meta[property='og:image']")
        if img_el and img_url := img_el.get('content'):
            result["images"].append(img_url)
        
        # Procura por "US$" ou "R$" no HTML
        price_match = re.search(r'(?:US\$|R\$)\s*([\d,.]+)', soup.get_text())
        if price_match:
            price_str = price_match.group(1).replace(',', '.')
            try:
                result["price"] = float(price_str)
            except ValueError:
                pass
        
        return result
    
    def extract_product_id(self, url: str) -> str:
        """Extrai item ID de URL AliExpress."""
        # Padrão: /item/{id}
        match = re.search(r'/item/(\d+)', url, re.I)
        if match:
            return match.group(1)
        # Fallback: pega do slug
        match = re.search(r'product_id=(\d+)', url)
        if match:
            return match.group(1)
        raise ScraperError(f"Não foi possível extrair ID de: {url}")
    
    def normalize_product(self, raw: Dict[str, Any], url: str) -> Product:
        """Converte dados brutos em Product."""
        
        product_id = self.extract_product_id(url)
        
        # Preço
        price_amount = None
        if raw.get("price"):
            if isinstance(raw["price"], str):
                # Remove símbolos
                price_str = re.sub(r'[^\d.]', '', raw["price"])
                price_amount = float(price_str) if price_str else None
            else:
                price_amount = float(raw["price"])
        
        if not price_amount:
            raise ScraperError("Preço não encontrado")
        
        # Imagens
        images = []
        image_list = raw.get("images") or raw.get("imgList") or []
        for idx, img_url in enumerate(image_list[:10]):
            if isinstance(img_url, str):
                images.append(ProductImage(
                    url=img_url,
                    is_primary=(idx == 0),
                    position=idx
                ))
        
        # Features
        features = []
        if raw.get("description"):
            features.append(str(raw["description"])[:300])
        
        # Variações/atributos
        attributes = []
        for attr_name, attr_value in raw.get("attributes", {}).items():
            if isinstance(attr_value, (list, tuple)):
                for val in attr_value[:3]:
                    attributes.append(ProductAttribute(
                        name=attr_name,
                        value=str(val)
                    ))
        
        product = Product(
            name=raw.get("title") or raw.get("name") or "Produto AliExpress",
            description=raw.get("description"),
            price=ProductPrice(
                amount=price_amount,
                currency="USD",
                original_amount=raw.get("original_price"),
            ),
            images=images,
            features=features,
            attributes=attributes,
            rating=raw.get("rating"),
            review_count=raw.get("review_count", 0),
            seller_name=raw.get("seller_name"),
            metadata=ProductMetadata(
                marketplace=self.marketplace,
                marketplace_id=product_id,
                source_url=url,
            ),
            raw_data=raw
        )
        
        return product
    
    async def scrape(self, url: str) -> Product:
        """Scrapa produto AliExpress."""
        if not self.validate_url(url):
            raise ScraperError(f"URL não é do AliExpress: {url}")
        
        logger.info(f"Scrapando AliExpress: {url}")
        
        html = await self.fetch_html(url)
        
        # Tenta extrair dados JS
        raw_data = self.extract_data_from_window(html)
        
        # Fallback para meta tags
        if not raw_data:
            soup = BeautifulSoup(html, "html.parser")
            raw_data = self.extract_from_meta(soup)
        
        product = self.normalize_product(raw_data or {}, url)
        logger.info(f"✓ Produto AliExpress extraído: {product.display_name}")
        return product
