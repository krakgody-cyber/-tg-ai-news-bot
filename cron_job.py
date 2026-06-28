import os
import requests
import sys

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

if not WEBHOOK_URL:
    print("WEBHOOK_URL not set")
    sys.exit(1)

url = f"{WEBHOOK_URL}/collect"
try:
    resp = requests.get(url, timeout=30)
    print(f"Collect triggered: {resp.status_code}")
except Exception as e:
    print(f"Error: {e}")
