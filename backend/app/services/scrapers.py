from abc import ABC, abstractmethod
from typing import Dict
import httpx
from bs4 import BeautifulSoup

class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self, url: str) -> Dict:
        ...

from app.services.shopee_scraper import ShopeeScraper

class GenericEcomScraper(BaseScraper):
    async def scrape(self, url: str) -> Dict:
        # Domain-based dispatch: use site-specific scrapers when possible
        if "shopee." in url:
            return await ShopeeScraper().scrape(url)

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, follow_redirects=True)
            html = r.text
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else ""
        # best-effort extraction
        price = None
        price_el = soup.select_one("[class*=price], [id*=price]")
        if price_el:
            price = price_el.get_text().strip()
        features = [li.get_text().strip() for li in soup.select("ul li")[:5]]
        return {"url": url, "title": title, "price": price, "images": [], "features": features, "raw": html[:1000]}
