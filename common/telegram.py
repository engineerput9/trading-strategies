"""Minimal Telegram sender. Needs env TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (never hardcode)."""
import os
import requests


def send(text: str) -> bool:
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat:
        print('telegram: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set; skipped')
        return False
    try:
        r = requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
                          data={'chat_id': chat, 'text': text[:4000]}, timeout=20)
        ok = r.ok and r.json().get('ok', False)
    except Exception as e:  # never echo the URL (contains the token)
        print('telegram: send failed:', type(e).__name__)
        return False
    print('telegram: sent' if ok else f'telegram: failed HTTP {r.status_code}')
    return ok
