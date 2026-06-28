from openai import OpenAI
from src.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL

client = OpenAI(
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = """Ты — автор Telegram-канала про технологии. Пиши коротко, живо и понятно для обычных людей.

ПРАВИЛА:
1. Максимум 3 коротких абзаца (80-150 слов), без воды
2. Начинай пост с одного уместного эмодзи
3. Пиши простым разговорным языком, как человек другу
4. Никаких хэштегов, длинных тире (—), шаблонных фраз
5. Только короткий дефис (-)
6. Тон — живой, естественный, без кликбейта
7. Заголовок **жирным**

Формат (строго JSON):
{"title": "Заголовок", "post": "текст...", "image_query": "запрос для картинки на русском", "tags": []}"""


def _clean_text(text):
    import re
    text = re.sub(r"\u2014|\u2013", "-", text)
    text = re.sub(r"#\S+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def _call_api(messages, temp=0.8):
    import json
    import re
    try:
        resp = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            temperature=temp,
            max_tokens=1500,
        )
        content = resp.choices[0].message.content.strip()
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            data = json.loads(content[start : end + 1])
            if "post" in data:
                data["post"] = _clean_text(data["post"])
            if "title" in data:
                data["title"] = _clean_text(data["title"])
            return data
        return {"title": "Ошибка", "post": _clean_text(content[:500]), "image_query": "AI technology abstract", "tags": []}
    except Exception as e:
        return {"title": "Ошибка генерации", "post": f"Не удалось сгенерировать пост: {e}", "image_query": "AI technology abstract", "tags": []}


def generate_post(news_items):
    news_text = ""
    for i, item in enumerate(news_items[:8], 1):
        news_text += (
            f"\n{i}. [{item['source']}] {item['title']}\n"
            f"   {item['summary'][:300]}\n"
            f"   {item['url']}\n"
        )

    if not news_text.strip():
        return None

    return _call_api([
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Вот свежие новости из мира AI. Выбери самую интересную и важную "
                "для обычных людей и напиши пост для Telegram-канала:\n\n"
                + news_text
            ),
        },
    ])


def generate_topic_post(topic, news_items):
    news_text = ""
    for i, item in enumerate(news_items[:8], 1):
        news_text += (
            f"\n{i}. [{item['source']}] {item['title']}\n"
            f"   {item['summary'][:300]}\n"
            f"   {item['url']}\n"
        )

    return _call_api([
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Мне нужен пост на тему: «{topic}».\n\n"
                "Вот что удалось найти по этой теме. Напиши пост для Telegram-канала, "
                "используя эти материалы:\n\n"
                + news_text
            ),
        },
    ])


def regenerate_post(source_url, title, old_content):
    return _call_api([
        {
            "role": "system",
            "content": SYSTEM_PROMPT + (
                "\n\nВАЖНО: Напиши ДРУГОЙ вариант поста на ту же тему."
                " Смени угол подачи, используй другие факты, другой стиль."
                " Предыдущий вариант поста уже был написан, не повторяй его."
            )
        },
        {
            "role": "user",
            "content": (
                "Вот новость, по которой уже был написан пост. Напиши ДРУГОЙ вариант:\n\n"
                f"Источник: {source_url}\n"
                f"Предыдущий заголовок: {title}\n"
                f"Предыдущий пост: {old_content[:500]}\n\n"
                "Напиши совершенно другой пост на ту же тему — другой угол, другой стиль, другие акценты."
            ),
        },
    ], temp=0.9)
