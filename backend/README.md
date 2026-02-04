InfinityAd AI - Backend

This folder contains the FastAPI backend for InfinityAd AI.

- Start dev server: uvicorn backend.main:app --reload --port 8000
- Place your Firebase service account JSON at the path configured by FIREBASE_KEY_PATH in your .env

Shopee Scraper

A site-specific Shopee scraper was added at `app/services/shopee_scraper.py`. It attempts to parse structured data (`application/ld+json`), embedded JS product objects, and falls back to OpenGraph/meta tags.

There are unit tests in `backend/tests/test_shopee_scraper.py` using an example fixture `backend/tests/fixtures/shopee_sample.html`.
