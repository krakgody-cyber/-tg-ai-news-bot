# 🤖 AI News Bot — Telegram бот для автоматического поиска новостей об AI

Автоматически собирает новости из мира AI каждые 6 часов, генерирует живые посты с картинками и присылает вам на утверждение.

## Как это работает

1. **Сбор** — RSS ленты (TechCrunch, The Verge, VentureBeat, Reddit, HuggingFace, GitHub, Arxiv)
2. **Генерация** — OpenRouter (DeepSeek V4 Flash Free) превращает новость в живой пост простым языком
3. **Изображение** — Pexels API подбирает картинку под тему
4. **Утверждение** — пост приходит вам в Telegram с кнопками ✅ Опубликовать / ❌ Отклонить
5. **Публикация** — после одобрения пост уходит в ваш канал

## Развёртывание на Render (бесплатно, без вашего ПК)

### Шаг 1. Создать Telegram бота
1. Напишите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot` и следуйте инструкциям
3. Сохраните **токен бота** (вида `123456:ABC-DEF...`)

### Шаг 2. Узнать свои ID
1. Напишите [@userinfobot](https://t.me/userinfobot) — получите ваш **User ID**
2. Создайте канал (если ещё нет), добавьте бота как администратора
3. ID канала: вида `@channelname` или `-1001234567890`

### Шаг 3. Получить API ключи

**OpenRouter (бесплатно):**
1. Зарегистрируйтесь на [openrouter.ai](https://openrouter.ai)
2. Создайте API ключ в настройках
3. Бот использует бесплатную модель `deepseek/deepseek-v4-flash-free`

**Pexels (опционально, для картинок):**
1. Зарегистрируйтесь на [pexels.com/api](https://www.pexels.com/api/)
2. Получите API ключ (бесплатно, 200 запросов/час)

### Шаг 4. Развернуть на Render
1. Зарегистрируйтесь на [render.com](https://render.com) (через GitHub)
2. Создайте форк этого репозитория или загрузите код
3. На Render: **New → Web Service**
4. Подключите ваш GitHub репозиторий
5. Настройки:
   - **Name:** `tg-ai-news-bot`
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn src.main:app --bind 0.0.0.0:$PORT --workers 1 --threads 4`
   - **Plan:** Free
6. Добавьте переменные окружения (Environment Variables):

| Переменная | Значение |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен от BotFather |
| `TELEGRAM_ADMIN_ID` | Ваш User ID |
| `TELEGRAM_CHANNEL_ID` | ID вашего канала (например `@channel`) |
| `OPENROUTER_API_KEY` | Ключ OpenRouter |
| `OPENROUTER_MODEL` | `deepseek/deepseek-v4-flash-free` |
| `BOT_MODE` | `webhook` |
| `WEBHOOK_URL` | `https://tg-ai-news-bot.onrender.com` |
| `PEXELS_API_KEY` | Ключ Pexels (опционально) |

7. Нажмите **Deploy**

### Шаг 5. Настроить автоматический сбор новостей
Бот запускает сбор новостей автоматически при старте и далее каждые 6 часов.

Для надёжности можно добавить **бесплатный uptime-мониторинг** (чтобы сервис не засыпал):

1. Зарегистрируйтесь на [cron-job.org](https://cron-job.org) (бесплатно)
2. Создайте задачу:
   - **URL:** `https://tg-ai-news-bot.onrender.com/ping`
   - **Schedule:** Every 5 minutes
   - **Method:** GET

Или используйте Render Cron Job (второй сервис из render.yaml).

## Команды бота

- `/start` — приветствие и справка
- `/collect` — срочно проверить новости сейчас
- `/pending` — показать сколько постов ожидает

## Требования

- Python 3.10+
- Бесплатный аккаунт на Render.com

## Стек

- Flask + Gunicorn (веб-сервер)
- APScheduler (планировщик)
- OpenRouter API (генерация текста)
- Pexels API (изображения)
- SQLite (база данных)
- Feedparser (RSS)
