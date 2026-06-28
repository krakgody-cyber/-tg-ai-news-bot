import json
import logging
import requests
import threading
from datetime import datetime

from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler

from src.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_ADMIN_ID,
    TELEGRAM_CHANNEL_ID,
    BOT_MODE,
    WEBHOOK_URL,
    PORT,
    POST_TIMES,
)
from src.database import (
    init_db,
    save_post,
    get_pending_posts,
    approve_post,
    reject_post,
    mark_posted,
    get_post,
    update_post_content,
    is_already_sent,
    mark_sent,
    set_edit_state,
    get_edit_state,
    clear_edit_state,
    get_last_post_id,
)
from src.news_collector import collect_news, search_topic_news
from src.post_generator import generate_post, regenerate_post, generate_topic_post
from src.image_fetcher import get_image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

app = Flask(__name__)
scheduler = BackgroundScheduler()


def tg_api(method, data=None, files=None):
    url = f"{API_URL}/{method}"
    try:
        if files:
            resp = requests.post(url, data=data, files=files, timeout=30)
        else:
            resp = requests.post(url, json=data, timeout=15)
        return resp.json()
    except Exception as e:
        logger.error(f"Telegram API error ({method}): {e}")
        return None


def send_message(chat_id, text, reply_markup=None, reply_to=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "link_preview_options": {"is_disabled": False},
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    if reply_to:
        data["reply_to_message_id"] = reply_to
    return tg_api("sendMessage", data)


def send_photo_post(chat_id, image_url, caption, reply_markup=None):
    try:
        img_resp = requests.get(image_url, timeout=15)
        if img_resp.ok:
            data = {
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "Markdown",
            }
            if reply_markup:
                data["reply_markup"] = reply_markup
            return tg_api("sendPhoto", data, {"photo": ("image.jpg", img_resp.content)})
    except Exception as e:
        logger.warning(f"sendPhoto failed, sending as text: {e}")
    return send_message(chat_id, caption, reply_markup)


def build_keyboard(post_id):
    return json.dumps({
        "inline_keyboard": [
            [
                {"text": "✅ Опубликовать", "callback_data": f"approve_{post_id}"},
                {"text": "🔄 Другой", "callback_data": f"regenerate_{post_id}"},
            ],
            [
                {"text": "✏️ Редактировать", "callback_data": f"edit_{post_id}"},
                {"text": "❌ Отклонить", "callback_data": f"reject_{post_id}"},
            ],
        ]
    })


def build_post_caption(title, content, tags, source_url=""):
    tags_str = " #".join([""] + (tags or ["AI", "новости"]))
    text = f"*{title}*\n\n{content}\n\n{tags_str}"
    return text


def send_post_to_admin(image_url, caption, keyboard):
    if image_url:
        return send_photo_post(TELEGRAM_ADMIN_ID, image_url, caption, keyboard)
    return send_message(TELEGRAM_ADMIN_ID, caption, keyboard)


def handle_callback(callback):
    data = callback.get("data", "")
    cb_id = callback.get("id")
    msg = callback.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))

    if str(chat_id) != str(TELEGRAM_ADMIN_ID):
        tg_api("answerCallbackQuery", {
            "callback_query_id": cb_id, "text": "Нет доступа", "show_alert": True,
        })
        return

    msg_id = msg.get("message_id")
    parts = data.split("_", 1)
    action = parts[0]
    post_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

    if action == "approve" and post_id:
        approve_post(post_id)
        post = get_post(post_id)
        if post:
            text = f"*{post['title']}*\n\n{post['content']}"
            if post.get("image_url"):
                send_photo_post(TELEGRAM_CHANNEL_ID, post["image_url"], text)
            else:
                send_message(TELEGRAM_CHANNEL_ID, text)
            mark_posted(post_id)

        tg_api("editMessageReplyMarkup", {
            "chat_id": msg["chat"]["id"],
            "message_id": msg_id,
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "✅ Опубликовано", "callback_data": "done"}]]
            }),
        })
        tg_api("answerCallbackQuery", {"callback_query_id": cb_id, "text": "✅ Опубликовано в канал!"})

    elif action == "reject" and post_id:
        reject_post(post_id)
        tg_api("editMessageReplyMarkup", {
            "chat_id": msg["chat"]["id"],
            "message_id": msg_id,
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "❌ Отклонено", "callback_data": "done"}]]
            }),
        })
        tg_api("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Пост отклонён"})

    elif action == "regenerate" and post_id:
        post = get_post(post_id)
        if not post:
            tg_api("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Ошибка: пост не найден"})
            return

        tg_api("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Генерирую другой вариант..."})

        result = regenerate_post(post["source_url"], post["title"], post["content"])
        if not result or not result.get("post"):
            send_message(TELEGRAM_ADMIN_ID, "Не удалось сгенерировать другой вариант")
            return

        new_title = result.get("title", post["title"])
        new_content = result.get("post", post["content"])
        image_query = result.get("image_query", "AI technology")
        tags = result.get("tags", ["AI", "новости"])

        old_img = post.get("image_url")
        new_image_url = get_image(image_query, post.get("source_url", "")) or old_img

        update_post_content(post_id, new_title, new_content)
        if new_image_url and new_image_url != old_img:
            from src.database import get_connection
            conn = get_connection()
            conn.execute("UPDATE posts SET image_url = ? WHERE id = ?", (new_image_url, post_id))
            conn.commit()
            conn.close()

        source_url = post.get("source_url", "")
        caption = build_post_caption(new_title, new_content, tags, source_url)
        tg_api("deleteMessage", {"chat_id": msg["chat"]["id"], "message_id": msg_id})
        send_post_to_admin(new_image_url, caption, build_keyboard(post_id))

    elif action == "edit" and post_id:
        set_edit_state(TELEGRAM_ADMIN_ID, post_id, msg_id)
        tg_api("editMessageReplyMarkup", {
            "chat_id": msg["chat"]["id"],
            "message_id": msg_id,
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "✏️ Редактируется...", "callback_data": "done"}]]
            }),
        })
        confirm = send_message(
            TELEGRAM_ADMIN_ID,
            "✏️ *Режим редактирования*\n\n"
            f"Отправьте новый текст поста *(в ответ на это сообщение)*.\n"
            "Можно использовать Markdown-разметку.\n\n"
            "Или нажмите /cancel чтобы отменить.",
            reply_to=msg_id,
        )
        tg_api("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Отправьте новый текст"})


def handle_text_message(text, chat_id, msg):
    if text == "/start":
        send_message(chat_id,
            "🤖 *AI News Bot*\n\n"
            "Я собираю новости из мира AI по расписанию и присылаю вам на утверждение.\n\n"
            "⏱ *Расписание:* 08:00, 12:00, 16:00, 20:00\n\n"
            "Команды:\n"
            "• /topic *тема* — сделать пост на любую тему\n"
            "• /collect — проверить новости сейчас\n"
            "• /pending — показать ожидающие посты\n"
            "• /status — статус бота\n"
            "• /cancel — отменить редактирование")
        return

    if text == "/cancel":
        state = get_edit_state(chat_id)
        if state:
            clear_edit_state(chat_id)
            send_message(chat_id, "❌ Редактирование отменено")
        else:
            send_message(chat_id, "Нет активного редактирования")
        return

    if text == "/collect":
        process_news()
        return

    if text == "/pending":
        posts = get_pending_posts()
        count = len(posts)
        if count:
            text_list = "\n".join([f"• #{p['id']} — {p['title'][:60]}..." for p in posts[:10]])
            send_message(chat_id, f"📋 *Ожидают утверждения:* {count}\n{text_list}")
        else:
            send_message(chat_id, "Нет постов на утверждение")
        return

    if text == "/status":
        pending = len(get_pending_posts())
        send_message(chat_id,
            "✅ *Бот работает*\n"
            f"📋 Ожидает: {pending}\n"
            "⏱ Расписание: 08:00, 12:00, 16:00, 20:00\n"
            "🧠 Модель: OpenRouter Free")
        return

    if text.startswith("/topic"):
        topic = text[6:].strip()
        if not topic:
            send_message(chat_id,
                "Укажите тему после /topic.\n"
                "Пример: `/topic новые нейросети для видео`")
            return
        send_message(chat_id, f"🔍 Ищу новости по теме: *{topic}*...")
        process_topic_post(topic, chat_id)
        return

    state = get_edit_state(chat_id)
    if state:
        post_id = state["post_id"]
        reply_to_msg_id = state["message_id"]

        post = get_post(post_id)
        if not post:
            send_message(chat_id, "Ошибка: пост не найден")
            clear_edit_state(chat_id)
            return

        old_parts = post["content"].split("\n\n", 1)
        new_title = old_parts[0] if old_parts else "AI Новость"

        new_full_text = text.strip()

        new_image_url = post.get("image_url", "")
        tags = ["AI", "новости"]

        update_post_content(post_id, new_title, new_full_text)

        caption = f"*{new_title}*\n\n{new_full_text}\n\n #AI #новости"

        clear_edit_state(chat_id)
        send_message(chat_id,
            "✅ *Текст сохранён!*\nПост обновлён, проверьте и опубликуйте.",
            reply_to=reply_to_msg_id,
        )
        send_post_to_admin(new_image_url, caption, build_keyboard(post_id))


def process_news():
    logger.info("=== Сбор новостей ===")
    try:
        all_news = collect_news()
        logger.info(f"Собрано {len(all_news)} новостей")

        new_news = [n for n in all_news if not is_already_sent(n["url"])]
        logger.info(f"Новых: {len(new_news)}")

        if not new_news:
            logger.info("Новых новостей нет")
            return

        for i in range(0, min(len(new_news), 30), 8):
            batch = new_news[i : i + 8]
            result = generate_post(batch)

            if not result:
                logger.warning("Не удалось сгенерировать пост")
                continue

            title = result.get("title", "Новость AI")
            post_text = result.get("post", "")
            image_query = result.get("image_query", "AI technology")
            tags = result.get("tags", ["AI", "новости"])

            if not post_text:
                continue

            source_url = batch[0]["url"]
            image_url = get_image(image_query, source_url)

            save_post(source_url, title, post_text, image_url or "")

            for item in batch:
                mark_sent(item["url"])

            post_id = get_last_post_id()
            if not post_id:
                continue

            caption = build_post_caption(title, post_text, tags, source_url)
            keyboard = build_keyboard(post_id)

            send_post_to_admin(image_url, caption, keyboard)
            logger.info(f"Пост #{post_id} отправлен на утверждение")
            break

    except Exception as e:
        logger.exception(f"Ошибка при сборе новостей: {e}")
        send_message(TELEGRAM_ADMIN_ID, f"⚠️ Ошибка сбора новостей: {e}")


def process_topic_post(topic, chat_id):
    try:
        news_items = search_topic_news(topic)
        if not news_items:
            send_message(chat_id, f"Не удалось найти новости по теме «{topic}»")
            return

        result = generate_topic_post(topic, news_items)
        if not result or not result.get("post"):
            send_message(chat_id, "Не удалось сгенерировать пост")
            return

        title = result.get("title", topic)
        post_text = result.get("post", "")
        image_query = result.get("image_query", "AI technology")
        tags = result.get("tags", ["AI", topic])

        source_url = news_items[0]["url"] if news_items else ""
        image_url = get_image(image_query, source_url)

        save_post(source_url, title, post_text, image_url or "")

        for item in news_items[:5]:
            mark_sent(item["url"])

        post_id = get_last_post_id()
        if post_id:
            caption = build_post_caption(title, post_text, tags, source_url)
            send_post_to_admin(image_url, caption, build_keyboard(post_id))
            send_message(chat_id, f"✅ Пост на тему «{topic}» отправлен на утверждение!")
        else:
            send_message(chat_id, "Ошибка сохранения поста")

    except Exception as e:
        logger.exception(f"Topic post error: {e}")
        send_message(chat_id, f"⚠️ Ошибка: {e}")


@app.route("/", methods=["GET"])
def index():
    return "AI News Bot is running", 200


@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200


@app.route("/collect", methods=["GET"])
def collect():
    process_news()
    return "ok", 200


@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return "ok", 200

    threading.Thread(target=_process_update, args=(update,), daemon=True).start()
    return "ok", 200


def _process_update(update):
    try:
        if "callback_query" in update:
            handle_callback(update["callback_query"])
        elif "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")
            handle_text_message(text, chat_id, msg)
    except Exception as e:
        logger.exception(f"Webhook error: {e}")


def set_webhook():
    if BOT_MODE == "webhook" and WEBHOOK_URL:
        url = f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"
        result = tg_api("setWebhook", {"url": url})
        if result and result.get("ok"):
            logger.info(f"Webhook установлен: {url}")
        else:
            logger.warning(f"Не удалось установить webhook: {result}")
    else:
        logger.info("Webhook не настроен, установите WEBHOOK_URL")


def start_bot():
    init_db()
    logger.info("База данных инициализирована")
    set_webhook()

    for t in POST_TIMES:
        hour, minute = map(int, t.split(":"))
        now = datetime.now()
        run_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if run_time <= now:
            run_time = run_time.replace(day=run_time.day + 1)

        scheduler.add_job(
            process_news,
            "cron",
            hour=hour,
            minute=minute,
            id=f"news_{t.replace(':', '')}",
            name=f"Сбор новостей в {t}",
        )
    scheduler.start()
    schedule_str = ", ".join(POST_TIMES)
    logger.info(f"Планировщик запущен: {schedule_str}")

    for t in POST_TIMES:
        hour, minute = map(int, t.split(":"))
        logger.info(f"  • {t:>5} — следующая проверка в {hour:02d}:{minute:02d} (серверное время)")
    logger.info(f"Бот запущен на порту {PORT}")


if __name__ == "__main__":
    start_bot()
    app.run(host="0.0.0.0", port=PORT)
