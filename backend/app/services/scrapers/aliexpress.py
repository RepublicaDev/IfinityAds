"""
Scraper especializado para AliExpress.
Implementa interface BaseScraper com suporte a API dinâmica.
"""
import httpx
from bs4 import BeautifulSoup
import json
import re
import hashlib
from typing import Dict, Optional, Any, List
from app.models.product import (
    Product, ProductPrice, ProductImage, ProductAttribute,
    ProductMetadata, Marketplace
)
from .base import BaseScraper, ScraperError, ScraperRegistry # <--- IMPORTANTE
import logging

logger = logging.getLogger(__name__)

@ScraperRegistry.register(Marketplace.ALIEXPRESS)
class AliExpressScraper(BaseScraper):
    """Scraper para AliExpress com parsing de JS dinâmico."""
    
    marketplace = Marketplace.ALIEXPRESS
    
    def validate_url(self, url: str) -> bool:
        """Valida URLs AliExpress."""
        return any(domain in url.lower() for domain in ["aliexpress.com", "aliexpress.co", "m.aliexpress.com"])
    
    async def fetch_html(self, url: str) -> str:
        """Fetch com headers simulando navegador."""
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Referer": "https://www.aliexpress.com/",
        }
        async with httpx.AsyncClient(timeout=self.request_timeout, follow_redirects=True) as client:
            try:
                r = await client.get(url, headers=headers)
                r.raise_for_status()
                return r.text
            except Exception as e:
                raise ScraperError(f"Falha ao buscar AliExpress: {e}")

    def extract_from_meta(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrai de meta tags e estrutura HTML."""
        result = {"title": None, "price": None, "images": [], "description": None, "features": []}
        
        title_el = soup.select_one("meta[property='og:title']")
        if title_el: result["title"] = title_el.get('content')
        
        price_el = soup.select_one("meta[property='product:price:amount']")
        # Correção Pylance: Verificação de None antes de converter para float
        price_val = price_el.get('content') if price_el else None
        if price_val:
            try:
                result["price"] = float(str(price_val))
            except (ValueError, TypeError): pass
            
        return result

    def normalize_product(self, raw: Dict[str, Any], url: str) -> Product:
        """Converte dados brutos em Product."""
        # Título
        title = str(raw.get("title") or raw.get("name") or "Produto AliExpress")
        
        # Preço
        price_val = raw.get("price") or 0.0
        try:
            price_amount = float(str(price_val))
        except (ValueError, TypeError):
            price_amount = 0.0

        # Imagens
        images: List[ProductImage] = []
        raw_images = raw.get("images") or []
        if isinstance(raw_images, list):
            for idx, img_url in enumerate(raw_images[:10]):
                if isinstance(img_url, str):
                    images.append(ProductImage(url=img_url, is_primary=(idx == 0), position=idx))

        # Construção do objeto Product corrigindo atributos ausentes
        product = Product(
            name=title,
            description=str(raw.get("description") or ""),
            price=ProductPrice(
                amount=price_amount,
                currency="USD"
            ),
            images=images,
            features=[str(f) for f in raw.get("features", [])],
            attributes=[],
            rating=float(raw.get("rating") or 0),
            review_count=int(raw.get("review_count") or 0),
            seller_name=str(raw.get("seller_name") or "Vendedor Global"),
            seller_rating=0.0, # Corrigido: Parâmetro faltante reportado
            metadata=ProductMetadata(
                marketplace=self.marketplace,
                marketplace_id=hashlib.md5(url.encode()).hexdigest()[:12],
                source_url=url,
            ),
            raw_data=raw
        )
        return product

    async def scrape(self, url: str) -> Product:
        html = await self.fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        raw_data = self.extract_from_meta(soup)
        product = self.normalize_product(raw_data, url)
        # Pylance: Alterado display_name para name
        logger.info(f"✓ Produto AliExpress extraído: {product.name}")
        return product