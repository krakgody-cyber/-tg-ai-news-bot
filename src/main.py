from src.bot import start_bot, app, PORT

# Инициализация при запуске (даже через gunicorn)
start_bot()
