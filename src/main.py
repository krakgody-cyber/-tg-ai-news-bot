from src.bot import start_bot, app, PORT

if __name__ == "__main__":
    start_bot()
    app.run(host="0.0.0.0", port=PORT)
