"""
Scraper especializado para Shopee.
Implementa interface BaseScraper com suporte a parsing robusto.
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


class ShopeeParser:
    """Parser interno para diferentes estruturas Shopee."""
    
    @staticmethod
    def parse_ld_json(soup: BeautifulSoup) -> Optional[Dict]:
        """Tenta extrair Schema.org (LD+JSON)."""
        el = soup.find("script", type="application/ld+json")
        if not el:
            return None
        try:
            data = json.loads(el.string)
            if isinstance(data, list):
                for entry in data:
                    if entry.get("@type") == "Product":
                        return entry
            elif data.get("@type") == "Product":
                return data
        except Exception as e:
            logger.debug(f"LD+JSON parse erro: {e}")
        return None
    
    @staticmethod
    def parse_embedded_json(html: str) -> Optional[Dict]:
        """Tenta extrair dados embutidos em variáveis JS."""
        patterns = [
            r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});",
            r"window\.__data\s*=\s*(\{.+?\});",
            r"\"product\"\s*:\s*(\{.+?\})\s*[,}]",
        ]
        
        for pattern in patterns:
            m = re.search(pattern, html, flags=re.S)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception as e:
                    logger.debug(f"Embedded JSON parse error: {e}")
        return None
    
    @staticmethod
    def extract_from_meta(soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrai dados de OpenGraph e meta tags."""
        result = {
            "title": None,
            "price": None,
            "images": [],
            "description": None,
            "features": []
        }
        
        # Title
        title_el = soup.select_one("meta[property='og:title'], meta[name='title']")
        if title_el:
            result["title"] = title_el.get('content')
        
        # Price
        price_el = soup.select_one("meta[property='product:price:amount']")
        if price_el:
            result["price"] = float(price_el.get('content', 0))
        
        # Images
        for img_el in soup.select("meta[property='og:image']"):
            if img_url := img_el.get('content'):
                result["images"].append(img_url)
        
        # Description
        desc_el = soup.select_one("meta[property='og:description']")
        if desc_el:
            result["description"] = desc_el.get('content')
        
        # Features from lists
        for li in soup.select("ul li")[:10]:
            text = li.get_text().strip()
            if text:
                result["features"].append(text)
        
        return result


class ShopeeScraper(BaseScraper):
    """Scraper para Shopee com fallback robusto."""
    
    marketplace = Marketplace.SHOPEE
    
    def validate_url(self, url: str) -> bool:
        """Valida URLs Shopee."""
        return "shopee.com" in url.lower() or "shopee.co" in url.lower()
    
    async def fetch_html(self, url: str) -> str:
        """Faz request HTTP com headers realistas."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        async with httpx.AsyncClient(timeout=self.request_timeout, follow_redirects=True) as client:
            try:
                r = await client.get(url, headers=headers)
                r.raise_for_status()
                return r.text
            except Exception as e:
                raise ScraperError(f"Falha ao buscar URL {url}: {e}")
    
    def parse_html(self, html: str) -> Dict[str, Any]:
        """Pipeline de parsing com múltiplos fallbacks."""
        soup = BeautifulSoup(html, "lxml")
        
        # Tentativa 1: LD+JSON
        data = ShopeeParser.parse_ld_json(soup)
        if data:
            logger.debug("✓ LD+JSON parsing bem-sucedido")
            return data
        
        # Tentativa 2: JS embutido
        data = ShopeeParser.parse_embedded_json(html)
        if data:
            logger.debug("✓ Embedded JSON parsing bem-sucedido")
            return data
        
        # Fallback 3: Meta tags
        data = ShopeeParser.extract_from_meta(soup)
        logger.debug("✓ Meta tags parsing bem-sucedido (fallback)")
        return data
    
    def extract_product_id(self, url: str) -> str:
        """Extrai ID do produto da URL."""
        # Padrão: shopee.com/product/id ou shopee.com.br/product/id/slug
        match = re.search(r'product/(\d+)', url)
        if match:
            return match.group(1)
        raise ScraperError(f"Não foi possível extrair ID do produto de: {url}")
    
    def normalize_product(self, raw: Dict[str, Any], url: str) -> Product:
        """Converte dados brutos em Product unificado."""
        
        product_id = self.extract_product_id(url)
        
        # Extrai preço
        price_amount = None
        if raw.get("price"):
            price_amount = float(raw["price"])
        elif raw.get("current_price"):
            price_amount = float(raw["current_price"])
        else:
            raise ScraperError("Não foi possível extrair preço")
        
        # Extrai imagens
        images = []
        for idx, img_url in enumerate(raw.get("images", [])[:10]):
            if isinstance(img_url, str):
                images.append(ProductImage(
                    url=img_url,
                    is_primary=(idx == 0),
                    position=idx
                ))
        
        # Extrai atributos/features
        features = raw.get("features", [])
        if isinstance(raw.get("description"), str):
            features = [raw["description"]] + features
        
        # Construir modelo
        product = Product(
            name=raw.get("title") or raw.get("name") or "Produto Shopee",
            description=raw.get("description"),
            price=ProductPrice(
                amount=price_amount,
                currency="BRL",
                original_amount=raw.get("original_price"),
            ),
            images=images,
            features=features[:5],
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
        """Scrapa produto Shopee."""
        if not self.validate_url(url):
            raise ScraperError(f"URL não é do Shopee: {url}")
        
        logger.info(f"Scrapando Shopee: {url}")
        
        html = await self.fetch_html(url)
        raw_data = self.parse_html(html)
        product = self.normalize_product(raw_data, url)
        
        logger.info(f"✓ Produto extraído: {product.display_name}")
        return product
