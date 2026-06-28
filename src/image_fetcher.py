import io
import re
import requests

from src.config import PEXELS_API_KEY

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

PEXELS_HEADERS = {"Authorization": PEXELS_API_KEY}


def search_pexels(query, per_page=1):
    if not PEXELS_API_KEY:
        return None
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers=PEXELS_HEADERS,
            params={"query": query, "per_page": per_page, "orientation": "landscape"},
            timeout=15,
        )
        if resp.ok:
            data = resp.json()
            if data.get("photos"):
                photo = data["photos"][0]
                return photo["src"]["large"]
    except Exception:
        pass
    return None


def fetch_og_image(source_url):
    if not source_url:
        return None
    try:
        resp = requests.get(source_url, headers=HEADERS, timeout=15)
        if not resp.ok:
            return None
        html = resp.text
        patterns = [
            r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
            r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
            r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']',
            r'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']twitter:image["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                img_url = match.group(1)
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(source_url)
                    img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
                return img_url
    except Exception:
        pass
    return None


def search_duckduckgo(query):
    try:
        resp = requests.get(
            "https://duckduckgo.com/i.js",
            params={"q": query, "o": "json", "l": "ru-ru", "f": ",,,", "p": "-1"},
            headers=HEADERS,
            timeout=15,
        )
        if resp.ok:
            data = resp.json()
            results = data.get("results", [])
            if results:
                return results[0].get("image")
    except Exception:
        pass
    return None


def get_image(image_query, source_url):
    img = search_pexels(image_query)
    if img:
        return img
    img = fetch_og_image(source_url)
    if img:
        return img
    img = search_duckduckgo(image_query)
    if img:
        return img
    return None


def download_image(url):
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=15)
        if resp.ok:
            return io.BytesIO(resp.content)
    except Exception:
        pass
    return None
