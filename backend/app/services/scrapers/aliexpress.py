"""
Scraper especializado para AliExpress.
Implementa interface BaseScraper com suporte a API dinâmica.
"""
import httpx
from bs4 import BeautifulSoup
import json
import re
import hashlib
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
        """Fallback robusto: extrai de meta tags e estrutura HTML."""
        result = {
            "title": None,
            "price": None,
            "images": [],
            "description": None,
            "features": []
        }
        
        # ===== TÍTULO =====
        # Tenta múltiplas fontes de título
        title_sources = [
            soup.select_one("meta[property='og:title']"),
            soup.select_one("meta[name='title']"),
            soup.select_one("h1"),
            soup.select_one("h1.product-title"),
            soup.select_one("[data-spm*='title']"),
        ]
        
        for source in title_sources:
            if source:
                title = source.get('content') if hasattr(source, 'get') else source.get_text(strip=True)
                if title and len(title) > 5:
                    result["title"] = title
                    break
        
        # ===== DESCRIÇÃO =====
        desc_sources = [
            soup.select_one("meta[property='og:description']"),
            soup.select_one("meta[name='description']"),
            soup.select_one(".product-description"),
            soup.select_one("[data-spm*='description']"),
        ]
        
        for source in desc_sources:
            if source:
                desc = source.get('content') if hasattr(source, 'get') else source.get_text(strip=True)
                if desc and len(desc) > 10:
                    result["description"] = desc
                    break
        
        # ===== PREÇO - Multi-strategy =====
        # 1. Tenta meta tags estruturadas
        price_el = soup.select_one("meta[property='product:price:amount']")
        if price_el and price_el.get('content'):
            try:
                result["price"] = float(price_el.get('content'))
            except (ValueError, TypeError):
                pass
        
        # 2. Tenta padrões de texto no HTML
        if not result["price"]:
            # Procura por "US$" ou "R$" seguido de número
            text_content = soup.get_text()
            price_patterns = [
                r'US\$\s*([\d,.]+)',
                r'R\$\s*([\d,.]+)',
                r'\$\s*([\d,.]+)',
                r'Price.*?:(.*?[\d,.]+)',
                r'price.*?:(.*?[\d,.]+)',
            ]
            
            for pattern in price_patterns:
                price_match = re.search(pattern, text_content, re.I)
                if price_match:
                    price_str = price_match.group(1).replace(',', '.').strip('$').strip()
                    try:
                        price = float(re.sub(r'[^\d.]', '', price_str))
                        if price > 0:  # Valida preço positivo
                            result["price"] = price
                            break
                    except (ValueError, AttributeError):
                        continue
        
        # 3. Tenta elementos span/div com classe de preço
        if not result["price"]:
            price_selectors = [
                "span.price",
                "div.price",
                "[class*='price']",
                "[data-spm*='price']",
            ]
            
            for selector in price_selectors:
                for el in soup.select(selector)[:3]:  # Top 3 matches
                    price_text = el.get_text(strip=True)
                    price_match = re.search(r'[\d,.]+', price_text)
                    if price_match:
                        try:
                            price = float(price_match.group().replace(',', '.'))
                            if 0.1 < price < 100000:  # Validação de range realista
                                result["price"] = price
                                break
                        except (ValueError, AttributeError):
                            continue
                if result["price"]:
                    break
        
        # ===== IMAGENS =====
        image_selectors = [
            ("meta[property='og:image']", "content"),
            ("img[src*='product']", "src"),
            ("img[src*='item']", "src"),
            ("img.product-image", "src"),
            (".product-gallery img", "src"),
            ("img[alt*='product']", "src"),
            ("img[alt*='item']", "src"),
        ]
        
        seen_urls = set()
        for selector, attr in image_selectors:
            if len(result["images"]) >= 10:
                break
            
            elements = soup.select(selector)
            for el in elements[:10]:
                img_url = el.get(attr) if attr else el.string
                
                # Normaliza URLs relativas
                if img_url:
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = 'https://aliexpress.com' + img_url
                    
                    # Remove duplicatas e URLs vazias
                    if img_url and img_url not in seen_urls and len(img_url) > 10:
                        result["images"].append(img_url)
                        seen_urls.add(img_url)
        
        # ===== FEATURES/SPECIFICATIONS =====
        # Procura por tabelas de especificações
        spec_selectors = [
            "table.specifications tbody tr",
            ".product-specs li",
            ".features li",
            ".specifications dd",
            "[class*='spec'] li",
        ]
        
        for selector in spec_selectors:
            if len(result["features"]) >= 8:
                break
            
            for el in soup.select(selector):
                text = el.get_text(strip=True)
                # Filtra linhas muito curtas ou muito longas
                if 10 < len(text) < 200:
                    result["features"].append(text)
        
        # Fallback: procura por listas com itens curtos
        if not result["features"]:
            for ul in soup.select("ul, ol"):
                for li in ul.select("li")[:8]:
                    text = li.get_text(strip=True)
                    if 10 < len(text) < 150:
                        result["features"].append(text)
        
        logger.debug(f"Meta extraction resultado: titulo={bool(result['title'])}, "
                    f"preco={result['price']}, imagens={len(result['images'])}, "
                    f"features={len(result['features'])}")
        
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
        """Converte dados brutos em Product com validações robustas."""
        
        try:
            product_id = self.extract_product_id(url)
        except ScraperError:
            product_id = hashlib.md5(url.encode()).hexdigest()[:16]
        
        # ===== VALIDAÇÃO DE TÍTULO =====
        title = raw.get("title") or raw.get("name")
        if not title or len(str(title).strip()) < 5:
            raise ScraperError("Título do produto não disponível ou inválido")
        title = str(title).strip()
        
        # ===== VALIDAÇÃO DE PREÇO =====
        price_amount = None
        
        # Tenta múltiplas chaves de preço
        price_keys = ["price", "current_price", "Price", "actualPrice", "priceCurrency"]
        for key in price_keys:
            price_val = raw.get(key)
            if price_val:
                if isinstance(price_val, str):
                    price_str = re.sub(r'[^\d.]', '', price_val)
                    try:
                        price_amount = float(price_str)
                        if price_amount > 0:
                            break
                    except ValueError:
                        continue
                elif isinstance(price_val, (int, float)):
                    price_amount = float(price_val)
                    if price_amount > 0:
                        break
        
        if not price_amount:
            raise ScraperError("Preço não encontrado ou inválido")
        
        # ===== IMAGENS =====
        images = []
        image_list = raw.get("images") or raw.get("imgList") or raw.get("image") or []
        
        # Garante que é uma lista
        if isinstance(image_list, str):
            image_list = [image_list]
        elif not isinstance(image_list, list):
            image_list = []
        
        for idx, img_url in enumerate(image_list[:10]):
            if img_url and isinstance(img_url, str):
                # Valida URL
                if img_url.startswith(('http://', 'https://', '//')):
                    images.append(ProductImage(
                        url=img_url,
                        is_primary=(idx == 0),
                        position=idx
                    ))
        
        # ===== FEATURES =====
        features = []
        
        # Tenta múltiplas chaves de features
        for feat_key in ["features", "specs", "attributes", "description", "short_description"]:
            feat_val = raw.get(feat_key)
            if feat_val:
                if isinstance(feat_val, list):
                    features = [str(f) for f in feat_val if f][:5]
                    break
                elif isinstance(feat_val, str) and len(feat_val) > 20:
                    features = [feat_val[:300]]
                    break
        
        # ===== ATRIBUTOS/VARIAÇÕES =====
        attributes = []
        raw_attrs = raw.get("attributes", {}) or {}
        
        if isinstance(raw_attrs, dict):
            for attr_name, attr_value in raw_attrs.items():
                if isinstance(attr_value, (list, tuple)):
                    for val in attr_value[:3]:
                        attributes.append(ProductAttribute(
                            name=str(attr_name),
                            value=str(val)
                        ))
        
        # ===== DESCRIÇÃO =====
        description = raw.get("description")
        if description and isinstance(description, str):
            description = description[:1000]
        
        # ===== RATING =====
        rating = raw.get("rating")
        if rating:
            try:
                rating = float(rating)
                rating = max(0, min(5, rating))  # Clamp 0-5
            except (ValueError, TypeError):
                rating = None
        
        review_count = raw.get("review_count", 0) or 0
        try:
            review_count = int(review_count)
        except (ValueError, TypeError):
            review_count = 0
        
        # ===== CONSTRUIR PRODUTO =====
        product = Product(
            name=title,
            description=description,
            price=ProductPrice(
                amount=price_amount,
                currency="USD",
                original_amount=raw.get("original_price"),
            ),
            images=images,
            features=features,
            attributes=attributes,
            rating=rating,
            review_count=review_count,
            seller_name=raw.get("seller_name"),
            metadata=ProductMetadata(
                marketplace=self.marketplace,
                marketplace_id=product_id,
                source_url=url,
            ),
            raw_data=raw
        )
        
        logger.debug(f"Produto normalizado: {product.display_name}")
        return product
    
    async def scrape(self, url: str) -> Product:
        """Scrapa produto AliExpress."""
        if not self.validate_url(url):
            raise ScraperError(f"URL não é do AliExpress: {url}")
        
        logger.info(f"Scrapando AliExpress: {url}")
        
        html = await self.fetch_html(url)
        
        # Estratégia 1: Tenta extrair dados JS embutidos
        raw_data = self.extract_data_from_window(html)
        
        # Estratégia 2: Fallback para parsing de meta tags/HTML
        if not raw_data or not raw_data.get("title"):
            soup = BeautifulSoup(html, "html.parser")
            fallback_data = self.extract_from_meta(soup)
            
            # Mescla dados: prioriza JS, mas usa fallback para campos vazios
            if raw_data:
                for key in fallback_data:
                    if not raw_data.get(key):
                        raw_data[key] = fallback_data[key]
            else:
                raw_data = fallback_data
        
        # Validação mínima antes de normalizar
        if not raw_data or not raw_data.get("title"):
            raise ScraperError(
                f"Impossível extrair dados do produto. "
                f"Verifique se a URL é válida: {url}"
            )
        
        product = self.normalize_product(raw_data, url)
        logger.info(f"✓ Produto AliExpress extraído: {product.display_name}")
        return product
