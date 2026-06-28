import feedparser
import requests
from datetime import datetime, timezone
import html
import re


RSS_SOURCES = [
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/ai-artificial-intelligence/rss.xml",
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
    },
    {
        "name": "Hugging Face Papers",
        "url": "https://huggingface.co/papers?format=rss",
    },
    {
        "name": "Arxiv AI (cs.AI)",
        "url": "http://export.arxiv.org/rss/cs.AI",
    },
    {
        "name": "GitHub Trending",
        "url": "https://github.com/trending.rss",
    },
    {
        "name": "Reddit ML",
        "url": "https://www.reddit.com/r/MachineLearning/.rss",
    },
    {
        "name": "Reddit Artificial",
        "url": "https://www.reddit.com/r/artificial/.rss",
    },
    {
        "name": "Reddit LocalLLaMA",
        "url": "https://www.reddit.com/r/LocalLLaMA/.rss",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def clean_html(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_rss(url, source_name):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        items = []
        for entry in feed.entries[:10]:
            title = clean_html(entry.get("title", ""))
            link = entry.get("link", "")
            summary = clean_html(entry.get("summary", entry.get("description", "")))[:500]
            published = entry.get("published", "")
            items.append({
                "source": source_name,
                "title": title,
                "url": link,
                "summary": summary,
                "published": published,
            })
        return items
    except Exception:
        return []


def fetch_github_trending():
    items = []
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories?q=AI+ML+LLM&sort=stars&order=desc&per_page=5",
            headers=HEADERS,
            timeout=15,
        )
        if resp.ok:
            for repo in resp.json().get("items", []):
                items.append({
                    "source": "GitHub Trending",
                    "title": f"{repo['full_name']} — {repo.get('description', '') or ''}",
                    "url": repo["html_url"],
                    "summary": f"☆ {repo.get('stargazers_count', 0)} | {repo.get('description', 'No description')}",
                    "published": "",
                })
    except Exception:
        pass
    return items


def fetch_huggingface_models():
    items = []
    try:
        resp = requests.get(
            "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=10&search=llm",
            headers=HEADERS,
            timeout=15,
        )
        if resp.ok:
            for model in resp.json():
                items.append({
                    "source": "HuggingFace Models",
                    "title": f"Новая модель: {model.get('modelId', '')}",
                    "url": f"https://huggingface.co/{model.get('modelId', '')}",
                    "summary": f"Загрузок: {model.get('downloads', 0):,}".replace(",", " "),
                    "published": "",
                })
    except Exception:
        pass
    return items


COLLECTORS = [
    ("RSS", fetch_rss),
    ("GitHub", fetch_github_trending),
    ("HuggingFace", fetch_huggingface_models),
]


def collect_news():
    all_items = []

    for name, func in COLLECTORS:
        if name == "RSS":
            for source in RSS_SOURCES:
                items = fetch_rss(source["url"], source["name"])
                all_items.extend(items)
        else:
            try:
                items = func()
                all_items.extend(items)
            except Exception:
                pass

    all_items.sort(key=lambda x: x.get("published", ""), reverse=True)
    return all_items


def search_topic_news(topic):
    items = []
    query = topic.replace(" ", "+")

    try:
        resp = requests.get(
            f"https://news.google.com/rss/search?q={query}+AI&hl=en&gl=US",
            headers=HEADERS,
            timeout=20,
        )
        if resp.ok:
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:10]:
                items.append({
                    "source": "Google News",
                    "title": clean_html(entry.get("title", "")),
                    "url": entry.get("link", ""),
                    "summary": clean_html(entry.get("summary", ""))[:400],
                    "published": entry.get("published", ""),
                })
    except Exception:
        pass

    try:
        resp = requests.get(
            f"https://hnrss.org/frontpage?q={query}&count=5",
            headers=HEADERS,
            timeout=20,
        )
        if resp.ok:
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:5]:
                items.append({
                    "source": "Hacker News",
                    "title": clean_html(entry.get("title", "")),
                    "url": entry.get("link", ""),
                    "summary": clean_html(entry.get("summary", ""))[:400],
                    "published": entry.get("published", ""),
                })
    except Exception:
        pass

    try:
        resp = requests.get(
            f"https://www.reddit.com/search.rss?q={query}+AI&sort=new&limit=5",
            headers=HEADERS,
            timeout=20,
        )
        if resp.ok:
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:5]:
                items.append({
                    "source": "Reddit",
                    "title": clean_html(entry.get("title", "")),
                    "url": entry.get("link", ""),
                    "summary": clean_html(entry.get("summary", ""))[:400],
                    "published": entry.get("published", ""),
                })
    except Exception:
        pass

    items.sort(key=lambda x: x.get("published", ""), reverse=True)
    return items[:10]
