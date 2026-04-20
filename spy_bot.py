import logging
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
import requests
import json

# ========== ТВОИ ДАННЫЕ ==========
BOT_TOKEN = "8078793115:AAFyXHvNgUQbrQbGeMxqySo0hGrGsN9N5Cw"
YOUR_ID = 8423031459

# ========== НАСТРОЙКИ ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== БАЗА ДАННЫХ ==========
conn = sqlite3.connect('spy.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        chat_id INTEGER,
        msg_id INTEGER,
        text TEXT,
        time TEXT,
        PRIMARY KEY (chat_id, msg_id)
    )
""")
conn.commit()

def save_msg(chat_id, msg_id, text):
    cursor.execute("INSERT OR REPLACE INTO messages VALUES (?, ?, ?, ?)",
                   (chat_id, msg_id, text[:1000], datetime.now().isoformat()))
    conn.commit()

def get_msg(chat_id, msg_id):
    cursor.execute("SELECT text FROM messages WHERE chat_id=? AND msg_id=?", (chat_id, msg_id))
    row = cursor.fetchone()
    return row[0] if row else None

def del_msg(chat_id, msg_id):
    cursor.execute("DELETE FROM messages WHERE chat_id=? AND msg_id=?", (chat_id, msg_id))
    conn.commit()

# ========== FLASK ВЕБ-СЕРВЕР ==========
app = Flask(__name__)

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Send error: {e}")

@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        logger.info(f"Received: {json.dumps(update, indent=2)}")
        
        if 'business_connection' in update:
            bc = update['business_connection']
            logger.info(f"Business update: {bc}")
        
        if 'message' in update:
            msg = update['message']
            chat_id = msg['chat']['id']
            msg_id = msg['message_id']
            text = msg.get('text', '')
            if text:
                save_msg(chat_id, msg_id, text)
                logger.info(f"Saved: {text[:50]}")
        
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/')
def home():
    return "Spy Bot is running!"

if __name__ == '__main__':
    webhook_url = f"https://YOUR_USERNAME.pythonanywhere.com/webhook/{BOT_TOKEN}"
    set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setwebhook?url={webhook_url}&allowed_updates=[\"message\",\"business_connection\",\"business_message\",\"edited_business_message\",\"deleted_business_messages\"]"
    
    response = requests.get(set_url)
    logger.info(f"Webhook set response: {response.json()}")
    
    send_telegram_message(YOUR_ID, "✅ Spy Bot запущен на PythonAnywhere!")
    
    app.run(host='0.0.0.0', port=5000)