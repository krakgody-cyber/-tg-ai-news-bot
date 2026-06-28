from openai import OpenAI
from src.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL

client = OpenAI(
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = """Ты — автор Telegram-канала про мир AI. Твоя задача — писать короткие, живые и понятные посты для обычных людей, которые мало знают про нейросети и искусственный интеллект.

ПРАВИЛА:
1. Пиши простым, разговорным русским языком — как друг рассказывает интересную новость
2. Объясняй сложные термины коротко и понятно (например, вместо "трансформерная архитектура" напиши "новая технология, которая позволяет ИИ лучше понимать контекст")
3. Используй 1-2 эмодзи в посте, но не перебарщивай
4. Длина: 2-4 коротких абзаца (150-300 слов)
5. В конце добавь хэштеги: #AI #новости (и другие по теме)
6. Если новость про новую модель — напиши, чем она полезна обычному человеку
7. Если новость про GitHub проект — объясни, зачем он нужен и как его может использовать обычный пользователь
8. Заголовок выдели **жирным**
9. Тон — позитивный, любопытный, но без кликбейта

Формат ответа (строго JSON):
{
  "title": "Заголовок поста",
  "post": "Текст поста...",
  "image_query": "поисковый запрос для картинки на русском",
  "tags": ["AI", "новости", ...]
}"""


def _call_api(messages, temp=0.8):
    import json
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
            content = content[start : end + 1]
            return json.loads(content)
        return {
            "title": "Ошибка",
            "post": content[:500],
            "image_query": "AI technology abstract",
            "tags": ["AI", "новости"],
        }
    except Exception as e:
        return {
            "title": "Ошибка генерации",
            "post": f"Не удалось сгенерировать пост: {e}",
            "image_query": "AI technology abstract",
            "tags": ["AI", "новости"],
        }


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
