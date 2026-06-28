import requests
import io

from src.config import PEXELS_API_KEY

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
