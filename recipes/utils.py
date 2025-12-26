"""Scraper helpers used for shopping images and related metadata."""

import logging
import requests
import re
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


def _normalize_img_url(page_url: str, img_url: str) -> str:
    """
    Turn relative / protocol-relative URLs into absolute https URLs.
    """
    img = img_url.strip()

    # //cdn.site.com/image.jpg → https://cdn.site.com/image.jpg
    if img.startswith("//"):
        return "https:" + img

    # /images/product.jpg → absolute using page_url
    if img.startswith("/"):
        return urljoin(page_url, img)

    # no scheme (images/x.jpg) → also join with page_url
    if not re.match(r"^https?://", img, re.IGNORECASE):
        return urljoin(page_url, img)

    return img


def scrape_product_image(url: str | None) -> str | None:
    """
    Given a product/shop URL, try to extract a good image URL.

    Strategy:
      1. Look for og:image, twitter:image, or <link rel="image_src">.
         (attributes can be in any order)
      2. If nothing found, fall back to the first <img src="..."> tag.
    """
    if not url:
        return None

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code != 200:
            logger.warning("[scraper] Non-200 for %s: %s", url, resp.status_code)
            return None

        html = resp.text or ""

        # 1) Meta & link tags (attributes in ANY order)
        meta_patterns = [
            # <meta property="og:image" content="...">
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']',
            # <meta content="..." property="og:image">
            r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:image["\']',

            # <meta name="twitter:image" content="...">
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\'](.*?)["\']',
            # <meta content="..." name="twitter:image">
            r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']twitter:image["\']',

            # <link rel="image_src" href="...">
            r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\'](.*?)["\']',
        ]

        for pat in meta_patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                img_url = _normalize_img_url(url, m.group(1))
                return img_url

        # 2) Fallback: first <img src="...">
        img_tag_pattern = r'<img[^>]+src=["\'](.*?)["\']'
        m = re.search(img_tag_pattern, html, re.IGNORECASE)
        if m:
            img_url = _normalize_img_url(url, m.group(1))
            return img_url

    except Exception as e:
        logger.warning("[scraper] Error while scraping %s: %s", url, e)

    return None
