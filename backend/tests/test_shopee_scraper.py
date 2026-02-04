import asyncio
from app.services.shopee_scraper import ShopeeScraper

import pathlib

sample_path = pathlib.Path(__file__).parent / 'fixtures' / 'shopee_sample.html'
html = sample_path.read_text()

async def test_parse_ld_json():
    s = ShopeeScraper()
    # call parsing methods directly
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    ld = s.parse_ld_json(soup)
    assert ld is not None
    assert ld.get('name') == 'Sample Shopee Product'

async def test_normalize_from_ld():
    s = ShopeeScraper()
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    ld = s.parse_ld_json(soup)
    fallback = s.extract_from_soup(soup)
    prod = s.normalize(ld, fallback)
    assert prod['title'] == 'Sample Shopee Product'
    assert prod['price'] == '49.90' or prod['price'] == '49.90'

# Run with pytest-asyncio or similar runner
if __name__ == '__main__':
    asyncio.run(test_parse_ld_json())
    asyncio.run(test_normalize_from_ld())
