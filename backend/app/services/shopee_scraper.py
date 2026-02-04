import httpx
from bs4 import BeautifulSoup
import json
import re
from typing import Dict

class ShopeeScraper:
    """Best-effort Shopee product scraper.

    It first tries to parse structured JSON-LD in <script type="application/ld+json">.
    If not found, it attempts to extract embedded JS JSON (common in Shopee pages) using regex,
    and falls back to OpenGraph/meta tags and simple DOM queries.
    """

    async def fetch_html(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, follow_redirects=True)
            r.raise_for_status()
            return r.text

    def parse_ld_json(self, soup: BeautifulSoup) -> Dict | None:
        el = soup.find("script", type="application/ld+json")
        if not el:
            return None
        try:
            data = json.loads(el.string)
            # Data can be a dict or a list
            if isinstance(data, list):
                for entry in data:
                    if entry.get("@type") == "Product":
                        return entry
            elif data.get("@type") == "Product":
                return data
        except Exception:
            return None
        return None

    def parse_embedded_json(self, html: str) -> Dict | None:
        # Attempt to find JS objects that contain "item" or "name" keys
        # Example patterns: window.__INITIAL_STATE__ = {...};
        m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});", html, flags=re.S)
        if m:
            try:
                obj = json.loads(m.group(1))
                # navigate common structures
                # This is heuristic and may need adjustments for real Shopee changes.
                # Search recursively for a dict containing keys like 'name' and 'price'
                def find_product(d):
                    if isinstance(d, dict):
                        if 'name' in d and ('price' in d or 'current_price' in d or 'price_max' in d):
                            return d
                        for v in d.values():
                            res = find_product(v)
                            if res:
                                return res
                    elif isinstance(d, list):
                        for it in d:
                            res = find_product(it)
                            if res:
                                return res
                    return None
                return find_product(obj)
            except Exception:
                pass
        # fallback: try to find a JSON-like block with "discountedPrice"
        m2 = re.search(r"\{\s*\"item\"\s*:\s*\{.+?\}\s*\}", html, flags=re.S)
        if m2:
            try:
                return json.loads(m2.group(0))
            except Exception:
                pass
        return None

    def extract_from_soup(self, soup: BeautifulSoup) -> Dict:
        title = soup.select_one("meta[property='og:title'], meta[name='title']")
        title_text = title.get('content') if title else (soup.title.string if soup.title else '')
        price_el = soup.select_one("meta[property='product:price:amount'], meta[name*='price']")
        price = price_el.get('content') if price_el else None
        images = []
        img = soup.select_one("meta[property='og:image']")
        if img and img.get('content'):
            images.append(img.get('content'))
        bullets = [li.get_text().strip() for li in soup.select("ul li")[:8]]
        return {"title": title_text, "price": price, "images": images, "features": bullets}

    def normalize(self, raw: Dict | None, fallback: Dict) -> Dict:
        product = {"title": None, "price": None, "images": [], "features": [], "raw": None}
        if raw is None:
            product.update(fallback)
            product['raw'] = None
            return product
        # Some embedded JS objects use different keys; attempt common ones
        title = raw.get('name') or raw.get('title') or raw.get('product_name') or raw.get('item_name')
        price = raw.get('price') or raw.get('current_price') or raw.get('price_max') or raw.get('discountedPrice')
        images = raw.get('images') or raw.get('image') or []
        if isinstance(images, str):
            images = [images]
        features = []
        # collect attributes
        for k in ['attributes', 'specs', 'description', 'item_description', 'short_description']:
            v = raw.get(k)
            if v and isinstance(v, (list, tuple)):
                features += [str(x) for x in v][:8]
            elif v and isinstance(v, str):
                # split into lines
                features += [line.strip() for line in v.split('\n') if line.strip()][:8]
        # fallback attempts
        if not title:
            title = fallback.get('title')
        if not price:
            price = fallback.get('price')
        if not images:
            images = fallback.get('images', [])
        product.update({"title": title, "price": price, "images": images, "features": features, "raw": raw})
        return product

    async def scrape(self, url: str) -> Dict:
        html = await self.fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        # try ld+json
        ld = self.parse_ld_json(soup)
        fallback = self.extract_from_soup(soup)
        if ld:
            return self.normalize(ld, fallback)
        # try embedded JSON
        emb = self.parse_embedded_json(html)
        if emb:
            return self.normalize(emb, fallback)
        # final fallback
        return self.normalize(None, fallback)
