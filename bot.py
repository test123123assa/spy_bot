import sqlite3
import requests
from flask import Flask, request, send_file
from datetime import datetime
from contextlib import contextmanager
import json
import io
import re
import os

# ===== КОНФИГУРАЦИЯ =====
TOKEN = os.getenv('BOT_TOKEN', '8657672564:AAGDoBIDGE46i7CsWqPXlfRo9IDon4g5usY')
ADMIN_ID = int(os.getenv('ADMIN_ID', '8423031459'))
whitelist_users = set()
whitelist_notified = set()
DB_PATH = os.getenv('DATABASE_PATH', '/data/spy.db')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
BOT_USERNAME = "@v373ments_bot"
API_URL = f"https://api.telegram.org/bot{TOKEN}/"
app = Flask(__name__)

# ===== ДЕФОЛТНЫЕ НАСТРОЙКИ ДИЗАЙНА =====
DEFAULT_SETTINGS = {
    # Изображения
    'start_image': "https://i.ibb.co/vWf7KTL/photo-2026-05-05-20-00-18.jpg",
    'welcome_image': "https://i.ibb.co/m5kx1c7C/photo-2026-05-05-19-08-58.jpg",
    'settings_image': "https://i.ibb.co/7tKL334J/4e297130-9e22-41e4-af43-57c6e58882a1.png",
    'whitelist_on_image': "AgACAgIAAxkBAAIThmn_tUEFbWvMa2FBUhtYJGF7PldkAAL_GWsbEZr4S4dg8OXCgx73AQADAgADeAADOwQ",
    'whitelist_off_image': "AgACAgIAAxkBAAITh2n_tUSm-MLAEBDPccto9c8lOU8dAAMaaxsRmvhL5KQx_Mh9MI0BAAMCAAN5AAM7BA",

    # Основные тексты
    'start_text': '<tg-emoji emoji-id="6028435952299413210">🤖</tg-emoji> Подключите бота к аккаунту в профиле, чтобы он мог помочь вам в переписке в нужный момент.',
    'welcome_text': '<tg-emoji emoji-id="6037249452824072506">🔥</tg-emoji> <b>Бот успешно подключен к вам!</b>\n\n<tg-emoji emoji-id="5904258298764334001">🔥</tg-emoji> Настроить уведомления <b>Вы</b> можете через <b>/settings</b>.',
    'disconnect_te  xt': '<tg-emoji emoji-id="6037496202990194718">🔥</tg-emoji> <b>Бот был отключён.</b>\n\nЕсли это произошло случайно, вы можете подключить бота повторно. Будьте осторожны и остерегайтесь других ботов, которые могут оказаться предназначены для мошенничества с вашим аккаунтом.',
    'help_text': '<tg-emoji emoji-id="5962952497197748583">🔥</tg-emoji> <b>Помощь по командам</b>\n━━━━━━━━━━━━━━━\n/start — Главное меню\n/settings — Настройки уведомлений\n/stats — Ваша статистика\n/chat @username или ID — Экспорт чата\n\n<tg-emoji emoji-id="5776078972659962594">🔥</tg-emoji> <b>Помощь по подключению</b>\n━━━━━━━━━━━━━━━\n<b>Как подключить:</b>\n1. Откройте <b>Ваш профиль</b> в Telegram\n2. Перейдите в <b>Автоматизация чатов</b>\n3. В поисковую строку напишите: <b>@v373ments_bot</b>\n4. Выберите <b>@v373ments_bot</b>\n5. <b>Разрешите</b> доступ ко всем чатам и сообщениям.',
    'whitelist_on_text': "🔒 <b>Включен белый список/технические работы.</b>\n\nСкоро вернёмся!",
    'whitelist_off_text': "✅ <b>Белый список/технические работы отключены.</b>\n\nБот снова работает, извиняемся за ожидание!",

    # Шаблоны уведомлений
    'deleted_template': "🗑 <b>{sender}</b> удалил сообщение:\n🕐 {time}",
    'edited_template': "✏️ <b>{sender}</b> изменил сообщение:\n🕐 {time}\n\n<blockquote>{old_content}</blockquote>\n\nна:\n\n<blockquote>{new_content}</blockquote>",
    'edited_fast_template': "✏️ <b>Редактирование</b>\n━━━━━━━━━━━━━━━\n💬 <b>Чат:</b> {chat}\n👤 <b>От:</b> {sender}\n🕐 {time}\n━━━━━━━━━━━━━━━\n❌ <b>Было:</b>\n<blockquote><i>(сообщение отредактировано слишком быстро)</i></blockquote>\n\n✅ <b>Стало:</b>\n<blockquote>{content}</blockquote>",

    # Настройки форматирования
    'time_format': "%d.%m.%Y %H:%M",
    'bot_name': "@v373ments_bot",
    'instruction_link': "https://t.me/SU1C1D3X/12",

    # Иконки медиа
    'photo_icon': "📷",
    'video_icon': "🎥",
    'voice_icon': "🎤",
    'audio_icon': "🎵",
    'document_icon': "📎",
    'animation_icon': "🎞",
    'video_note_icon': "⭕",
    'sticker_icon': "🎭",
    'contact_icon': "📞",
    'location_icon': "📍",
    'poll_icon': "📊",
    'unknown_icon': "❓",

    # Кнопки интерфейса
    'btn_copy_username': "📋 Скопировать {bot_name}",
    'btn_instruction': "📖 Подробная инструкция",
    'btn_back': "‹ Назад",
    'btn_settings_edits': "Уведомления об изменении",
    'btn_settings_deletes': "Уведомления об удалении",
    'btn_settings_blur': "Блюр удаленных медиа",
    'btn_turn_on': "✅ Включить",
    'btn_turn_off': "❌ Выключить",

    # Тексты настроек
    'settings_title': '<tg-emoji emoji-id="6032742198179532882">⚙️</tg-emoji> Настройки',
    'settings_description': "Выберите параметр для изменения:",
    'setting_edits_title': '<tg-emoji emoji-id="6039779802741739617">✏️</tg-emoji> <b>Уведомления об изменении</b>',
    'setting_edits_desc': "<blockquote>Если ваш собеседник изменит любое сообщение, бот мгновенно пришлёт вам его старую и новую версию.</blockquote>",
    'setting_deletes_title': '<tg-emoji emoji-id="6039522349517115015">🗑️</tg-emoji> <b>Уведомления об удалении</b>',
    'setting_deletes_desc': "<blockquote>Если ваш собеседник удалит любое сообщение, бот мгновенно сохранит его вам.</blockquote>",
    'setting_blur_title': '<tg-emoji emoji-id="6039451237743595514">🎭</tg-emoji> <b>Блюр удаленных медиа</b>',
    'setting_blur_desc': "<blockquote>Все удаленные медиа/фотографии будут приходить с эффектом блюра. Это будет Вам полезно, если вы находитесь в общественном месте.</blockquote>",

    # Сообщения об изменении статуса
    'msg_enabled': "✅ Включено",
    'msg_disabled': "❌ Выключено",
    'msg_saved': "💾 Сохранено!",
    'msg_cancelled': "❌ Отменено",
    'msg_reset_confirm': "🔄 Все настройки дизайна будут сброшены к стандартным. Вы уверены?",
    'msg_reset_success': "✅ Настройки сброшены к стандартным значениям",

    # Кнопки в уведомлениях
    'btn_skip_delete': "🗑 Пропустить",
    'btn_skip_edit': "🗑 Пропустить",

    # Заголовки разделов дизайна
    'design_main_title': "🎨 Дизайн-панель бота",
    'design_main_desc': "Выберите раздел для настройки:",
    'design_images_title': "📷 Настройка изображений",
    'design_images_desc': "Выберите изображение для изменения:\n\n💡 Отправьте фото или ссылку на изображение",
    'design_texts_title': "📝 Настройка текстов",
    'design_texts_desc': "Выберите текст для изменения:\n\n💡 Можно использовать HTML разметку и плейсхолдеры",
    'design_templates_title': "🎨 Настройка шаблонов",
    'design_templates_desc': "Выберите шаблон для изменения:\n\n💡 Доступные плейсхолдеры:\n<code>{sender}</code> — отправитель\n<code>{time}</code> — время\n<code>{content}</code>, <code>{old_content}</code>, <code>{new_content}</code> — содержимое\n<code>{chat}</code> — чат",
    'design_config_title': "⚙️ Настройка конфигурации",
    'design_config_desc': "Выберите параметр для изменения:",
    'design_icons_title': "🔧 Настройка иконок",
    'design_icons_desc': "Выберите иконку для изменения:\n\n💡 Используйте эмодзи или текст",

    # Названия элементов дизайна
    'design_btn_images': "📷 Изображения",
    'design_btn_texts': "📝 Тексты",
    'design_btn_templates': "🎨 Шаблоны",
    'design_btn_config': "⚙️ Настройки",
    'design_btn_icons': "🔧 Иконки",
    'design_btn_formatting': "🎭 Форматирование",
    'design_btn_reset': "🔄 Сброс",

    # Эмодзи и стили
    'emoji_success': "✅",
    'emoji_danger': "❌",
    'emoji_warning': "⚠️",
    'emoji_info': "ℹ️",

    # Индивидуальные цвета кнопок (success/danger/primary/secondary или пусто)
    'btn_edits_style': "",
    'btn_deletes_style': "",
    'btn_blur_style': "",
    'btn_on_style': "",
    'btn_off_style': "",
    'btn_copy_style': "",
    'btn_instruction_style': "",
    'btn_back_style': "",

    # Стили инлайн кнопок в /settings (success=зелёный, danger=красный)
    'style_edits_on': "success",
    'style_edits_off': "danger",
    'style_deletes_on': "success",
    'style_deletes_off': "danger",
    'style_blur_on': "success",
    'style_blur_off': "danger",

    # Управление функциями бота
    'cmd_start_enabled': "1",
    'cmd_settings_enabled': "1",
    'cmd_help_enabled': "1",
    'cmd_stats_enabled': "1",
    'cmd_plus_enabled': "1",
    'cmd_chat_enabled': "1"
}

# ===== БАЗА ДАННЫХ =====
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()

# ===== PLUS ПОДПИСКА =====
def check_plus_subscription(user_id):
    """Проверяет наличие активной подписки Plus"""
    with get_db() as conn:
        row = conn.execute("""
            SELECT expires_at FROM plus_subscriptions
            WHERE user_id=? AND expires_at > ?
        """, (user_id, datetime.now().isoformat())).fetchone()
        return row is not None

def get_plus_info(user_id):
    """Получает информацию о подписке Plus"""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM plus_subscriptions WHERE user_id=?
        """, (user_id,)).fetchone()
        if row:
            return dict(row)
        return None

def add_plus_subscription(user_id, days):
    """Добавляет подписку Plus на N дней"""
    from datetime import timedelta
    expires_at = datetime.now() + timedelta(days=days)

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO plus_subscriptions
            (user_id, activated_at, expires_at)
            VALUES (?, ?, ?)
        """, (user_id, datetime.now().isoformat(), expires_at.isoformat()))
        conn.commit()

def remove_plus_subscription(user_id):
    """Удаляет подписку Plus"""
    with get_db() as conn:
        conn.execute("DELETE FROM plus_subscriptions WHERE user_id=?", (user_id,))
        conn.commit()

def get_whitelist_mode():
    with get_db() as conn:
        row = conn.execute("SELECT value FROM bot_settings WHERE key='whitelist_mode'").fetchone()
        return row["value"] == "1" if row else False

def set_whitelist_mode(val):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('whitelist_mode', ?)",
            ("1" if val else "0",))
        conn.commit()

def load_whitelist():
    global whitelist_users
    try:
        with get_db() as conn:
            rows = conn.execute("SELECT user_id FROM whitelist").fetchall()
            whitelist_users = set(r["user_id"] for r in rows)
    except:
        whitelist_users = set()

whitelist_notified = set()
load_whitelist()

def init_db():
    with get_db() as conn:
        # Пользователи бота
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            first_name TEXT,
            joined_at  TEXT,
            is_muted   INTEGER DEFAULT 0,
            is_banned  INTEGER DEFAULT 0
        )''')

        # Подключения бизнес-аккаунтов
        conn.execute('''CREATE TABLE IF NOT EXISTS connections (
            connection_id TEXT PRIMARY KEY,
            user_id       INTEGER
        )''')

        # Все входящие сообщения
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id  INTEGER,
            owner_id    INTEGER,
            sender_id   INTEGER,
            sender_name TEXT,
            chat_id     INTEGER,
            chat_name   TEXT,
            content     TEXT,
            media_type  TEXT,
            file_id     TEXT,
            timestamp   TEXT,
            deleted     INTEGER DEFAULT 0,
            edited      INTEGER DEFAULT 0,
            edit_count  INTEGER DEFAULT 0,
            UNIQUE(message_id, owner_id, chat_id)
        )''')

        # История редактирований
        conn.execute('''CREATE TABLE IF NOT EXISTS edits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id  INTEGER,
            owner_id    INTEGER,
            chat_id     INTEGER,
            sender_name TEXT,
            chat_name   TEXT,
            old_content TEXT,
            new_content TEXT,
            media_type  TEXT,
            file_id     TEXT,
            edited_at   TEXT
        )''')

        # Настройки каждого пользователя
        conn.execute('''CREATE TABLE IF NOT EXISTS settings (
            user_id       INTEGER PRIMARY KEY,
            notify_edits  INTEGER DEFAULT 1,
            notify_deletes INTEGER DEFAULT 1,
            blur_media    INTEGER DEFAULT 0
        )''')

        # Белый список
        conn.execute('''CREATE TABLE IF NOT EXISTS whitelist (
            user_id INTEGER PRIMARY KEY
        )''')

        # Настройки бота
        conn.execute('''CREATE TABLE IF NOT EXISTS bot_settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )''')

        # Состояния админа
        conn.execute('''CREATE TABLE IF NOT EXISTS admin_states_db (
            user_id INTEGER PRIMARY KEY,
            action  TEXT,
            data    TEXT
        )''')

        # Кастомизация бота
        conn.execute('''CREATE TABLE IF NOT EXISTS bot_customization (
            setting_key   TEXT PRIMARY KEY,
            setting_value TEXT,
            setting_type  TEXT,
            description   TEXT,
            created_at    TEXT,
            updated_at    TEXT
        )''')

        # Plus подписки
        conn.execute('''CREATE TABLE IF NOT EXISTS plus_subscriptions (
            user_id      INTEGER PRIMARY KEY,
            activated_at TEXT,
            expires_at   TEXT
        )''')

        conn.commit()

        # Инициализируем дефолтные настройки дизайна
        init_default_design()

def init_default_design():
    """Инициализация дефолтных настроек дизайна"""
    with get_db() as conn:
        for key, value in DEFAULT_SETTINGS.items():
            existing = conn.execute("SELECT setting_key FROM bot_customization WHERE setting_key=?", (key,)).fetchone()
            if not existing:
                setting_type = get_setting_type(key)
                description = get_setting_description(key)
                conn.execute("""INSERT INTO bot_customization
                    (setting_key, setting_value, setting_type, description, created_at, updated_at)
                    VALUES (?,?,?,?,?,?)""",
                    (key, value, setting_type, description, datetime.now().isoformat(), datetime.now().isoformat()))

        # Миграция: заменяем {sender_name} на {sender} в существующих шаблонах
        templates = conn.execute("""
            SELECT setting_key, setting_value FROM bot_customization
            WHERE setting_type='template' AND setting_value LIKE '%{sender_name}%'
        """).fetchall()

        for row in templates:
            old_value = row["setting_value"]
            new_value = old_value.replace("{sender_name}", "{sender}")
            conn.execute("""UPDATE bot_customization
                SET setting_value=?, updated_at=?
                WHERE setting_key=?""",
                (new_value, datetime.now().isoformat(), row["setting_key"]))

        conn.commit()

def get_setting_type(key):
    """Определяет тип настройки по ключу"""
    if 'image' in key:
        return 'image'
    elif key in ['time_format', 'bot_name', 'instruction_link']:
        return 'config'
    elif 'template' in key:
        return 'template'
    elif 'icon' in key:
        return 'icon'
    else:
        return 'text'

def get_setting_description(key):
    """Возвращает описание настройки"""
    descriptions = {
        # Изображения
        'start_image': 'Изображение для команды /start',
        'welcome_image': 'Изображение при подключении бота',
        'settings_image': 'Изображение в настройках',
        'whitelist_on_image': 'Изображение при включении белого списка',
        'whitelist_off_image': 'Изображение при выключении белого списка',

        # Основные тексты
        'start_text': 'Текст приветствия /start',
        'welcome_text': 'Текст при подключении',
        'help_text': 'Текст помощи /help',
        'whitelist_on_text': 'Текст при включении белого списка',
        'whitelist_off_text': 'Текст при выключении белого списка',

        # Шаблоны
        'deleted_template': 'Шаблон удалённого сообщения',
        'edited_template': 'Шаблон редактированного сообщения',
        'edited_fast_template': 'Шаблон быстрого редактирования',

        # Конфигурация
        'time_format': 'Формат времени (%d.%m.%Y %H:%M)',
        'bot_name': 'Имя бота в сообщениях',
        'instruction_link': 'Ссылка на инструкцию',

        # Иконки медиа
        'photo_icon': 'Иконка фото',
        'video_icon': 'Иконка видео',
        'voice_icon': 'Иконка голосового',
        'audio_icon': 'Иконка аудио',
        'document_icon': 'Иконка документа',
        'animation_icon': 'Иконка GIF',
        'video_note_icon': 'Иконка видео-кружка',
        'sticker_icon': 'Иконка стикера',
        'contact_icon': 'Иконка контакта',
        'location_icon': 'Иконка геолокации',
        'poll_icon': 'Иконка опроса',
        'unknown_icon': 'Иконка неизвестного типа',

        # Кнопки интерфейса
        'btn_copy_username': 'Кнопка копирования username',
        'btn_instruction': 'Кнопка инструкции',
        'btn_back': 'Кнопка "Назад"',
        'btn_settings_edits': 'Название кнопки редактирования',
        'btn_settings_deletes': 'Название кнопки удаления',
        'btn_settings_blur': 'Название кнопки блюра',
        'btn_turn_on': 'Кнопка включения',
        'btn_turn_off': 'Кнопка выключения',

        # Заголовки и описания
        'settings_title': 'Заголовок страницы настроек',
        'settings_description': 'Описание страницы настроек',
        'setting_edits_title': 'Заголовок настройки редактирования',
        'setting_edits_desc': 'Описание настройки редактирования',
        'setting_deletes_title': 'Заголовок настройки удаления',
        'setting_deletes_desc': 'Описание настройки удаления',
        'setting_blur_title': 'Заголовок настройки блюра',
        'setting_blur_desc': 'Описание настройки блюра',

        # Сообщения
        'msg_enabled': 'Сообщение "Включено"',
        'msg_disabled': 'Сообщение "Выключено"',
        'msg_saved': 'Сообщение "Сохранено"',
        'msg_cancelled': 'Сообщение "Отменено"',
        'msg_reset_confirm': 'Подтверждение сброса настроек',
        'msg_reset_success': 'Сообщение об успешном сбросе',

        # Заголовки дизайна
        'design_main_title': 'Заголовок главной дизайн-панели',
        'design_images_title': 'Заголовок раздела изображений',
        'design_texts_title': 'Заголовок раздела текстов',
        'design_templates_title': 'Заголовок раздела шаблонов',
        'design_config_title': 'Заголовок раздела настроек',
        'design_icons_title': 'Заголовок раздела иконок',

        # Названия кнопок дизайна
        'design_btn_images': 'Название кнопки "Изображения"',
        'design_btn_texts': 'Название кнопки "Тексты"',
        'design_btn_templates': 'Название кнопки "Шаблоны"',
        'design_btn_config': 'Название кнопки "Настройки"',
        'design_btn_icons': 'Название кнопки "Иконки"',
        'design_btn_formatting': 'Название кнопки "Форматирование"',
        'design_btn_reset': 'Название кнопки "Сброс"',

        # Эмодзи
        'emoji_success': 'Эмодзи успеха',
        'emoji_danger': 'Эмодзи ошибки',
        'emoji_warning': 'Эмодзи предупреждения',
        'emoji_info': 'Эмодзи информации',

        # Кнопки в уведомлениях
        'btn_skip_delete': 'Кнопка "Пропустить" под удалённым сообщением',
        'btn_skip_edit': 'Кнопка "Пропустить" под редактированным сообщением',

        # Индивидуальные цвета кнопок
        'btn_edits_style': 'Цвет кнопки редактирования',
        'btn_deletes_style': 'Цвет кнопки удаления',
        'btn_blur_style': 'Цвет кнопки блюра',
        'btn_on_style': 'Цвет кнопки включения',
        'btn_off_style': 'Цвет кнопки выключения',
        'btn_copy_style': 'Цвет кнопки копирования',
        'btn_instruction_style': 'Цвет кнопки инструкции',
        'btn_back_style': 'Цвет кнопки назад',

        # Управление командами
        'cmd_start_enabled': 'Включить команду /start',
        'cmd_settings_enabled': 'Включить команду /settings',
        'cmd_help_enabled': 'Включить команду /help',
        'cmd_stats_enabled': 'Включить команду /stats',
        'cmd_plus_enabled': 'Включить команду /plus',
        'cmd_chat_enabled': 'Включить команду /chat'
    }
    return descriptions.get(key, f'Настройка {key}')

# ===== ФУНКЦИИ РАБОТЫ С КАСТОМИЗАЦИЕЙ =====
def get_custom_setting(key, default=None):
    """Получает кастомную настройку из БД"""
    with get_db() as conn:
        row = conn.execute("SELECT setting_value FROM bot_customization WHERE setting_key=?", (key,)).fetchone()
        if row:
            return row["setting_value"]
        return default or DEFAULT_SETTINGS.get(key, "")

def set_custom_setting(key, value, setting_type=None):
    """Сохраняет кастомную настройку в БД"""
    with get_db() as conn:
        if not setting_type:
            setting_type = get_setting_type(key)
        description = get_setting_description(key)

        conn.execute("""INSERT OR REPLACE INTO bot_customization
            (setting_key, setting_value, setting_type, description, updated_at)
            VALUES (?,?,?,?,?)""",
            (key, value, setting_type, description, datetime.now().isoformat()))
        conn.commit()

def delete_custom_setting(key):
    """Удаляет кастомную настройку (возврат к дефолтной)"""
    with get_db() as conn:
        conn.execute("DELETE FROM bot_customization WHERE setting_key=?", (key,))
        conn.commit()

def format_template(template, **kwargs):
    """Форматирует шаблон с подстановкой переменных"""
    try:
        # Безопасная замена плейсхолдеров
        for key, value in kwargs.items():
            if value is None:
                value = ""
            template = template.replace(f"{{{key}}}", str(value))
        return template
    except Exception as e:
        print(f"[format_template] Error: {e}")
        return template

init_db()

# ===== НАСТРОЙКИ =====
def get_settings(user_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM settings WHERE user_id=?", (user_id,)).fetchone()
        if row:
            return dict(row)
        conn.execute("INSERT INTO settings (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return {"user_id": user_id, "notify_edits": 1, "notify_deletes": 1, "blur_media": 0}

def set_setting(user_id, key, value):
    if key not in {"notify_edits", "notify_deletes", "blur_media"}:
        return
    with get_db() as conn:
        conn.execute(f"UPDATE settings SET {key}=? WHERE user_id=?", (value, user_id))
        conn.commit()

# ===== ВСПОМОГАТЕЛЬНЫЕ =====
def get_owner(connection_id):
    with get_db() as conn:
        row = conn.execute("SELECT user_id FROM connections WHERE connection_id=?", (connection_id,)).fetchone()
        return row["user_id"] if row else None

def is_muted(user_id):
    with get_db() as conn:
        row = conn.execute("SELECT is_muted FROM users WHERE user_id=?", (user_id,)).fetchone()
        return bool(row["is_muted"]) if row else False

def is_banned(user_id):
    with get_db() as conn:
        row = conn.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
        return bool(row["is_banned"]) if row else False

def register_user(user_id, username, first_name):
    with get_db() as conn:
        # Проверяем существует ли пользователь
        existing = conn.execute("SELECT user_id, username, first_name FROM users WHERE user_id=?", (user_id,)).fetchone()

        if existing:
            # Пользователь уже есть - обновляем username и first_name если они изменились
            old_username = existing["username"]
            old_first_name = existing["first_name"]

            if old_username != username or old_first_name != first_name:
                conn.execute("""
                    UPDATE users
                    SET username=?, first_name=?
                    WHERE user_id=?
                """, (username, first_name, user_id))
                conn.commit()
                print(f"[UPDATE] User {user_id}: username '{old_username}' -> '{username}', name '{old_first_name}' -> '{first_name}'")
        else:
            # Новый пользователь - добавляем
            conn.execute("""
                INSERT INTO users (user_id, username, first_name, joined_at)
                VALUES (?,?,?,?)
            """, (user_id, username, first_name, datetime.now().isoformat()))
            conn.commit()
            print(f"[NEW USER] User {user_id} registered: {first_name} (@{username})")

def parse_media(msg):
    """Возвращает (media_type, file_id, content) с кастомными иконками"""
    if "text" in msg:
        return None, None, msg["text"]

    cap = msg.get("caption") or ""

    if "photo" in msg:
        photos = msg["photo"]
        if isinstance(photos, list) and photos:
            icon = get_custom_setting('photo_icon', '📷')
            return "photo", photos[-1]["file_id"], cap or f"{icon} Фото"

    if "video" in msg:
        icon = get_custom_setting('video_icon', '🎥')
        return "video", msg["video"]["file_id"], cap or f"{icon} Видео"

    if "voice" in msg:
        icon = get_custom_setting('voice_icon', '🎤')
        return "voice", msg["voice"]["file_id"], f"{icon} Голосовое"

    if "video_note" in msg:
        icon = get_custom_setting('video_note_icon', '⭕')
        return "video_note", msg["video_note"]["file_id"], f"{icon} Кружок"

    if "animation" in msg:
        icon = get_custom_setting('animation_icon', '🎞')
        return "animation", msg["animation"]["file_id"], cap or f"{icon} GIF"

    if "audio" in msg:
        icon = get_custom_setting('audio_icon', '🎵')
        return "audio", msg["audio"]["file_id"], cap or f"{icon} Аудио"

    if "document" in msg:
        icon = get_custom_setting('document_icon', '📎')
        return "document", msg["document"]["file_id"], cap or f"{icon} Документ"

    if "sticker" in msg:
        s = msg["sticker"]
        icon = get_custom_setting('sticker_icon', '🎭')
        return "sticker", s["file_id"], f"{icon} Стикер {s.get('emoji','')}"

    if "contact" in msg:
        c = msg["contact"]
        icon = get_custom_setting('contact_icon', '📞')
        return None, None, f"{icon} Контакт: {c.get('first_name','')} {c.get('phone_number','')}"

    if "location" in msg:
        loc = msg["location"]
        icon = get_custom_setting('location_icon', '📍')
        return None, None, f"{icon} Локация: {loc['latitude']}, {loc['longitude']}"

    if "poll" in msg:
        icon = get_custom_setting('poll_icon', '📊')
        return None, None, f"{icon} Опрос: {msg['poll'].get('question','')}"

    icon = get_custom_setting('unknown_icon', '❓')
    return None, None, f"{icon} Неизвестный тип"

def get_sender(msg):
    u = msg.get("from") or {}
    name = ((u.get("first_name") or "") + " " + (u.get("last_name") or "")).strip()
    return name or "Неизвестный", u.get("id", 0)

def get_chat_name(msg):
    chat = msg.get("chat") or {}
    name = ((chat.get("first_name") or "") + " " + (chat.get("last_name") or "")).strip()
    return name or chat.get("title") or chat.get("username") or "Неизвестный чат"

def format_time():
    """Форматирует время согласно настройкам"""
    time_format = get_custom_setting('time_format', '%d.%m.%Y %H:%M')
    return datetime.now().strftime(time_format)

def is_command_enabled(command):
    """Проверяет, включена ли команда"""
    cmd_map = {
        "/start": "cmd_start_enabled",
        "/settings": "cmd_settings_enabled",
        "/help": "cmd_help_enabled",
        "/stats": "cmd_stats_enabled",
        "/plus": "cmd_plus_enabled",
        "/chat": "cmd_chat_enabled"
    }
    setting_key = cmd_map.get(command)
    if setting_key:
        return get_custom_setting(setting_key, "1") == "1"
    return True

# ===== TELEGRAM API =====
def api(method, **kwargs):
    import time
    for attempt in range(3):
        try:
            r = requests.post(f"{API_URL}{method}", json=kwargs, timeout=15).json()
            if not r.get("ok"):
                print(f"[API] {method} → {r.get('description')}")
            return r
        except Exception as e:
            print(f"[API] {method} attempt {attempt+1} exception: {e}")
            if attempt < 2:
                time.sleep(3)
    return {}

def send_msg(chat_id, text, markup=None):
    p = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if markup: p["reply_markup"] = markup
    return api("sendMessage", **p)

def send_photo_msg(chat_id, photo, caption=None, markup=None, spoiler=False):
    p = {"chat_id": chat_id, "photo": photo, "parse_mode": "HTML"}
    if caption: p["caption"] = caption
    if markup: p["reply_markup"] = markup
    if spoiler: p["has_spoiler"] = True
    return api("sendPhoto", **p)

def send_video_msg(chat_id, video, caption=None, spoiler=False, markup=None):
    p = {"chat_id": chat_id, "video": video, "parse_mode": "HTML"}
    if caption: p["caption"] = caption
    if spoiler: p["has_spoiler"] = True
    if markup: p["reply_markup"] = markup
    return api("sendVideo", **p)

def send_voice_msg(chat_id, voice, caption=None, markup=None):
    p = {"chat_id": chat_id, "voice": voice, "parse_mode": "HTML"}
    if caption: p["caption"] = caption
    if markup: p["reply_markup"] = markup
    return api("sendVoice", **p)

def send_audio_msg(chat_id, audio, caption=None, markup=None):
    p = {"chat_id": chat_id, "audio": audio, "parse_mode": "HTML"}
    if caption: p["caption"] = caption
    if markup: p["reply_markup"] = markup
    return api("sendAudio", **p)

def send_doc_msg(chat_id, doc, caption=None, markup=None):
    p = {"chat_id": chat_id, "document": doc, "parse_mode": "HTML"}
    if caption: p["caption"] = caption
    if markup: p["reply_markup"] = markup
    return api("sendDocument", **p)

def send_anim_msg(chat_id, anim, caption=None, spoiler=False, markup=None):
    p = {"chat_id": chat_id, "animation": anim, "parse_mode": "HTML"}
    if caption: p["caption"] = caption
    if spoiler: p["has_spoiler"] = True
    if markup: p["reply_markup"] = markup
    return api("sendAnimation", **p)

def send_vnote_msg(chat_id, vnote):
    return api("sendVideoNote", chat_id=chat_id, video_note=vnote)

def send_sticker_msg(chat_id, sticker):
    return api("sendSticker", chat_id=chat_id, sticker=sticker)

def edit_cap(chat_id, msg_id, caption, markup=None):
    p = {"chat_id": chat_id, "message_id": msg_id, "caption": caption, "parse_mode": "HTML"}
    if markup: p["reply_markup"] = markup
    return api("editMessageCaption", **p)

def edit_txt(chat_id, msg_id, text, markup=None):
    p = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    if markup: p["reply_markup"] = markup
    return api("editMessageText", **p)

def answer_cb(cb_id, text=None, alert=False):
    p = {"callback_query_id": cb_id}
    if text: p["text"] = text
    if alert: p["show_alert"] = True
    return api("answerCallbackQuery", **p)

# ===== ОТПРАВКА УДАЛЁННОГО МЕДИА =====
def notify_deleted(owner_id, row):
    s = get_settings(owner_id)
    spoiler = s["blur_media"] == 1
    ts = format_time()
    sender_name = row.get("sender_name", "?") or "?"
    sender_id = row.get("sender_id", 0) or 0
    chat = row.get("chat_name", "Неизвестный чат") or "Неизвестный чат"

    # Создаём кликабельную ссылку на профиль по ID (формат HTML)
    if sender_id and sender_id > 0:
        sender_link = f'<a href="tg://user?id={sender_id}">{sender_name}</a>'
    else:
        sender_link = sender_name

    # Используем кастомный шаблон с кликабельной ссылкой
    template = get_custom_setting('deleted_template')
    header = format_template(template, sender=sender_link, time=ts, chat=chat)

    content = row["content"] or ""
    media_type = row["media_type"]
    file_id = row["file_id"]

    # Определяем иконки из настроек
    plain_labels = {
        f"{get_custom_setting('photo_icon', '📷')} Фото",
        f"{get_custom_setting('video_icon', '🎥')} Видео",
        f"{get_custom_setting('audio_icon', '🎵')} Аудио",
        f"{get_custom_setting('document_icon', '📎')} Документ",
        f"{get_custom_setting('voice_icon', '🎤')} Голосовое",
        f"{get_custom_setting('video_note_icon', '⭕')} Кружок",
        f"{get_custom_setting('animation_icon', '🎞')} GIF",
        f"{get_custom_setting('unknown_icon', '❓')} Неизвестный тип"
    }

    sticker_prefix = f"{get_custom_setting('sticker_icon', '🎭')} Стикер"
    has_text = content and content not in plain_labels and not content.startswith(sticker_prefix)

    # Создаем кнопку "Пропустить"
    skip_button = {
        "inline_keyboard": [[
            {"text": get_custom_setting('btn_skip_delete', '🗑 Пропустить'), "callback_data": "skip_notification"}
        ]]
    }

    # ОТПРАВЛЯЕМ МЕДИА (фото, видео, гс, файлы, гифки, кружки, стикеры)
    if media_type and file_id:
        caption = header
        if has_text:
            caption += f"\n\n<blockquote>{content}</blockquote>"

        if media_type == "photo":
            send_photo_msg(owner_id, file_id, caption=caption, markup=skip_button, spoiler=spoiler)
        elif media_type == "video":
            send_video_msg(owner_id, file_id, caption=caption, markup=skip_button, spoiler=spoiler)
        elif media_type == "voice":
            send_voice_msg(owner_id, file_id, caption=caption, markup=skip_button)
        elif media_type == "audio":
            send_audio_msg(owner_id, file_id, caption=caption, markup=skip_button)
        elif media_type == "document":
            send_doc_msg(owner_id, file_id, caption=caption, markup=skip_button)
        elif media_type == "animation":
            send_anim_msg(owner_id, file_id, caption=caption, markup=skip_button, spoiler=spoiler)
        elif media_type == "video_note":
            send_msg(owner_id, header, markup=skip_button)
            send_vnote_msg(owner_id, file_id)
        elif media_type == "sticker":
            send_msg(owner_id, header, markup=skip_button)
            send_sticker_msg(owner_id, file_id)
    else:
        # Текстовые сообщения
        text = header
        if content:
            text += f"\n\n<blockquote>{content}</blockquote>"
        send_msg(owner_id, text, markup=skip_button)

def notify_edited(owner_id, row, old_content, new_content, edit_num):
    ts = format_time()
    sender_name = row.get("sender_name", "?") or "?"
    sender_id = row.get("sender_id", 0) or 0
    chat = row.get("chat_name", "Неизвестный чат") or "Неизвестный чат"

    # Создаём кликабельную ссылку на профиль по ID (работает только с username)
    if sender_id and sender_id > 0:
        sender_link = f'<a href="tg://user?id={sender_id}">{sender_name}</a>'
    else:
        sender_link = sender_name

    # Используем кастомный шаблон с кликабельной ссылкой
    template = get_custom_setting('edited_template')
    text = format_template(template,
        sender=sender_link,
        time=ts,
        chat=chat,
        old_content=old_content if old_content else "📎 Медиафайл",
        new_content=new_content if new_content else "📎 Медиафайл"
    )

    # Создаем кнопку "Пропустить"
    skip_button = {
        "inline_keyboard": [[
            {"text": get_custom_setting('btn_skip_edit', '🗑 Пропустить'), "callback_data": "skip_notification"}
        ]]
    }

    send_msg(owner_id, text, markup=skip_button)

# ===== КЛАВИАТУРЫ С КАСТОМИЗАЦИЕЙ =====
def kb_start():
    bot_name = get_custom_setting('bot_name')
    instruction_link = get_custom_setting('instruction_link')
    btn_copy_text = get_custom_setting('btn_copy_username').replace('{bot_name}', bot_name)
    btn_instruction_text = get_custom_setting('btn_instruction')

    # Получаем индивидуальные стили
    copy_style = get_custom_setting('btn_copy_style', '')
    instruction_style = get_custom_setting('btn_instruction_style', '')

    buttons = []

    # Кнопка копирования с copy_text (автокопирование при нажатии)
    copy_btn = {
        "text": btn_copy_text,
        "copy_text": {"text": "@v373ments_bot"}
    }
    if copy_style:
        copy_btn["style"] = copy_style
    buttons.append([copy_btn])

    # Кнопка инструкции
    instruction_btn = {"text": btn_instruction_text, "url": instruction_link}
    if instruction_style:
        instruction_btn["style"] = instruction_style
    buttons.append([instruction_btn])

    return {"inline_keyboard": buttons}

def kb_settings(user_id):
    s = get_settings(user_id)

    return {"inline_keyboard": [
        [{"text": "Уведомления об изменении", "callback_data": "s_edits"}],
        [{"text": "Уведомления об удалении", "callback_data": "s_deletes"}],
        [{"text": "Блюр удаленных медиа", "callback_data": "s_blur"}]
    ]}

def kb_detail(stype, val):
    """ОДНА переключаемая кнопка вместо двух"""
    btn_back = get_custom_setting('btn_back')

    # Одна кнопка которая переключается
    if val:
        # Если включено - показываем красную кнопку "Выключить"
        btn = {
            "text": "Выключить",
            "callback_data": f"off_{stype}",
            "style": "danger",
            "icon_custom_emoji_id": "5774077015388852135"  # красный крестик
        }
    else:
        # Если выключено - показываем зеленую кнопку "Включить"
        btn = {
            "text": "Включить",
            "callback_data": f"on_{stype}",
            "style": "success",
            "icon_custom_emoji_id": "5774022692642492953"  # зеленая галочка
        }

    return {"inline_keyboard": [
        [btn],
        [{"text": btn_back, "callback_data": "back_settings"}]
    ]}

# ===== ДИЗАЙН ПАНЕЛЬ С ПОЛНОЙ КАСТОМИЗАЦИЕЙ =====
def kb_design_main():
    """Главное меню дизайн-панели с кастомными названиями"""
    return {"inline_keyboard": [
        [{"text": get_custom_setting('design_btn_images'), "callback_data": "design_images"}],
        [{"text": get_custom_setting('design_btn_texts'), "callback_data": "design_texts"}],
        [{"text": get_custom_setting('design_btn_templates'), "callback_data": "design_templates"}],
        [{"text": get_custom_setting('design_btn_config'), "callback_data": "design_config"}],
        [{"text": get_custom_setting('design_btn_icons'), "callback_data": "design_icons"}],
        [{"text": "📝 Форматы", "callback_data": "design_formats"}],
        [{"text": "🎛 Кнопки", "callback_data": "design_buttons"}],
        [{"text": "⚙️ Управление функциями", "callback_data": "design_commands"}]
    ]}

def kb_design_images():
    """Меню настройки изображений"""
    return {"inline_keyboard": [
        [{"text": "🖼 Стартовое фото", "callback_data": "edit_start_image"}],
        [{"text": "👋 Приветствие", "callback_data": "edit_welcome_image"}],
        [{"text": "⚙️ Настройки", "callback_data": "edit_settings_image"}],
        [{"text": "🔒 Белый список ВКЛ", "callback_data": "edit_whitelist_on_image"}],
        [{"text": "🔓 Белый список ВЫКЛ", "callback_data": "edit_whitelist_off_image"}],
        [{"text": "‹ Назад", "callback_data": "design_main"}]
    ]}

def kb_design_texts():
    """Меню настройки текстов"""
    return {"inline_keyboard": [
        [{"text": "🏠 Приветствие /start", "callback_data": "edit_start_text"}],
        [{"text": "👋 При подключении", "callback_data": "edit_welcome_text"}],
        [{"text": "❓ Помощь /help", "callback_data": "edit_help_text"}],
        [{"text": "🔒 Белый список ВКЛ", "callback_data": "edit_whitelist_on_text"}],
        [{"text": "🔓 Белый список ВЫКЛ", "callback_data": "edit_whitelist_off_text"}],
        [{"text": "‹ Назад", "callback_data": "design_main"}]
    ]}

def kb_design_templates():
    """Меню настройки шаблонов"""
    return {"inline_keyboard": [
        [{"text": "🗑 Шаблон удаления", "callback_data": "edit_deleted_template"}],
        [{"text": "✏️ Шаблон редактирования", "callback_data": "edit_edited_template"}],
        [{"text": "⚡ Быстрое редактирование", "callback_data": "edit_edited_fast_template"}],
        [{"text": "‹ Назад", "callback_data": "design_main"}]
    ]}

def kb_design_config():
    """Меню настройки конфигурации"""
    return {"inline_keyboard": [
        [{"text": "🕐 Формат времени", "callback_data": "edit_time_format"}],
        [{"text": "🤖 Имя бота", "callback_data": "edit_bot_name"}],
        [{"text": "🔗 Ссылка инструкции", "callback_data": "edit_instruction_link"}],
        [{"text": "‹ Назад", "callback_data": "design_main"}]
    ]}

def kb_design_icons():
    """Меню настройки иконок"""
    return {"inline_keyboard": [
        [{"text": "📷 Фото", "callback_data": "edit_photo_icon"}, {"text": "🎥 Видео", "callback_data": "edit_video_icon"}],
        [{"text": "🎤 Голос", "callback_data": "edit_voice_icon"}, {"text": "🎵 Аудио", "callback_data": "edit_audio_icon"}],
        [{"text": "📎 Документ", "callback_data": "edit_document_icon"}, {"text": "🎞 GIF", "callback_data": "edit_animation_icon"}],
        [{"text": "⭕ Кружок", "callback_data": "edit_video_note_icon"}, {"text": "🎭 Стикер", "callback_data": "edit_sticker_icon"}],
        [{"text": "📞 Контакт", "callback_data": "edit_contact_icon"}, {"text": "📍 Локация", "callback_data": "edit_location_icon"}],
        [{"text": "📊 Опрос", "callback_data": "edit_poll_icon"}, {"text": "❓ Неизвестно", "callback_data": "edit_unknown_icon"}],
        [{"text": "‹ Назад", "callback_data": "design_main"}]
    ]}

def kb_design_buttons():
    """Меню настройки всех кнопок - разделено по категориям"""
    return {"inline_keyboard": [
        [{"text": "🏠 Главное меню", "callback_data": "buttons_main"}],
        [{"text": "⚙️ Кнопки настроек", "callback_data": "buttons_settings"}],
        [{"text": "🎨 Кнопки дизайн-панели", "callback_data": "buttons_design"}],
        [{"text": "  Кнопки уведомлений", "callback_data": "buttons_notifications"}],
        [{"text": " 🔙 Навигация", "callback_data": "buttons_navigation"}],
        [{"text": "💬 Сообщения", "callback_data": "buttons_messages"}],
        [{"text": "‹ Назад", "callback_data": "design_main"}]
    ]}

def kb_buttons_main():
    """Кнопки главного меню (старт)"""
    return {"inline_keyboard": [
        [{"text": "📋 Кнопка копирования", "callback_data": "edit_btn_copy_username"}],
        [{"text": "📖 Кнопка инструкции", "callback_data": "edit_btn_instruction"}],
        [{"text": "‹ Назад", "callback_data": "design_buttons"}]
    ]}

def kb_buttons_settings():
    """Кнопки для настроек"""
    return {"inline_keyboard": [
        [{"text": "📝 Редактирование", "callback_data": "edit_btn_settings_edits"}],
        [{"text": "🗑 Удаление", "callback_data": "edit_btn_settings_deletes"}],
        [{"text": "🎭 Блюр медиа", "callback_data": "edit_btn_settings_blur"}],
        [{"text": "✅ Кнопка включения", "callback_data": "edit_btn_turn_on"}],
        [{"text": "❌ Кнопка выключения", "callback_data": "edit_btn_turn_off"}],
        [{"text": "‹ Назад", "callback_data": "design_buttons"}]
    ]}

def kb_buttons_design():
    """Кнопки дизайн-панели"""
    return {"inline_keyboard": [
        [{"text": "📷 Изображения", "callback_data": "edit_design_btn_images"}],
        [{"text": "📝 Тексты", "callback_data": "edit_design_btn_texts"}],
        [{"text": "🎨 Шаблоны", "callback_data": "edit_design_btn_templates"}],
        [{"text": "⚙️ Настройки", "callback_data": "edit_design_btn_config"}],
        [{"text": "🔧 Иконки", "callback_data": "edit_design_btn_icons"}],
        [{"text": "🎭 Форматирование", "callback_data": "edit_design_btn_formatting"}],
        [{"text": "🔄 Сброс", "callback_data": "edit_design_btn_reset"}],
        [{"text": "‹ Назад", "callback_data": "design_buttons"}]
    ]}

def kb_buttons_navigation():
    """Кнопки навигации"""
    return {"inline_keyboard": [
        [{"text": "🔙 Кнопка назад", "callback_data": "edit_btn_back"}],
        [{"text": "‹ Назад", "callback_data": "design_buttons"}]
    ]}

def kb_buttons_notifications():
    """Кнопки в уведомлениях"""
    return {"inline_keyboard": [
        [{"text": "🗑 Кнопка 'Пропустить' (удаление)", "callback_data": "edit_btn_skip_delete"}],
        [{"text": "✏️ Кнопка 'Пропустить' (редактирование)", "callback_data": "edit_btn_skip_edit"}],
        [{"text": "‹ Назад", "callback_data": "design_buttons"}]
    ]}

def kb_buttons_messages():
    """Кнопки для сообщений"""
    return {"inline_keyboard": [
        [{"text": "✅ Сообщение 'Включено'", "callback_data": "edit_msg_enabled"}],
        [{"text": "❌ Сообщение 'Выключено'", "callback_data": "edit_msg_disabled"}],
        [{"text": "💾 Сообщение 'Сохранено'", "callback_data": "edit_msg_saved"}],
        [{"text": "❌ Сообщение 'Отменено'", "callback_data": "edit_msg_cancelled"}],
        [{"text": "‹ Назад", "callback_data": "design_buttons"}]
    ]}

def kb_design_interface():
    """Меню настройки кнопок интерфейса"""
    return {"inline_keyboard": [
        [{"text": "🏠 Кнопки главного меню", "callback_data": "interface_main"}],
        [{"text": "⚙️ Кнопки настроек", "callback_data": "interface_settings"}],
        [{"text": "🎨 Кнопки дизайн-панели", "callback_data": "interface_design"}],
        [{"text": "📝 Заголовки разделов", "callback_data": "interface_titles"}],
        [{"text": "💬 Системные сообщения", "callback_data": "interface_messages"}],
        [{"text": "🔘 Эмодзи статусов", "callback_data": "interface_emojis"}],
        [{"text": "‹ Назад", "callback_data": "design_main"}]
    ]}

def kb_interface_main():
    """Настройка кнопок главного меню"""
    return {"inline_keyboard": [
        [{"text": "📋 Кнопка копирования", "callback_data": "edit_btn_copy_username"}],
        [{"text": "📖 Кнопка инструкции", "callback_data": "edit_btn_instruction"}],
        [{"text": "‹ Назад", "callback_data": "design_interface"}]
    ]}

def kb_interface_settings():
    """Настройка кнопок настроек"""
    return {"inline_keyboard": [
        [{"text": "✏️ Кнопка редактирования", "callback_data": "edit_btn_settings_edits"}],
        [{"text": "🗑 Кнопка удаления", "callback_data": "edit_btn_settings_deletes"}],
        [{"text": "🎭 Кнопка блюра", "callback_data": "edit_btn_settings_blur"}],
        [{"text": "✅ Кнопка включения", "callback_data": "edit_btn_turn_on"}],
        [{"text": "❌ Кнопка выключения", "callback_data": "edit_btn_turn_off"}],
        [{"text": "‹ Назад", "callback_data": "design_interface"}]
    ]}

def kb_interface_design():
    """Настройка кнопок дизайн-панели"""
    return {"inline_keyboard": [
        [{"text": "📷 Изображения", "callback_data": "edit_design_btn_images"}],
        [{"text": "📝 Тексты", "callback_data": "edit_design_btn_texts"}],
        [{"text": "🎨 Шаблоны", "callback_data": "edit_design_btn_templates"}],
        [{"text": "⚙️ Настройки", "callback_data": "edit_design_btn_config"}],
        [{"text": "🔧 Иконки", "callback_data": "edit_design_btn_icons"}],
        [{"text": "🎭 Форматирование", "callback_data": "edit_design_btn_formatting"}],
        [{"text": "🔄 Сброс", "callback_data": "edit_design_btn_reset"}],
        [{"text": "‹ Назад", "callback_data": "design_interface"}]
    ]}

def kb_interface_titles():
    """Настройка заголовков разделов"""
    return {"inline_keyboard": [
        [{"text": "🎨 Заголовок дизайн-панели", "callback_data": "edit_design_main_title"}],
        [{"text": "📷 Заголовок изображений", "callback_data": "edit_design_images_title"}],
        [{"text": "📝 Заголовок текстов", "callback_data": "edit_design_texts_title"}],
        [{"text": "🎨 Заголовок шаблонов", "callback_data": "edit_design_templates_title"}],
        [{"text": "⚙️ Заголовок настроек", "callback_data": "edit_design_config_title"}],
        [{"text": "🔧 Заголовок иконок", "callback_data": "edit_design_icons_title"}],
        [{"text": "‹ Назад", "callback_data": "design_interface"}]
    ]}

def kb_interface_messages():
    """Настройка системных сообщений"""
    return {"inline_keyboard": [
        [{"text": "💾 Сообщение сохранения", "callback_data": "edit_msg_saved"}],
        [{"text": "❌ Сообщение отмены", "callback_data": "edit_msg_cancelled"}],
        [{"text": "✅ Сообщение включения", "callback_data": "edit_msg_enabled"}],
        [{"text": "❌ Сообщение выключения", "callback_data": "edit_msg_disabled"}],
        [{"text": "🔄 Подтверждение сброса", "callback_data": "edit_msg_reset_confirm"}],
        [{"text": "✅ Успех сброса", "callback_data": "edit_msg_reset_success"}],
        [{"text": "‹ Назад", "callback_data": "design_interface"}]
    ]}

def kb_interface_emojis():
    """Настройка эмодзи статусов"""
    return {"inline_keyboard": [
        [{"text": "✅ Эмодзи успеха", "callback_data": "edit_emoji_success"}],
        [{"text": "❌ Эмодзи ошибки", "callback_data": "edit_emoji_danger"}],
        [{"text": "⚠️ Эмодзи предупреждения", "callback_data": "edit_emoji_warning"}],
        [{"text": "ℹ️ Эмодзи информации", "callback_data": "edit_emoji_info"}],
        [{"text": "‹ Назад", "callback_data": "design_interface"}]
    ]}

def kb_design_inline_buttons():
    """Главное меню настройки стилей инлайн кнопок"""
    return {"inline_keyboard": [
        [{"text": "⚙️ Кнопки /settings", "callback_data": "inline_settings_buttons"}],
        [{"text": "‹ Назад", "callback_data": "design_main"}]
    ]}

def kb_inline_settings_buttons():
    """Настройка стилей кнопок /settings"""
    edits_on = get_custom_setting('style_edits_on', 'success')
    edits_off = get_custom_setting('style_edits_off', 'danger')
    deletes_on = get_custom_setting('style_deletes_on', 'success')
    deletes_off = get_custom_setting('style_deletes_off', 'danger')
    blur_on = get_custom_setting('style_blur_on', 'success')
    blur_off = get_custom_setting('style_blur_off', 'danger')

    return {"inline_keyboard": [
        [{"text": f"✏️ Уведомления об изменении (ВКЛ): {edits_on}", "callback_data": "style_edit_edits_on"}],
        [{"text": f"✏️ Уведомления об изменении (ВЫКЛ): {edits_off}", "callback_data": "style_edit_edits_off"}],
        [{"text": f"🗑 Уведомления об удалении (ВКЛ): {deletes_on}", "callback_data": "style_edit_deletes_on"}],
        [{"text": f"🗑 Уведомления об удалении (ВЫКЛ): {deletes_off}", "callback_data": "style_edit_deletes_off"}],
        [{"text": f"🎭 Блюр удаленных медиа (ВКЛ): {blur_on}", "callback_data": "style_edit_blur_on"}],
        [{"text": f"🎭 Блюр удаленных медиа (ВЫКЛ): {blur_off}", "callback_data": "style_edit_blur_off"}],
        [{"text": "‹ Назад", "callback_data": "design_inline_buttons"}]
    ]}

def kb_design_styles():
    """Настройка цветов кнопок"""
    return {"inline_keyboard": [
        [{"text": "🔘 Кнопки настроек", "callback_data": "style_settings_buttons"}],
        [{"text": "🏠 Кнопки главного меню", "callback_data": "style_main_buttons"}],
        [{"text": "🔙 Кнопки навигации", "callback_data": "style_nav_buttons"}],
        [{"text": "✅ Эмодзи успеха", "callback_data": "edit_emoji_success"}],
        [{"text": "❌ Эмодзи ошибки", "callback_data": "edit_emoji_danger"}],
        [{"text": "🎨 Быстрые схемы", "callback_data": "design_color_schemes"}],
        [{"text": "‹ Назад", "callback_data": "design_main"}]
    ]}

def kb_style_settings_buttons():
    """Настройка цветов кнопок настроек"""
    return {"inline_keyboard": [
        [{"text": "✏️ Кнопка редактирования", "callback_data": "set_btn_color_edits"}],
        [{"text": "🗑 Кнопка удаления", "callback_data": "set_btn_color_deletes"}],
        [{"text": "🎭 Кнопка блюра", "callback_data": "set_btn_color_blur"}],
        [{"text": "✅ Кнопка включения", "callback_data": "set_btn_color_on"}],
        [{"text": "❌ Кнопка выключения", "callback_data": "set_btn_color_off"}],
        [{"text": "‹ Назад к стилям", "callback_data": "design_styles"}]
    ]}

def kb_style_main_buttons():
    """Настройка цветов кнопок главного меню"""
    return {"inline_keyboard": [
        [{"text": "📋 Кнопка копирования", "callback_data": "set_btn_color_copy"}],
        [{"text": "📖 Кнопка инструкции", "callback_data": "set_btn_color_instruction"}],
        [{"text": "‹ Назад к стилям", "callback_data": "design_styles"}]
    ]}

def kb_style_nav_buttons():
    """Настройка цветов кнопок навигации"""
    return {"inline_keyboard": [
        [{"text": "🔙 Кнопка назад", "callback_data": "set_btn_color_back"}],
        [{"text": "‹ Назад к стилям", "callback_data": "design_styles"}]
    ]}

def kb_color_picker(button_type):
    """Выбор цвета для кнопки"""
    current_style = get_custom_setting(f'btn_{button_type}_style', '')

    def make_btn(color, style, is_current=False):
        check = "✅ " if is_current else ""
        return {"text": f"{check}{color}", "callback_data": f"apply_color_{button_type}_{style}"}

    return {"inline_keyboard": [
        [make_btn("🔵 Синий", "primary", current_style == "primary")],
        [make_btn("🟢 Зелёный", "success", current_style == "success")],
        [make_btn("🔴 Красный", "danger", current_style == "danger")],
        [make_btn("⚪ Очистить цвет", "clear", current_style == "")],
        [{"text": "‹ Назад", "callback_data": f"style_{get_button_group(button_type)}_buttons"}]
    ]}

def get_button_group(button_type):
    """Определяет группу кнопки для навигации"""
    if button_type in ["edits", "deletes", "blur", "on", "off"]:
        return "settings"
    elif button_type in ["copy", "instruction"]:
        return "main"
    elif button_type in ["back"]:
        return "nav"
    return "settings"

def kb_color_schemes():
    """Быстрые цветовые схемы"""
    return {"inline_keyboard": [
        [{"text": "🟢 Зелёная тема", "callback_data": "scheme_green"}],
        [{"text": "🔴 Красная тема", "callback_data": "scheme_red"}],
        [{"text": "🔵 Синяя тема", "callback_data": "scheme_blue"}],
        [{"text": "🗑 Очистить все цвета", "callback_data": "scheme_clear"}],
        [{"text": "‹ Назад", "callback_data": "design_styles"}]
    ]}

def kb_design_formats():
    """Меню форматов (HTML и эмодзи)"""
    return {"inline_keyboard": [
        [{"text": "🔧 Генератор HTML", "callback_data": "html_generator"}],
        [{"text": "📋 Примеры кода", "callback_data": "html_examples"}],
        [{"text": "🎭 Генератор Premium эмодзи", "callback_data": "emoji_generator"}],
        [{"text": "‹ Назад", "callback_data": "design_main"}]
    ]}

def kb_design_commands():
    """Меню управления функциями бота"""
    start_enabled = get_custom_setting('cmd_start_enabled', '1') == '1'
    settings_enabled = get_custom_setting('cmd_settings_enabled', '1') == '1'
    help_enabled = get_custom_setting('cmd_help_enabled', '1') == '1'
    stats_enabled = get_custom_setting('cmd_stats_enabled', '1') == '1'
    plus_enabled = get_custom_setting('cmd_plus_enabled', '1') == '1'
    chat_enabled = get_custom_setting('cmd_chat_enabled', '1') == '1'

    def cmd_button(text, cmd_key, is_enabled):
        status = "✅" if is_enabled else "❌"
        return {"text": f"{status} {text}", "callback_data": f"toggle_cmd_{cmd_key}"}

    return {"inline_keyboard": [
        [cmd_button("Команда /start", "start", start_enabled)],
        [cmd_button("Команда /settings", "settings", settings_enabled)],
        [cmd_button("Команда /help", "help", help_enabled)],
        [cmd_button("Команда /stats", "stats", stats_enabled)],
        [cmd_button("Команда /plus", "plus", plus_enabled)],
        [cmd_button("Экспорт чатов /chat", "chat", chat_enabled)],
        [{"text": "‹ Назад", "callback_data": "design_main"}]
    ]}

def kb_html_helper():
    """Генератор HTML тегов"""
    return {"inline_keyboard": [
        [{"text": "💪 Жирный", "callback_data": "html_bold"}, {"text": "💬 Курсив", "callback_data": "html_italic"}],
        [{"text": "📝 Подчёркнутый", "callback_data": "html_underline"}, {"text": "❌ Зачёркнутый", "callback_data": "html_strike"}],
        [{"text": "💻 Код", "callback_data": "html_code"}, {"text": "🙈 Спойлер", "callback_data": "html_spoiler"}],
        [{"text": "💬 Цитата", "callback_data": "html_quote"}, {"text": "🔗 Ссылка", "callback_data": "html_link"}],
        [{"text": "📦 Блок кода", "callback_data": "html_pre"}],
        [{"text": "‹ Назад", "callback_data": "design_formats"}]
    ]}

def kb_design_preview(setting_key):
    """Кнопки для предпросмотра настройки"""
    buttons = [
        [{"text": "👀 Предпросмотр", "callback_data": f"preview_{setting_key}"}],
        [{"text": "💾 Сохранить", "callback_data": f"save_{setting_key}"}, {"text": "❌ Отмена", "callback_data": "cancel_edit"}]
    ]

    # Добавляем кнопку удаления для изображений
    if get_setting_type(setting_key) == 'image':
        buttons.insert(1, [{"text": "🗑 Удалить изображение", "callback_data": f"delete_{setting_key}"}])

    return {"inline_keyboard": buttons}

# ===== ДИНАМИЧЕСКИЕ ТЕКСТЫ НАСТРОЕК =====
def get_setting_text(stype):
    """Получает текст настройки с кастомизацией"""
    if stype == "edits":
        title = get_custom_setting('setting_edits_title')
        desc = get_custom_setting('setting_edits_desc')
        return f"{title}\n\n{desc}"

    elif stype == "deletes":
        title = get_custom_setting('setting_deletes_title')
        desc = get_custom_setting('setting_deletes_desc')
        return f"{title}\n\n{desc}"

    elif stype == "blur":
        title = get_custom_setting('setting_blur_title')
        desc = get_custom_setting('setting_blur_desc')
        return f"{title}\n\n{desc}"

    return "Настройка не найдена"

SETTING_TEXTS = {
    "edits": get_setting_text("edits"),
    "deletes": get_setting_text("deletes"),
    "blur": get_setting_text("blur")
}

SETTING_KEYS = {"edits": "notify_edits", "deletes": "notify_deletes", "blur": "blur_media"}

# ===== ОБРАБОТЧИКИ ДИЗАЙН-ПАНЕЛИ =====
def handle_design_command(chat_id, user_id):
    """Обработчик команды /design"""
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    send_msg(chat_id,
        "🎨 <b>Дизайн-панель бота</b>\n\n"
        "Здесь вы можете настроить:\n"
        "📷 <b>Изображения</b> — фото в сообщениях\n"
        "📝 <b>Тексты</b> — приветствие, помощь\n"
        "🎨 <b>Шаблоны</b> — удаление, редактирование\n"
        "⚙️ <b>Настройки</b> — формат времени, ссылки\n"
        "🔧 <b>Иконки</b> — символы типов медиа\n"
        "🎭 <b>Форматирование</b> — HTML разметка\n\n"
        "💡 <i>Используйте плейсхолдеры в шаблонах:</i>\n"
        "<code>{sender}</code> — имя отправителя\n"
        "<code>{time}</code> — время\n"
        "<code>{content}</code> — текст сообщения\n"
        "<code>{chat}</code> — название чата\n"
        "<code>{bot_name}</code> — имя бота",
        markup=kb_design_main())

def handle_design_callback(cb):
    """Обработчик callback'ов дизайн-панели"""
    cb_id = cb["id"]
    data = cb["data"]
    user_id = cb["from"]["id"]
    chat_id = cb["message"]["chat"]["id"]
    msg_id = cb["message"]["message_id"]

    print(f"[DESIGN DEBUG] Received: {data}")

    if not is_admin(user_id):
        print(f"[DESIGN DEBUG] Access denied for user {user_id}")
        answer_cb(cb_id, "⛔ Нет доступа", alert=True)
        return

    print(f"[DESIGN DEBUG] Processing {data} for admin {user_id}")

    # СУПЕР ПРОСТОЙ ТЕСТ
    if data == "super_test":
        send_msg(chat_id, "🧪 <b>СУПЕР ТЕСТ УСПЕШЕН!</b>\n\nОбработчик design callback работает!")
        answer_cb(cb_id, "✅ Тест в handle_design_callback работает!", alert=True)
        return

    # ДОПОЛНИТЕЛЬНАЯ ОТЛАДКА ДЛЯ design_formatting
    if data == "design_formatting":
        print(f"[FORMATTING DEBUG] FOUND design_formatting callback!")
        try:
            print(f"[FORMATTING DEBUG] About to edit message")
            edit_txt(chat_id, msg_id, "🔧 ТЕСТ ФОРМАТИРОВАНИЯ", markup=None)
            print(f"[FORMATTING DEBUG] Message edited successfully")
            answer_cb(cb_id)
            print(f"[FORMATTING DEBUG] Callback answered")
        except Exception as e:
            print(f"[FORMATTING ERROR] Error: {e}")
        return

    # Навигация по разделам
    if data == "design_main":
        edit_txt(chat_id, msg_id,
            "🎨 <b>Дизайн-панель бота</b>\n\nВыберите раздел для настройки:",
            markup=kb_design_main())
        answer_cb(cb_id)

    elif data == "design_images":
        edit_txt(chat_id, msg_id,
            "📷 <b>Настройка изображений</b>\n\nВыберите изображение для изменения:\n\n"
            "💡 <i>Отправьте фото или ссылку на изображение</i>",
            markup=kb_design_images())
        answer_cb(cb_id)

    elif data == "design_texts":
        edit_txt(chat_id, msg_id,
            "📝 <b>Настройка текстов</b>\n\nВыберите текст для изменения:\n\n"
            "💡 <i>Можно использовать HTML разметку и плейсхолдеры</i>",
            markup=kb_design_texts())
        answer_cb(cb_id)

    elif data == "design_templates":
        edit_txt(chat_id, msg_id,
            "🎨 <b>Настройка шаблонов</b>\n\nВыберите шаблон для изменения:\n\n"
            "💡 <i>Доступные плейсхолдеры:</i>\n"
            "<code>{sender}</code> — отправитель\n"
            "<code>{time}</code> — время\n"
            "<code>{content}</code>, <code>{old_content}</code>, <code>{new_content}</code> — содержимое\n"
            "<code>{chat}</code> — чат",
            markup=kb_design_templates())
        answer_cb(cb_id)

    elif data == "design_config":
        edit_txt(chat_id, msg_id,
            "⚙️ <b>Настройка конфигурации</b>\n\nВыберите параметр для изменения:",
            markup=kb_design_config())
        answer_cb(cb_id)

    elif data == "design_icons":
        edit_txt(chat_id, msg_id,
            get_custom_setting('design_icons_title', '🔧 Настройка иконок') + "\n\n" +
            get_custom_setting('design_icons_desc', 'Выберите иконку для изменения:\n\n💡 Используйте эмодзи или текст'),
            markup=kb_design_icons())
        answer_cb(cb_id)

    elif data == "design_buttons":
        edit_txt(chat_id, msg_id,
            "🎛 <b>НАСТРОЙКА КНОПОК</b>\n\n"
            "Выберите категорию кнопок для редактирования:\n\n"
            "🏠 <b>Главное меню</b> — кнопки на старте\n"
            "⚙️ <b>Кнопки настроек</b> — редактирование, удаление, блюр\n"
            "🎨 <b>Кнопки дизайн-панели</b> — меню /design\n"
            "🔔 <b>Кнопки уведомлений</b> — кнопка 'Пропустить'\n"
            "🔙 <b>Навигация</b> — кнопка назад\n"
            "💬 <b>Сообщения</b> — тексты уведомлений\n\n"
            "💡 <i>Вы можете изменить название, эмодзи любой кнопки</i>",
            markup=kb_design_buttons())
        answer_cb(cb_id)

    elif data == "design_inline_buttons":
        edit_txt(chat_id, msg_id,
            "🎨 <b>НАСТРОЙКА СТИЛЕЙ ИНЛАЙН КНОПОК</b>\n\n"
            "Выберите категорию кнопок для настройки цветов:\n\n"
            "⚙️ <b>Кнопки /settings</b> — редактирование, удаление, блюр\n\n"
            "💡 <i>Настройте цвета кнопок когда функция включена/выключена</i>\n"
            "🟢 <code>success</code> — зелёный\n"
            "🔴 <code>danger</code> — красный\n"
            "🔵 <code>primary</code> — синий\n"
            "⚪ <code>secondary</code> — серый",
            markup=kb_design_inline_buttons())
        answer_cb(cb_id)

    elif data == "inline_settings_buttons":
        edit_txt(chat_id, msg_id,
            "⚙️ <b>СТИЛИ КНОПОК /SETTINGS</b>\n\n"
            "Настройте цвета кнопок когда функция включена (ВКЛ) или выключена (ВЫКЛ):\n\n"
            "Доступные стили:\n"
            "🟢 <code>success</code> — зелёный\n"
            "🔴 <code>danger</code> — красный\n"
            "🔵 <code>primary</code> — синий\n"
            "⚪ <code>secondary</code> — серый",
            markup=kb_inline_settings_buttons())
        answer_cb(cb_id)

    elif data == "buttons_main":
        edit_txt(chat_id, msg_id,
            "🏠 <b>Кнопки главного меню</b>\n\n"
            "Выберите кнопку для редактирования:",
            markup=kb_buttons_main())
        answer_cb(cb_id)

    elif data == "buttons_settings":
        edit_txt(chat_id, msg_id,
            "⚙️ <b>Кнопки настроек</b>\n\n"
            "Выберите кнопку для редактирования:",
            markup=kb_buttons_settings())
        answer_cb(cb_id)

    elif data == "buttons_design":
        edit_txt(chat_id, msg_id,
            "🎨 <b>Кнопки дизайн-панели</b>\n\n"
            "Выберите кнопку для редактирования:",
            markup=kb_buttons_design())
        answer_cb(cb_id)

    elif data == "buttons_navigation":
        edit_txt(chat_id, msg_id,
            "🔙 <b>Кнопки навигации</b>\n\n"
            "Выберите кнопку для редактирования:",
            markup=kb_buttons_navigation())
        answer_cb(cb_id)

    elif data == "buttons_notifications":
        edit_txt(chat_id, msg_id,
            "🔔 <b>Кнопки в уведомлениях</b>\n\n"
            "Это кнопки под сообщениями об удалении и редактировании.\n\n"
            "Выберите кнопку для редактирования:",
            markup=kb_buttons_notifications())
        answer_cb(cb_id)

    elif data == "buttons_messages":
        edit_txt(chat_id, msg_id,
            "💬 <b>Сообщения</b>\n\n"
            "Выберите сообщение для редактирования:",
            markup=kb_buttons_messages())
        answer_cb(cb_id)

    elif data == "design_interface":
        edit_txt(chat_id, msg_id,
            "🌈 <b>Настройка кнопок интерфейса</b>\n\nВыберите раздел для настройки:\n\n"
            "💡 <i>Здесь можно изменить все тексты кнопок и элементов интерфейса</i>",
            markup=kb_design_interface())
        answer_cb(cb_id)

    elif data == "design_styles":
        edit_txt(chat_id, msg_id,
            "🎨 <b>Настройка цветов кнопок</b>\n\nВыберите группу кнопок:\n\n"
            "💡 <i>Можно задать индивидуальный цвет каждой кнопке</i>",
            markup=kb_design_styles())
        answer_cb(cb_id)

    # Обработчики групп кнопок
    elif data == "style_settings_buttons":
        edit_txt(chat_id, msg_id,
            "🔘 <b>Цвета кнопок настроек</b>\n\nВыберите кнопку для изменения цвета:",
            markup=kb_style_settings_buttons())
        answer_cb(cb_id)

    elif data == "style_main_buttons":
        edit_txt(chat_id, msg_id,
            "🏠 <b>Цвета кнопок главного меню</b>\n\nВыберите кнопку для изменения цвета:",
            markup=kb_style_main_buttons())
        answer_cb(cb_id)

    elif data == "style_nav_buttons":
        edit_txt(chat_id, msg_id,
            "🔙 <b>Цвета кнопок навигации</b>\n\nВыберите кнопку для изменения цвета:",
            markup=kb_style_nav_buttons())
        answer_cb(cb_id)

    # Обработчики выбора кнопки для покраски
    elif data.startswith("set_btn_color_"):
        button_type = data[14:]  # убираем "set_btn_color_"
        button_names = {
            "edits": "✏️ Редактирование",
            "deletes": "🗑 Удаление",
            "blur": "🎭 Блюр",
            "on": "✅ Включение",
            "off": "❌ Выключение",
            "copy": "📋 Копирование",
            "instruction": "📖 Инструкция",
            "back": "🔙 Назад"
        }
        button_name = button_names.get(button_type, button_type)
        edit_txt(chat_id, msg_id,
            f"🎨 <b>Цвет кнопки: {button_name}</b>\n\nВыберите цвет:\n\n"
            f"💡 <i>Текущий цвет: {get_custom_setting(f'btn_{button_type}_style', 'не задан')}</i>",
            markup=kb_color_picker(button_type))
        answer_cb(cb_id)

    # Применение цвета
    elif data.startswith("apply_color_"):
        parts = data[12:].split("_", 1)  # убираем "apply_color_"
        if len(parts) == 2:
            button_type, color = parts
            if color == "clear":
                set_custom_setting(f'btn_{button_type}_style', '')
                color_name = "сброшен"
            else:
                set_custom_setting(f'btn_{button_type}_style', color)
                color_names = {"primary": "синий", "success": "зелёный", "danger": "красный"}
                color_name = color_names.get(color, color)

            button_names = {
                "edits": "✏️ Редактирование",
                "deletes": "🗑 Удаление",
                "blur": "🎭 Блюр",
                "on": "✅ Включение",
                "off": "❌ Выключение",
                "copy": "📋 Копирование",
                "instruction": "📖 Инструкция",
                "back": "🔙 Назад"
            }
            button_name = button_names.get(button_type, button_type)

            edit_txt(chat_id, msg_id,
                f"✅ <b>Цвет применён!</b>\n\n"
                f"🎨 Кнопка: {button_name}\n"
                f"🌈 Цвет: {color_name}",
                markup=kb_color_picker(button_type))
            answer_cb(cb_id, f"Цвет {color_name} применён к кнопке {button_name}!", alert=True)

    elif data == "design_color_schemes":
        edit_txt(chat_id, msg_id,
            "🎨 <b>Цветовые схемы</b>\n\nВыберите предустановленную тему:\n\n"
            "💡 <i>Быстро примените готовую цветовую схему</i>",
            markup=kb_color_schemes())
        answer_cb(cb_id)

    elif data.startswith("scheme_"):
        scheme = data[7:]  # убираем "scheme_"
        apply_color_scheme(scheme)

        scheme_names = {
            "green": "Зелёная",
            "red": "Красная",
            "blue": "Синяя",
            "clear": "Очистка цветов"
        }
        scheme_name = scheme_names.get(scheme, scheme.title())

        if scheme == "clear":
            message = "🗑 <b>Все цвета очищены!</b>\n\nВсе кнопки вернулись к стандартному виду"
        else:
            message = f"🎨 <b>Схема применена!</b>\n\n✅ Активирована: <b>{scheme_name}</b>\n\n💡 Все кнопки получили единый стиль"

        edit_txt(chat_id, msg_id, message, markup=kb_color_schemes())
        answer_cb(cb_id, f"✅ {scheme_name} применена!", alert=True)

    elif data == "preview_demo":
        answer_cb(cb_id, "👀 Это демонстрация стиля кнопки!", alert=True)

    elif data == "preview_button_styles":
        preview_button_styles(chat_id, user_id)
        answer_cb(cb_id)

    # Обработка демо-кнопок для предпросмотра стилей
    elif data == "demo_on":
        answer_cb(cb_id, "✅ Демо: включенная настройка", alert=True)

    elif data == "demo_off":
        answer_cb(cb_id, "❌ Демо: выключенная настройка", alert=True)

    elif data == "demo_primary":
        answer_cb(cb_id, "🔵 Демо: основной стиль кнопки", alert=True)

    elif data == "demo_secondary":
        answer_cb(cb_id, "⚫ Демо: вторичный стиль кнопки", alert=True)

    # Обработка подменю интерфейса
    elif data == "interface_main":
        edit_txt(chat_id, msg_id,
            "🏠 <b>Кнопки главного меню</b>\n\nНастройка кнопок стартового экрана:",
            markup=kb_interface_main())
        answer_cb(cb_id)

    elif data == "interface_settings":
        edit_txt(chat_id, msg_id,
            "⚙️ <b>Кнопки настроек</b>\n\nНастройка кнопок в меню настроек:",
            markup=kb_interface_settings())
        answer_cb(cb_id)

    elif data == "interface_design":
        edit_txt(chat_id, msg_id,
            "🎨 <b>Кнопки дизайн-панели</b>\n\nНастройка названий разделов дизайна:",
            markup=kb_interface_design())
        answer_cb(cb_id)

    elif data == "interface_titles":
        edit_txt(chat_id, msg_id,
            "📝 <b>Заголовки разделов</b>\n\nНастройка заголовков в дизайн-панели:",
            markup=kb_interface_titles())
        answer_cb(cb_id)

    elif data == "interface_messages":
        edit_txt(chat_id, msg_id,
            "💬 <b>Системные сообщения</b>\n\nНастройка текстов уведомлений:",
            markup=kb_interface_messages())
        answer_cb(cb_id)

    elif data == "interface_emojis":
        edit_txt(chat_id, msg_id,
            "🔘 <b>Эмодзи статусов</b>\n\nНастройка эмодзи для разных состояний:",
            markup=kb_interface_emojis())
        answer_cb(cb_id)

    elif data == "design_formats":
        # ОБРАБОТЧИК МЕНЮ ФОРМАТОВ
        edit_txt(chat_id, msg_id,
            "📝 <b>ФОРМАТЫ ТЕКСТА</b>\n\n"
            "Выберите инструмент:\n\n"
            "🔧 <b>Генератор HTML</b> — создайте готовые HTML теги для форматирования текста\n\n"
            "📋 <b>Примеры кода</b> — посмотрите все доступные HTML теги с примерами\n\n"
            "🎭 <b>Генератор Premium эмодзи</b> — создайте тег для Premium эмодзи по ID\n\n"
            "💡 <i>Все HTML теги работают в шаблонах удаления, редактирования и других текстах бота</i>",
            markup=kb_design_formats())
        answer_cb(cb_id)

    elif data == "design_commands":
        edit_txt(chat_id, msg_id,
            "⚙️ <b>Управление функциями бота</b>\n\nВключите или отключите команды:\n\n"
            "💡 <i>Отключенные команды не будут работать для пользователей</i>",
            markup=kb_design_commands())
        answer_cb(cb_id)

    elif data == "html_generator":
        # ГЕНЕРАТОР HTML ТЕГОВ
        edit_txt(chat_id, msg_id,
            "🔧 <b>ГЕНЕРАТОР HTML ТЕГОВ</b>\n\n"
            "Нажмите на кнопку, чтобы получить готовый HTML код.\n\n"
            "📌 <b>Как использовать:</b>\n"
            "1. Нажмите кнопку нужного форматирования\n"
            "2. Скопируйте код из сообщения\n"
            "3. Замените \"ваш текст\" на свой текст\n"
            "4. Вставьте в любой шаблон в /design\n\n"
            "💡 <i>Все коды работают в шаблонах удаления, редактирования и других текстах</i>",
            markup=kb_html_helper())
        answer_cb(cb_id)

    elif data == "html_examples":
        # ПРИМЕРЫ HTML КОДА
        examples_text = (
            "📋 <b>ПРИМЕРЫ HTML КОДА:</b>\n\n"
            "1️⃣ <b>Жирный</b>: <code>&lt;b&gt;текст&lt;/b&gt;</code>\n"
            "   Результат: <b>текст</b>\n\n"
            "2️⃣ <i>Курсив</i>: <code>&lt;i&gt;текст&lt;/i&gt;</code>\n"
            "   Результат: <i>текст</i>\n\n"
            "3️⃣ <u>Подчёркнутый</u>: <code>&lt;u&gt;текст&lt;/u&gt;</code>\n"
            "   Результат: <u>текст</u>\n\n"
            "4️⃣ <s>Зачёркнутый</s>: <code>&lt;s&gt;текст&lt;/s&gt;</code>\n"
            "   Результат: <s>текст</s>\n\n"
            "5️⃣ <code>Моноширинный</code>: <code>&lt;code&gt;текст&lt;/code&gt;</code>\n"
            "   Результат: <code>текст</code>\n\n"
            "6️⃣ Спойлер: <code>&lt;tg-spoiler&gt;текст&lt;/tg-spoiler&gt;</code>\n\n"
            "7️⃣ Цитата:\n"
            "<code>&lt;blockquote&gt;текст&lt;/blockquote&gt;</code>\n"
            "   Результат:\n<blockquote>текст</blockquote>\n\n"
            "🔗 <b>Ссылка:</b>\n<code>&lt;a href=\"https://site.com\"&gt;текст&lt;/a&gt;</code>\n\n"
            "📦 <b>Блок кода:</b>\n<code>&lt;pre&gt;много\nстрок\nкода&lt;/pre&gt;</code>\n\n"
            "✅ <b>Все эти теги работают в шаблонах!</b>"
        )
        edit_txt(chat_id, msg_id, examples_text, markup=kb_design_formats())
        answer_cb(cb_id)

    elif data == "emoji_generator":
        # ГЕНЕРАТОР PREMIUM ЭМОДЗИ
        edit_txt(chat_id, msg_id,
            "🎭 <b>ГЕНЕРАТОР PREMIUM ЭМОДЗИ</b>\n\n"
            "📝 <b>Отправьте ID эмодзи</b>, чтобы получить готовый тег.\n\n"
            "💡 <b>Где взять ID эмодзи:</b>\n"
            "• Найдите эмодзи в @PremiumEmojiBot\n"
            "• Или используйте популярные ID:\n"
            "   <code>5465665476357570821</code> — 🔥\n"
            "   <code>5467644880818014071</code> — ❤️\n"
            "   <code>5472105853051474482</code> — 👍\n\n"
            "📌 <b>Как использовать:</b>\n"
            "1. Отправьте ID эмодзи (например: 5465665476357570821)\n"
            "2. Получите готовый тег для вставки\n"
            "3. Вставьте в любой шаблон в /design\n\n"
            "⚠️ <b>Работает только с Telegram Premium</b>",
            markup=kb_design_formats())
        answer_cb(cb_id)

        # Устанавливаем состояние ожидания ID эмодзи
        set_admin_state(user_id, {"action": "awaiting_emoji_id"})

    # ОБРАБОТКА HTML КНОПОК
    elif data.startswith("html_"):
        html_type = data[5:]  # убираем "html_"

        html_codes = {
            "bold": ("<b>", "</b>", "жирный", "<b>ваш текст</b>"),
            "italic": ("<i>", "</i>", "курсив", "<i>ваш текст</i>"),
            "code": ("<code>", "</code>", "моноширинный", "<code>ваш текст</code>"),
            "strike": ("<s>", "</s>", "зачёркнутый", "<s>ваш текст</s>"),
            "underline": ("<u>", "</u>", "подчёркнутый", "<u>ваш текст</u>"),
            "spoiler": ("<tg-spoiler>", "</tg-spoiler>", "спойлер", "<tg-spoiler>ваш текст</tg-spoiler>"),
            "quote": ("<blockquote>", "</blockquote>", "цитата", "<blockquote>ваш текст</blockquote>"),
            "link": ('<a href="https://example.com">', "</a>", "ссылка", '<a href="https://example.com">текст ссылки</a>'),
            "pre": ("<pre>", "</pre>", "блок кода", "<pre>ваш\nмногострочный\nкод</pre>")
        }

        if html_type in html_codes:
            start_tag, end_tag, description, example = html_codes[html_type]

            # Отправляем код отдельным сообщением с примером
            send_msg(chat_id,
                f"✅ <b>HTML код для \"{description}\":</b>\n\n"
                f"<code>{example}</code>\n\n"
                f"📋 <b>Как использовать:</b>\n"
                f"1. Скопируйте код выше\n"
                f"2. Замените \"ваш текст\" на свой текст\n"
                f"3. Вставьте в шаблон в /design\n\n"
                f"📌 <b>Пример результата:</b>\n"
                f"{start_tag}пример текста{end_tag}")

            answer_cb(cb_id, f"✅ Код для {description} отправлен!")
        else:
            answer_cb(cb_id, "❌ Ошибка: неизвестный тип", alert=True)

    elif data.startswith("toggle_cmd_"):
        cmd_type = data[11:]  # убираем "toggle_cmd_"
        setting_key = f"cmd_{cmd_type}_enabled"
        current_value = get_custom_setting(setting_key, "1")
        new_value = "0" if current_value == "1" else "1"
        set_custom_setting(setting_key, new_value)

        cmd_names = {
            "start": "/start",
            "settings": "/settings",
            "help": "/help",
            "stats": "/stats",
            "chat": "/chat",
            "plus": "/plus"
        }
        cmd_name = cmd_names.get(cmd_type, cmd_type)
        status = "включена" if new_value == "1" else "отключена"

        edit_txt(chat_id, msg_id,
            "⚙️ <b>Управление функциями бота</b>\n\nВключите или отключите команды:\n\n"
            "💡 <i>Отключенные команды не будут работать для пользователей</i>",
            markup=kb_design_commands())
        answer_cb(cb_id, f"Команда {cmd_name} {status}", alert=True)

    # Отмена редактирования
    elif data == "cancel_edit":
        clear_admin_state(user_id)
        edit_txt(chat_id, msg_id,
            "🎨 <b>Дизайн-панель бота</b>\n\nВыберите раздел для настройки:",
            markup=kb_design_main())
        answer_cb(cb_id, "❌ Редактирование отменено")

    # Изменение стилей инлайн кнопок
    elif data.startswith("style_edit_"):
        style_key = data[11:]  # убираем "style_edit_"

        # Показываем меню выбора стиля
        current_style = get_custom_setting(style_key, 'success')

        style_names = {
            'edits_on': '✏️ Уведомления об изменении (ВКЛ)',
            'edits_off': '✏️ Уведомления об изменении (ВЫКЛ)',
            'deletes_on': '🗑 Уведомления об удалении (ВКЛ)',
            'deletes_off': '🗑 Уведомления об удалении (ВЫКЛ)',
            'blur_on': '🎭 Блюр удаленных медиа (ВКЛ)',
            'blur_off': '🎭 Блюр удаленных медиа (ВЫКЛ)'
        }

        button_name = style_names.get(style_key, style_key)

        edit_txt(chat_id, msg_id,
            f"🎨 <b>Изменение стиля кнопки</b>\n\n"
            f"Кнопка: <b>{button_name}</b>\n"
            f"Текущий стиль: <code>{current_style}</code>\n\n"
            f"Выберите новый стиль:",
            markup={
                "inline_keyboard": [
                    [{"text": "🟢 success (зелёный)", "callback_data": f"set_style_{style_key}_success"}],
                    [{"text": "🔴 danger (красный)", "callback_data": f"set_style_{style_key}_danger"}],
                    [{"text": "🔵 primary (синий)", "callback_data": f"set_style_{style_key}_primary"}],
                    [{"text": "⚪ secondary (серый)", "callback_data": f"set_style_{style_key}_secondary"}],
                    [{"text": "‹ Назад", "callback_data": "inline_settings_buttons"}]
                ]
            })
        answer_cb(cb_id)

    # Сохранение стиля
    elif data.startswith("set_style_"):
        parts = data[10:].rsplit('_', 1)  # убираем "set_style_" и разделяем
        style_key = parts[0]
        new_style = parts[1]

        # Сохраняем новый стиль
        set_custom_setting(f'style_{style_key}', new_style)

        edit_txt(chat_id, msg_id,
            f"✅ <b>Стиль обновлён!</b>\n\n"
            f"Новый стиль: <code>{new_style}</code>\n\n"
            f"Проверьте изменения в /settings",
            markup={"inline_keyboard": [[{"text": "‹ Назад", "callback_data": "inline_settings_buttons"}]]})
        answer_cb(cb_id, "✅ Стиль сохранён!", alert=True)

    # Редактирование настроек
    elif data.startswith("edit_"):
        setting_key = data[5:]  # убираем "edit_"
        handle_edit_setting(chat_id, user_id, msg_id, setting_key)
        answer_cb(cb_id)

    # Удаление изображения
    elif data.startswith("delete_"):
        setting_key = data[7:]  # убираем "delete_"
        delete_custom_setting(setting_key)
        edit_txt(chat_id, msg_id,
            f"🗑 <b>Изображение удалено</b>\n\n"
            f"Настройка <b>{get_setting_description(setting_key)}</b> сброшена к стандартному значению.",
            markup=kb_design_main())
        answer_cb(cb_id, "🗑 Изображение удалено!", alert=True)

    # Предпросмотр
    elif data.startswith("preview_"):
        setting_key = data[8:]  # убираем "preview_"
        handle_preview_setting(chat_id, user_id, setting_key)
        answer_cb(cb_id)

    # Сохранение
    elif data.startswith("save_"):
        setting_key = data[5:]  # убираем "save_"
        handle_save_setting(chat_id, user_id, setting_key)
        answer_cb(cb_id, "✅ Сохранено!", alert=True)

    # Сброс настроек
    elif data == "design_reset":
        edit_txt(chat_id, msg_id,
            "🔄 <b>Сброс настроек</b>\n\n"
            "⚠️ Все настройки дизайна будут сброшены к стандартным.\n\n"
            "Вы уверены?",
            markup={"inline_keyboard": [
                [{"text": "✅ Да, сбросить", "callback_data": "confirm_reset"}],
                [{"text": "❌ Отмена", "callback_data": "design_main"}]
            ]})
        answer_cb(cb_id)

    elif data == "confirm_reset":
        reset_design_settings()
        edit_txt(chat_id, msg_id,
            "✅ <b>Настройки сброшены</b>\n\nВсе параметры дизайна возвращены к стандартным значениям.",
            markup=kb_design_main())
        answer_cb(cb_id)

def handle_edit_setting(chat_id, user_id, msg_id, setting_key):
    """Начало редактирования настройки"""
    current_value = get_custom_setting(setting_key)
    description = get_setting_description(setting_key)
    setting_type = get_setting_type(setting_key)

    # Сохраняем состояние редактирования
    set_admin_state(user_id, {
        "action": "design_edit",
        "setting_key": setting_key,
        "original_msg_id": msg_id
    })

    text = f"✏️ <b>Редактирование:</b> {description}\n\n"

    if setting_type == "image":
        text += "📷 <b>Текущее изображение:</b>\n"
        text += f"<code>{current_value}</code>\n\n"
        text += "📤 Отправьте новое изображение (фото или ссылку):"

    elif setting_type == "template":
        text += "🎨 <b>Текущий шаблон:</b>\n"
        text += f"<blockquote>{current_value}</blockquote>\n\n"
        text += "📝 Отправьте новый шаблон:"

        if "deleted" in setting_key:
            text += "\n\n💡 <b>Доступные плейсхолдеры:</b>\n"
            text += "<code>{sender}</code> — отправитель\n<code>{time}</code> — время"
        elif "edited" in setting_key:
            text += "\n\n💡 <b>Доступные плейсхолдеры:</b>\n"
            text += "<code>{sender}</code> — отправитель\n<code>{time}</code> — время\n"
            text += "<code>{old_content}</code> — старый текст\n<code>{new_content}</code> — новый текст\n"
            text += "<code>{chat}</code> — название чата"

    else:
        text += "📝 <b>Текущее значение:</b>\n"
        text += f"<blockquote>{current_value}</blockquote>\n\n"
        text += "📤 Отправьте новое значение:"

    edit_txt(chat_id, msg_id, text, markup={"inline_keyboard": [
        [{"text": "❌ Отмена", "callback_data": "cancel_edit"}]
    ]})

def handle_preview_setting(chat_id, user_id, setting_key):
    """Предпросмотр настройки с тестовыми данными"""
    state = get_admin_state(user_id)
    if not state or state.get("action") != "design_edit":
        return

    temp_value = state.get("temp_value", "")
    setting_type = get_setting_type(setting_key)

    if setting_type == "template":
        # Тестовые данные для предпросмотра
        test_data = {
            "sender": "Иван Иванов (@ivan)",
            "time": format_time(),
            "content": "Тестовое сообщение для примера",
            "old_content": "Старый текст сообщения",
            "new_content": "Новый текст сообщения",
            "chat": "Тестовый чат",
            "bot_name": get_custom_setting('bot_name')
        }

        preview_text = format_template(temp_value, **test_data)

        send_msg(chat_id,
            f"👀 <b>Предпросмотр шаблона:</b>\n\n{preview_text}\n\n"
            f"<i>Это пример того, как будет выглядеть сообщение</i>")

    elif setting_type == "image":
        if temp_value.startswith("http"):
            send_photo_msg(chat_id, temp_value, caption="👀 <b>Предпросмотр изображения</b>")
        else:
            send_msg(chat_id, f"👀 <b>Предпросмотр:</b>\nFile ID: <code>{temp_value}</code>")

    else:
        send_msg(chat_id, f"👀 <b>Предпросмотр:</b>\n<blockquote>{temp_value}</blockquote>")

def handle_save_setting(chat_id, user_id, setting_key):
    """Сохранение настройки"""
    state = get_admin_state(user_id)
    if not state or state.get("action") != "design_edit":
        return

    temp_value = state.get("temp_value", "")
    if temp_value:
        set_custom_setting(setting_key, temp_value)

    # Возвращаемся к главному меню дизайна
    msg_id = state.get("original_msg_id")
    if msg_id:
        edit_txt(chat_id, msg_id,
            "🎨 <b>Дизайн-панель бота</b>\n\nВыберите раздел для настройки:",
            markup=kb_design_main())

    clear_admin_state(user_id)

def reset_design_settings():
    """Сброс всех настроек дизайна к дефолтным"""
    with get_db() as conn:
        conn.execute("DELETE FROM bot_customization")
        conn.commit()
    init_default_design()

def apply_color_scheme(scheme):
    """Применяет предустановленную цветовую схему"""
    if scheme == "green":
        style = "success"
        emoji_success = "🟢"
        emoji_danger = "🔴"
    elif scheme == "red":
        style = "danger"
        emoji_success = "🔴"
        emoji_danger = "⚫"
    elif scheme == "blue":
        style = "primary"
        emoji_success = "🔵"
        emoji_danger = "⚪"
    elif scheme == "clear":
        # Очищаем все стили
        for btn_type in ["edits", "deletes", "blur", "on", "off", "copy", "instruction", "back"]:
            set_custom_setting(f'btn_{btn_type}_style', '')
        set_custom_setting('emoji_success', '✅')
        set_custom_setting('emoji_danger', '❌')
        return
    else:
        return

    # Применяем стиль ко всем кнопкам
    for btn_type in ["edits", "deletes", "blur", "on", "off", "copy", "instruction", "back"]:
        set_custom_setting(f'btn_{btn_type}_style', style)

    # Обновляем эмодзи (НЕ автоматически меняем эмодзи по цвету как просил пользователь)
    # set_custom_setting('emoji_success', emoji_success)
    # set_custom_setting('emoji_danger', emoji_danger)

def preview_button_styles(chat_id, user_id):
    """Показывает предпросмотр всех стилей кнопок"""
    success_emoji = get_custom_setting('emoji_success', '✅')
    danger_emoji = get_custom_setting('emoji_danger', '❌')

    send_msg(chat_id,
        "👀 <b>Предпросмотр стилей кнопок</b>\n\n"
        f"✨ Эмодзи успеха: {success_emoji}\n"
        f"❌ Эмодзи ошибки: {danger_emoji}\n\n"
        f"💡 Нажмите на кнопки ниже, чтобы увидеть стили в действии:",
        markup=create_demo_settings_keyboard(user_id))

def handle_design_message(chat_id, user_id, msg):
    """Обработка сообщений в режиме редактирования дизайна"""
    state = get_admin_state(user_id)

    print(f"[DESIGN MSG] user={user_id}, state={state}")  # DEBUG

    # Обработка генератора Premium эмодзи
    if state and state.get("action") == "awaiting_emoji_id":
        text = msg.get("text", "").strip()

        if text.startswith("/"):
            send_msg(chat_id, "⚠️ Режим генератора эмодзи. Отправьте ID эмодзи или вернитесь в /design")
            return True

        # РАЗРЕШАЕМ КОМАНДЫ ОТМЕНЫ
        if text in ["/cancel", "/stop", "/design"]:
            clear_admin_state(user_id)
            send_msg(chat_id,
                "❌ <b>Генератор эмодзи отменён</b>\n\n"
                "Используйте /design для возврата в дизайн-панель")
            return True

        # Проверяем что это число (ID эмодзи)
        if text.isdigit() and len(text) > 10:
            emoji_id = text
            # Генерируем готовый тег
            emoji_tag = f'<tg-emoji emoji-id="{emoji_id}">😀</tg-emoji>'

            send_msg(chat_id,
                f"✅ <b>Готовый тег Premium эмодзи:</b>\n\n"
                f"<code>{emoji_tag}</code>\n\n"
                f"📋 <b>Как использовать:</b>\n"
                f"1. Скопируйте код выше\n"
                f"2. Замените 😀 на нужную эмодзи\n"
                f"3. Вставьте в любой шаблон в /design\n\n"
                f"💡 <b>Пример:</b>\n"
                f"<code>&lt;tg-emoji emoji-id=\"{emoji_id}\"&gt;🔥&lt;/tg-emoji&gt;</code>\n\n"
                f"⚠️ Работает только с Telegram Premium")

            # Очищаем состояние
            clear_admin_state(user_id)
            return True
        else:
            send_msg(chat_id,
                "❌ <b>Неверный формат ID</b>\n\n"
                "ID эмодзи должен быть числом (например: 5465665476357570821)\n\n"
                "Попробуйте ещё раз или используйте /cancel для отмены")
            return True

    # Обычная обработка редактирования дизайна
    if not state or state.get("action") != "design_edit":
        return False

    setting_key = state.get("setting_key")
    if not setting_key:
        return False

    # Проверяем команды
    text = msg.get("text", "")

    # РАЗРЕШАЕМ КОМАНДЫ ОТМЕНЫ
    if text in ["/cancel", "/stop", "/design"]:
        clear_admin_state(user_id)
        send_msg(chat_id,
            "❌ <b>Редактирование отменено</b>\n\n"
            "Используйте /design для возврата в дизайн-панель")
        return True

    # Блокируем остальные команды
    if text.startswith("/"):
        send_msg(chat_id,
            "⚠️ <b>Режим редактирования дизайна</b>\n\n"
            "Отправьте новое значение или используйте /cancel для отмены")
        return True

    # Получаем новое значение из сообщения
    new_value = None

    if "photo" in msg:
        # Если отправили фото
        photos = msg["photo"]
        if photos:
            new_value = photos[-1]["file_id"]
    elif "text" in msg:
        # Если отправили текст
        new_value = msg["text"]

    if new_value:
        print(f"[DESIGN MSG] Got new value, length={len(str(new_value))}")  # DEBUG

        # Сохраняем временное значение для предпросмотра
        state["temp_value"] = new_value
        set_admin_state(user_id, state)

        print(f"[DESIGN MSG] State saved, sending confirmation...")  # DEBUG

        # Сокращаем длинный текст для отображения
        display_value = str(new_value)
        if len(display_value) > 200:
            display_value = display_value[:200] + "..."

        # Показываем меню с предпросмотром
        result = send_msg(chat_id,
            f"✅ <b>Новое значение получено!</b>\n\n"
            f"🔧 <b>Настройка:</b> {get_setting_description(setting_key)}\n\n"
            f"📝 <b>Предпросмотр:</b>\n"
            f"<blockquote>{display_value}</blockquote>\n\n"
            f"💡 Нажмите '💾 Сохранить' или /cancel для отмены",
            markup=kb_design_preview(setting_key))

        print(f"[DESIGN MSG] Message sent, result={result.get('ok') if result else 'None'}")  # DEBUG

        return True

    return False

# ===== ЭКСПОРТ ЧАТА =====
def handle_chat_export(chat_id, user_id, query):
    """Экспорт истории чата с пользователем в файл — без обрезаний"""
    query = query.strip().lstrip("@")

    # Сначала находим chat_id по запросу
    with get_db() as conn:
        first_row = conn.execute("""
            SELECT chat_id FROM messages
            WHERE owner_id=? AND (chat_name LIKE ? OR sender_name LIKE ? OR CAST(chat_id AS TEXT) = ?)
            LIMIT 1
        """, (user_id, f"%{query}%", f"%{query}%", query)).fetchone()

        if not first_row:
            send_msg(chat_id, f"❌ История чата с <b>{query}</b> не найдена.")
            return

        target_chat_id = first_row["chat_id"]
        total_count = conn.execute("""
            SELECT COUNT(*) FROM messages WHERE owner_id=? AND chat_id=?
        """, (user_id, target_chat_id)).fetchone()[0]

        if total_count == 0:
            send_msg(chat_id, f"❌ История чата с <b>{query}</b> не найдена.")
            return

        chat_name_export = conn.execute("""
            SELECT chat_name FROM messages WHERE owner_id=? AND chat_id=? LIMIT 1
        """, (user_id, target_chat_id)).fetchone()["chat_name"] or query

    send_msg(chat_id,
        f"📤 <b>Экспорт чата</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💬 Чат: <b>{chat_name_export}</b>\n"
        f"🆔 ID: <code>{target_chat_id or 'неизвестно'}</code>\n"
        f"📊 Сообщений: <b>{total_count}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⏳ Формирую файл, подождите...")

    # Формируем файл батчами по 5000 — не держим всё в памяти сразу
    filename = f"chat_{query}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    buf = io.BytesIO()

    header = (
        f"═══════════════════════════════════════\n"
        f"История чата: {chat_name_export}\n"
        f"ID чата: {target_chat_id or 'неизвестно'}\n"
        f"Экспортировано: {format_time()}\n"
        f"Всего сообщений: {total_count}\n"
        f"═══════════════════════════════════════\n\n"
    )
    buf.write(header.encode('utf-8'))

    BATCH = 5000
    offset = 0
    while True:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT sender_name, content, media_type, file_id, timestamp, deleted
                FROM messages WHERE owner_id=? AND chat_id=?
                ORDER BY timestamp ASC
                LIMIT ? OFFSET ?
            """, (user_id, target_chat_id, BATCH, offset)).fetchall()

        if not rows:
            break

        for r in rows:
            ts = (r["timestamp"] or "")[:16].replace("T", " ")
            sender = r["sender_name"] or "Неизвестный"
            content = r["content"] or ""
            media_type = r["media_type"]
            deleted_mark = " 🗑[УДАЛЕНО]" if r["deleted"] else ""

            if media_type and not content:
                content = f"[{media_type}]"

            line = f"[{ts}] {sender}:\n  {content}{deleted_mark}\n"
            if media_type and r["file_id"]:
                line += f"  📎 {media_type} (file_id: {r['file_id'][:30]}...)\n"
            line += "\n"
            buf.write(line.encode('utf-8'))

        offset += BATCH

    buf.seek(0)

    # Отправляем с большим таймаутом чтобы большой файл не обрывался
    for attempt in range(3):
        try:
            files = {"document": (filename, buf)}
            data = {
                "chat_id": chat_id,
                "caption": f"📄 <b>История чата с {chat_name_export}</b>\n🆔 ID: <code>{target_chat_id or 'неизвестно'}</code>\n📊 Сообщений: {total_count}",
                "parse_mode": "HTML"
            }
            r = requests.post(f"{API_URL}sendDocument", files=files, data=data, timeout=120)
            if r.status_code == 200 and r.json().get("ok"):
                break
            else:
                print(f"[CHAT EXPORT] attempt {attempt+1} failed: {r.text[:200]}")
                buf.seek(0)
        except Exception as e:
            print(f"[CHAT EXPORT] attempt {attempt+1} exception: {e}")
            buf.seek(0)
            import time
            time.sleep(3)

# ===== ОБРАБОТЧИКИ =====
def on_start(chat_id, user_id, username, first_name):
    register_user(user_id, username, first_name)
    get_settings(user_id)

    start_image = get_custom_setting('start_image')
    start_text = get_custom_setting('start_text')
    bot_name = get_custom_setting('bot_name')

    formatted_text = format_template(start_text, bot_name=bot_name)

    send_photo_msg(chat_id, start_image,
        caption=formatted_text,
        markup=kb_start())

def on_settings(chat_id, user_id):
    settings_image = get_custom_setting('settings_image')
    settings_title = get_custom_setting('settings_title', '⚙️ Настройки')
    settings_desc = get_custom_setting('settings_description', 'Выберите параметр для изменения:')

    send_photo_msg(chat_id, settings_image,
        caption=f"<b>{settings_title}</b>\n\n{settings_desc}",
        markup=kb_settings(user_id))

def create_demo_settings_keyboard(user_id):
    """Создает демо-клавиатуру настроек с примерами стилей"""
    s = get_settings(user_id)

    success_emoji = get_custom_setting('emoji_success', '✅')
    danger_emoji = get_custom_setting('emoji_danger', '❌')

    return {"inline_keyboard": [
        [{"text": f"{success_emoji} Включенная настройка", "callback_data": "demo_on"}],
        [{"text": f"{danger_emoji} Выключенная настройка", "callback_data": "demo_off"}],
        [{"text": "🔵 Основной стиль", "callback_data": "demo_primary"}],
        [{"text": "⚫ Вторичный стиль", "callback_data": "demo_secondary"}],
        [{"text": "‹ Назад к стилям", "callback_data": "design_styles"}]
    ]}

def on_callback(cb):
    try:
        cb_id = cb["id"]
        data = cb["data"]
        user_id = cb["from"]["id"]
        chat_id = cb["message"]["chat"]["id"]
        msg_id = cb["message"]["message_id"]
        has_photo = "photo" in cb["message"]

        # СУПЕР ОТЛАДКА - ЛОГИРУЕМ ВСЕ КОЛЛБЭКИ
        print(f"[CALLBACK DEBUG] data='{data}', user_id={user_id}, is_admin={is_admin(user_id)}")

        def edit(text, markup):
            if has_photo:
                edit_cap(chat_id, msg_id, text, markup=markup)
            else:
                edit_txt(chat_id, msg_id, text, markup=markup)

        # Обработка дизайн-панели
        if (data.startswith("design_") or data.startswith("edit_") or data.startswith("preview_") or
            data.startswith("save_") or data.startswith("delete_") or data.startswith("fmt_") or
            data.startswith("html_") or  # НОВЫЕ HTML КОЛЛБЭКИ
            data.startswith("interface_") or data.startswith("scheme_") or data.startswith("demo_") or
            data.startswith("toggle_cmd_") or data.startswith("style_") or data.startswith("set_btn_color_") or
            data.startswith("apply_color_") or
            data == "confirm_reset" or data == "cancel_edit" or data == "format_helper" or
            data == "format_examples" or data == "preview_demo" or data == "emoji_helper" or
            data == "design_formats" or data == "html_generator" or data == "html_examples" or
            data == "emoji_generator" or data.startswith("html_") or
            data == "design_buttons" or data.startswith("buttons_")):
            print(f"[ROUTING DEBUG] Sending to handle_design_callback: {data}")
            handle_design_callback(cb)
            return
    except Exception as e:
        print(f"[CALLBACK ERROR] Error in on_callback: {e}")
        import traceback
        traceback.print_exc()
        return

    if data == "copy_username":
        bot_name = get_custom_setting('bot_name')
        answer_cb(cb_id, f"Скопируйте: {bot_name}", alert=True)

    elif data == "skip_notification":
        # Удаляем сообщение с уведомлением
        try:
            api("deleteMessage", chat_id=chat_id, message_id=msg_id)
            answer_cb(cb_id, "🗑 Уведомление удалено", alert=False)
        except:
            answer_cb(cb_id, "❌ Не удалось удалить", alert=True)
        return

    elif data == "back_start":
        answer_cb(cb_id)
        start_text = get_custom_setting('start_text')
        bot_name = get_custom_setting('bot_name')
        formatted_text = format_template(start_text, bot_name=bot_name)
        edit(formatted_text, kb_start())

    elif data == "back_settings":
        settings_title = get_custom_setting('settings_title')
        settings_desc = get_custom_setting('settings_description')
        edit(f"{settings_title}\n\n{settings_desc}", kb_settings(user_id))
        answer_cb(cb_id)

    elif data.startswith("s_"):
        stype = data[2:]
        s = get_settings(user_id)
        key = SETTING_KEYS.get(stype)
        if key:
            edit(get_setting_text(stype), kb_detail(stype, s[key]))
            answer_cb(cb_id)

    elif data.startswith("on_"):
        stype = data[3:]
        key = SETTING_KEYS.get(stype)
        if key:
            set_setting(user_id, key, 1)
            edit(get_setting_text(stype), kb_detail(stype, 1))
            answer_cb(cb_id, get_custom_setting('msg_enabled', '✅ Включено'), alert=True)

    elif data.startswith("off_"):
        stype = data[4:]
        key = SETTING_KEYS.get(stype)
        if key:
            set_setting(user_id, key, 0)
            edit(get_setting_text(stype), kb_detail(stype, 0))
            answer_cb(cb_id, get_custom_setting('msg_disabled', '❌ Выключено'), alert=True)

    elif data.startswith("user_profile_"):
        # Обработка просмотра профиля пользователя
        if not is_admin(user_id):
            answer_cb(cb_id, "⛔ Нет доступа", alert=True)
            return

        target_user_id = int(data.split("_")[2])

        with get_db() as conn:
            row = conn.execute("""
                SELECT u.*, COUNT(DISTINCT c.connection_id) as connected,
                       COUNT(DISTINCT m.id) as msg_count,
                       SUM(CASE WHEN m.deleted=1 THEN 1 ELSE 0 END) as del_count,
                       COUNT(DISTINCT e.id) as edit_count
                FROM users u
                LEFT JOIN connections c ON u.user_id = c.user_id
                LEFT JOIN messages m ON u.user_id = m.owner_id
                LEFT JOIN edits e ON u.user_id = e.owner_id
                WHERE u.user_id = ?
                GROUP BY u.user_id
            """, (target_user_id,)).fetchone()

            if not row:
                answer_cb(cb_id, "❌ Пользователь не найден", alert=True)
                return

            # Формируем текст профиля
            name = row["first_name"] or "Без имени"
            uname = f"@{row['username']}" if row["username"] else "нет"

            profile_text = f"👤 <b>Профиль пользователя</b>\n\n"
            profile_text += f"<b>Имя:</b> {name}\n"
            profile_text += f"<b>Username:</b> {uname}\n"
            profile_text += f"<b>ID:</b> <code>{row['user_id']}</code>\n"
            profile_text += f"<b>Зарегистрирован:</b> {row['joined_at'][:10] if row['joined_at'] else 'неизвестно'}\n\n"

            profile_text += f"📊 <b>Статистика:</b>\n"
            profile_text += f"• Сообщений: {row['msg_count'] or 0}\n"
            profile_text += f"• Удалено: {row['del_count'] or 0}\n"
            profile_text += f"• Редактировано: {row['edit_count'] or 0}\n\n"

            profile_text += f"🔧 <b>Статус:</b>\n"
            profile_text += f"• Подключен: {'✅ Да' if row['connected'] else '❌ Нет'}\n"
            profile_text += f"• Забанен: {'🚫 Да' if row['is_banned'] else '✅ Нет'}\n"
            profile_text += f"• Заглушен: {'🔇 Да' if row['is_muted'] else '✅ Нет'}\n"

            # Кнопки действий
            action_buttons = []

            # Кнопка бана/разбана
            if row['is_banned']:
                action_buttons.append([{"text": "✅ Разбанить", "callback_data": f"unban_{target_user_id}"}])
            else:
                action_buttons.append([{"text": "🚫 Забанить", "callback_data": f"ban_{target_user_id}"}])

            # Кнопка мута/размута
            if row['is_muted']:
                action_buttons.append([{"text": "🔊 Размутить", "callback_data": f"unmute_{target_user_id}"}])
            else:
                action_buttons.append([{"text": "🔇 Замутить", "callback_data": f"mute_{target_user_id}"}])

            # Кнопка "Назад к списку"
            action_buttons.append([{"text": "‹ К списку", "callback_data": "back_to_users"}])

            markup = {"inline_keyboard": action_buttons}
            edit_txt(chat_id, msg_id, profile_text, markup=markup)
            answer_cb(cb_id)

    elif data.startswith("ban_"):
        # Забанить пользователя
        if not is_admin(user_id):
            answer_cb(cb_id, "⛔ Нет доступа", alert=True)
            return

        target_user_id = int(data.split("_")[1])
        with get_db() as conn:
            conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (target_user_id,))
            conn.commit()

        answer_cb(cb_id, "🚫 Пользователь забанен", alert=True)
        # Перезагружаем профиль
        on_callback({"id": cb_id, "data": f"user_profile_{target_user_id}", "from": cb["from"], "message": cb["message"]})

    elif data.startswith("unban_"):
        # Разбанить пользователя
        if not is_admin(user_id):
            answer_cb(cb_id, "⛔ Нет доступа", alert=True)
            return

        target_user_id = int(data.split("_")[1])
        with get_db() as conn:
            conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (target_user_id,))
            conn.commit()

        answer_cb(cb_id, "✅ Пользователь разбанен", alert=True)
        # Перезагружаем профиль
        on_callback({"id": cb_id, "data": f"user_profile_{target_user_id}", "from": cb["from"], "message": cb["message"]})

    elif data.startswith("mute_"):
        # Замутить пользователя
        if not is_admin(user_id):
            answer_cb(cb_id, "⛔ Нет доступа", alert=True)
            return

        target_user_id = int(data.split("_")[1])
        with get_db() as conn:
            conn.execute("UPDATE users SET is_muted=1 WHERE user_id=?", (target_user_id,))
            conn.commit()

        answer_cb(cb_id, "🔇 Пользователь заглушен", alert=True)
        # Перезагружаем профиль
        on_callback({"id": cb_id, "data": f"user_profile_{target_user_id}", "from": cb["from"], "message": cb["message"]})

    elif data.startswith("unmute_"):
        # Размутить пользователя
        if not is_admin(user_id):
            answer_cb(cb_id, "⛔ Нет доступа", alert=True)
            return

        target_user_id = int(data.split("_")[1])
        with get_db() as conn:
            conn.execute("UPDATE users SET is_muted=0 WHERE user_id=?", (target_user_id,))
            conn.commit()

        answer_cb(cb_id, "🔊 Пользователь размучен", alert=True)
        # Перезагружаем профиль
        on_callback({"id": cb_id, "data": f"user_profile_{target_user_id}", "from": cb["from"], "message": cb["message"]})

    elif data == "back_to_users":
        # Возврат к списку пользователей
        if not is_admin(user_id):
            answer_cb(cb_id, "⛔ Нет доступа", alert=True)
            return

        handle_users_command(chat_id, user_id)
        answer_cb(cb_id)

def on_business_connection(bc):
    user = bc["user"]
    user_id = user["id"]
    enabled = bc.get("is_enabled", True)

    register_user(user_id, user.get("username"), user.get("first_name"))
    get_settings(user_id)

    with get_db() as conn:
        if enabled:
            conn.execute("INSERT OR REPLACE INTO connections VALUES (?,?)", (bc["id"], user_id))
            conn.commit()

            welcome_image = get_custom_setting('welcome_image')
            welcome_text = get_custom_setting('welcome_text')

            send_photo_msg(user_id, welcome_image, caption=welcome_text)
        else:
            conn.execute("DELETE FROM connections WHERE connection_id=?", (bc["id"],))
            conn.commit()

            # Текст и кнопка при отключении
            disconnect_text = get_custom_setting('disconnect_text',
                '<tg-emoji emoji-id="6037496202990194718">🔥</tg-emoji> <b>Бот был отключён.</b>\n\n'
                'Если это произошло случайно, вы можете подключить бота повторно. '
                'Будьте осторожны и остерегайтесь других ботов, которые могут оказаться предназначены для мошенничества с вашим аккаунтом.')

            disconnect_button = {
                "inline_keyboard": [[
                    {"text": "Как подключить?", "url": "https://t.me/SU1C1D3X/12"}
                ]]
            }

            send_msg(user_id, disconnect_text, markup=disconnect_button)

def on_business_message(msg, owner_id):
    """Сохраняем входящее сообщение в БД"""
    try:
        # Проверка белого списка
        if not check_whitelist(owner_id):
            if owner_id not in whitelist_notified:
                whitelist_notified.add(owner_id)
                send_msg(owner_id, "🔒 Включен белый список/технические работы. Вернитесь позже.")
            return

        # Если владелец пишет сам себе — обрабатываем как команду
        sender_id = (msg.get("from") or {}).get("id", 0)
        if sender_id == owner_id:
            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id", owner_id)
            if text.startswith("/"):
                on_message(msg)
                return

            if get_admin_state(owner_id) is not None:
                # Проверяем, если это режим дизайна
                state = get_admin_state(owner_id)
                if state and state.get("action") == "design_edit":
                    if handle_design_message(chat_id, owner_id, msg):
                        return
                else:
                    handle_admin_confirm(chat_id, owner_id, text)
                    return

        media_type, file_id, content = parse_media(msg)
        sender_name, sender_id = get_sender(msg)
        chat_name = get_chat_name(msg)
        msg_id = msg["message_id"]
        chat_id = msg.get("chat", {}).get("id", 0)

        with get_db() as conn:
            conn.execute("""INSERT OR REPLACE INTO messages(
                message_id, owner_id, sender_id, sender_name, chat_id, chat_name,
                content, media_type, file_id, timestamp, deleted, edited, edit_count
            ) VALUES (?,?,?,?,?,?,?,?,?,?,0,0,0)""",
                (msg_id, owner_id, sender_id, sender_name, chat_id, chat_name,
                 content or "", media_type, file_id, datetime.now().isoformat()))
            conn.commit()

    except Exception as e:
        print(f"[on_business_message] {e}")

def on_edited_business_message(msg, owner_id):
    """Сохраняем редактирование и уведомляем владельца"""
    try:
        media_type, file_id, new_content = parse_media(msg)
        sender_name, sender_id = get_sender(msg)
        chat_name = get_chat_name(msg)
        msg_id = msg["message_id"]
        chat_id = msg.get("chat", {}).get("id", 0)

        with get_db() as conn:
            row = conn.execute("SELECT * FROM messages WHERE message_id=? AND owner_id=? AND chat_id=?",
                (msg_id, owner_id, chat_id)).fetchone()

            if row:
                old_content = row["content"]
                new_count = row["edit_count"] + 1

                conn.execute("""INSERT INTO edits(
                    message_id, owner_id, chat_id, sender_name, chat_name,
                    old_content, new_content, media_type, file_id, edited_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (msg_id, owner_id, chat_id, sender_name, chat_name,
                     old_content, new_content, media_type, file_id, datetime.now().isoformat()))

                conn.execute("""UPDATE messages SET content=?, media_type=?, file_id=?,
                    edited=1, edit_count=? WHERE message_id=? AND owner_id=? AND chat_id=?""",
                    (new_content, media_type, file_id, new_count, msg_id, owner_id, chat_id))

                conn.commit()

                s = get_settings(owner_id)
                if s["notify_edits"] and not is_muted(owner_id):
                    notify_edited(owner_id, dict(row), old_content, new_content, new_count)
            else:
                # Сообщение ещё не сохранено - НЕ отправляем быстрое редактирование
                conn.execute("""INSERT OR REPLACE INTO messages(
                    message_id, owner_id, sender_id, sender_name, chat_id, chat_name,
                    content, media_type, file_id, timestamp, deleted, edited, edit_count
                ) VALUES (?,?,?,?,?,?,?,?,?,?,0,1,1)""",
                    (msg_id, owner_id, sender_id, sender_name, chat_id, chat_name,
                     new_content or "", media_type, file_id, datetime.now().isoformat()))

                conn.commit()

    except Exception as e:
        print(f"[on_edited_business_message] {e}")

def on_deleted_business_messages(dbd):
    """Получаем удалённые сообщения и уведомляем владельца"""
    bc_id = dbd.get("business_connection_id")
    owner_id = get_owner(bc_id)
    if not owner_id:
        return

    for msg_id in dbd.get("message_ids", []):
        try:
            with get_db() as conn:
                rows = conn.execute("SELECT * FROM messages WHERE message_id=? AND owner_id=? AND deleted=0",
                    (msg_id, owner_id)).fetchall()

                for row in rows:
                    conn.execute("UPDATE messages SET deleted=1 WHERE message_id=? AND owner_id=? AND chat_id=?",
                        (msg_id, owner_id, row["chat_id"]))
                    conn.commit()

                    s = get_settings(owner_id)
                    if s["notify_deletes"] and not is_muted(owner_id):
                        notify_deleted(owner_id, dict(row))

        except Exception as e:
            print(f"[on_deleted] msg_id={msg_id} error: {e}")

# ===== АДМИН ПАНЕЛЬ =====
admin_states = {}

def get_admin_state(user_id):
    if user_id in admin_states:
        return admin_states[user_id]

    with get_db() as conn:
        row = conn.execute("SELECT action, data FROM admin_states_db WHERE user_id=?", (user_id,)).fetchone()
        if row:
            import json
            state = {"action": row["action"]}
            if row["data"]:
                state.update(json.loads(row["data"]))
            admin_states[user_id] = state
            return state
    return None

def set_admin_state(user_id, state):
    import json
    admin_states[user_id] = state
    data = json.dumps({k: v for k, v in state.items() if k != "action"})

    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO admin_states_db (user_id, action, data) VALUES (?,?,?)",
            (user_id, state.get("action"), data))
        conn.commit()

def clear_admin_state(user_id):
    admin_states.pop(user_id, None)
    with get_db() as conn:
        conn.execute("DELETE FROM admin_states_db WHERE user_id=?", (user_id,))
        conn.commit()

def is_admin(user_id):
    return user_id == ADMIN_ID

def handle_plus_command(chat_id, user_id):
    """Обработчик команды /plus - показывает статус подписки"""
    plus_info = get_plus_info(user_id)

    if plus_info:
        # У пользователя есть подписка
        from datetime import datetime
        expires_at = datetime.fromisoformat(plus_info['expires_at'])
        activated_at = datetime.fromisoformat(plus_info['activated_at'])

        # Проверяем активна ли подписка
        if expires_at > datetime.now():
            days_left = (expires_at - datetime.now()).days
            send_msg(chat_id,
                f"✨ <b>Telegram Plus подписка</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📊 Статус: <b>✅ Активна</b>\n"
                f"📅 Активирована: <b>{activated_at.strftime('%d.%m.%Y')}</b>\n"
                f"⏰ Действует до: <b>{expires_at.strftime('%d.%m.%Y %H:%M')}</b>\n"
                f"⏳ Осталось дней: <b>{days_left}</b>\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"🎁 <b>Преимущества Plus:</b>\n"
                f"• 📊 Расширенная статистика\n"
                f"• ⚡ Приоритетная обработка\n"
                f"• 🎨 Индивидуальные шаблоны\n"
                f"• 🔔 Дополнительные уведомления\n"
                f"• 💎 Эксклюзивные функции\n\n"
                f"💬 По вопросам продления свяжитесь с администратором")
        else:
            send_msg(chat_id,
                f"❌ <b>Подписка Plus истекла</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📅 Была активна до: <b>{expires_at.strftime('%d.%m.%Y')}</b>\n\n"
                f"💬 Для продления свяжитесь с администратором")
    else:
        # У пользователя нет подписки
        send_msg(chat_id,
            f"✨ <b>Telegram Plus подписка</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 Статус: <b>❌ Не активна</b>\n\n"
            f"🎁 <b>Преимущества Plus:</b>\n"
            f"• 📊 Расширенная статистика\n"
            f"• ⚡ Приоритетная обработка сообщений\n"
            f"• 🎨 Индивидуальные шаблоны для каждого чата\n"
            f"• 🔔 Дополнительные уведомления\n"
            f"• 💎 Эксклюзивные функции бота\n"
            f"• 🚀 Без ограничений\n\n"
            f"💰 <b>Стоимость:</b> уточняйте у администратора\n"
            f"💬 <b>Купить:</b> свяжитесь с администратором")

def handle_admin_command(chat_id, user_id):
    print(f"[ADMIN] called by {user_id}, is_admin={is_admin(user_id)}", flush=True)
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    with get_db() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        connected = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]
        total_del = conn.execute("SELECT COUNT(*) FROM messages WHERE deleted=1").fetchone()[0]
        total_edit = conn.execute("SELECT COUNT(*) FROM edits").fetchone()[0]
        total_msg = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        banned = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0]
        muted = conn.execute("SELECT COUNT(*) FROM users WHERE is_muted=1").fetchone()[0]

        # Plus подписки
        plus_total = conn.execute("SELECT COUNT(*) FROM plus_subscriptions").fetchone()[0]
        plus_active = conn.execute("""
            SELECT COUNT(*) FROM plus_subscriptions
            WHERE expires_at > ?
        """, (datetime.now().isoformat(),)).fetchone()[0]

    send_msg(chat_id,
        f"👑 <b>Админ-панель</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"🔗 Подключено: <b>{connected}</b>\n"
        f"💾 Сообщений в БД: <b>{total_msg}</b>\n"
        f"🗑 Удалений поймано: <b>{total_del}</b>\n"
        f"✏️ Редактирований: <b>{total_edit}</b>\n"
        f"🚫 Забанено: <b>{banned}</b>\n"
        f"🔇 Замьючено: <b>{muted}</b>\n"
        f"✨ Plus подписок: <b>{plus_active}/{plus_total}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<b>Команды:</b>\n"
        f"/users — список пользователей\n"
        f"/design — дизайн-панель бота\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👥 <b>Пользователи:</b>\n"
        f"/users — список пользователей\n"
        f"/find ID или @username — найти юзера\n"
        f"/info ID — инфо о юзере\n"
        f"/msg ID текст — написать юзеру\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👁 <b>Слежка:</b>\n"
        f"/spy ID — удалённые юзера\n"
        f"/media ID — медиафайлы юзера\n"
        f"/getfile file_id — получить файл по ID\n"
        f"/spyedits ID — редактирования юзера\n"
        f"/spystats ID — статистика юзера\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🚫 <b>Управление:</b>\n"
        f"/ban ID — забанить\n"
        f"/unban ID — разбанить\n"
        f"/mute ID — замьютить\n"
        f"/unmute ID — размьютить\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✨ <b>Plus подписки:</b>\n"
        f"/plusadd ID дни — добавить подписку\n"
        f"/plusremove ID — удалить подписку\n"
        f"/pluslist — список подписчиков\n"
        f"/pluscheck ID — проверить подписку\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 <b>Рассылка:</b>\n"
        f"/broadcast — рассылка всем\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📋 <b>Белый список:</b>\n"
        f"/whitelist — вкл/выкл белый список\n"
        f"/wladd ID — добавить в список\n"
        f"/wlremove ID — убрать из списка\n"
        f"/wllist — показать список")

def handle_users_command(chat_id, user_id):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    with get_db() as conn:
        rows = conn.execute("""
            SELECT u.user_id, u.username, u.first_name, u.is_banned, u.is_muted,
                   COUNT(c.connection_id) as connected
            FROM users u
            LEFT JOIN connections c ON u.user_id = c.user_id
            GROUP BY u.user_id
            ORDER BY u.joined_at DESC
            LIMIT 50
        """).fetchall()

        if not rows:
            send_msg(chat_id, "👥 Пользователей нет.")
            return

        text = f"👥 <b>Список пользователей ({len(rows)}):</b>\n\nНажмите на пользователя для просмотра профиля:"

        # Создаем кнопки в столбик (по одной на строку)
        buttons = []
        for r in rows:
            name = r["first_name"] or "Без имени"
            uname = f"@{r['username']}" if r["username"] else ""

            # Иконки статусов
            icons = ""
            if r["connected"]: icons += "🔗 "
            if r["is_banned"]: icons += "🚫 "
            if r["is_muted"]: icons += "🔇 "

            # Текст кнопки
            button_text = f"{icons}{name}"
            if uname:
                button_text += f" {uname}"

            # Добавляем кнопку в отдельную строку
            buttons.append([{
                "text": button_text,
                "callback_data": f"user_profile_{r['user_id']}"
            }])

        markup = {"inline_keyboard": buttons}
        send_msg(chat_id, text, markup=markup)

def handle_find_command(chat_id, user_id, query):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    query = query.strip().lstrip("@")
    with get_db() as conn:
        row = conn.execute("""
            SELECT u.*, COUNT(c.connection_id) as connected,
                   COUNT(m.id) as msg_count,
                   SUM(CASE WHEN m.deleted=1 THEN 1 ELSE 0 END) as del_count
            FROM users u
            LEFT JOIN connections c ON u.user_id = c.user_id
            LEFT JOIN messages m ON u.user_id = m.owner_id
            WHERE CAST(u.user_id AS TEXT) = ? OR u.username = ?
            GROUP BY u.user_id
        """, (query, query)).fetchone()

        if not row:
            send_msg(chat_id, f"❌ Пользователь <code>{query}</code> не найден.")
            return

        name = row["first_name"] or "?"
        uname = f"@{row['username']}" if row["username"] else "нет"
        joined = (row["joined_at"] or "")[:10]

        send_msg(chat_id,
            f"🔍 <b>Пользователь найден</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 Имя: <b>{name}</b>\n"
            f"📛 Username: {uname}\n"
            f"🆔 ID: <code>{row['user_id']}</code>\n"
            f"📅 Регистрация: {joined}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔗 Подключён: {'✅' if row['connected'] else '❌'}\n"
            f"🚫 Бан: {'✅' if row['is_banned'] else '❌'}\n"
            f"🔇 Мьют: {'✅' if row['is_muted'] else '❌'}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💾 Сообщений: <b>{row['msg_count']}</b>\n"
            f"🗑 Удалений: <b>{row['del_count']}</b>")

def handle_ban_command(chat_id, user_id, target_id):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    set_admin_state(user_id, {"action": "ban", "target": target_id})
    with get_db() as conn:
        row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()
        name = row["first_name"] if row else "?"
        uname = f"@{row['username']}" if row and row["username"] else "нет"

    send_msg(chat_id,
        f"⚠️ <b>Подтверди бан</b>\n\n"
        f"👤 {name} ({uname})\n"
        f"🆔 <code>{target_id}</code>\n\n"
        f"Напиши <b>да</b> для подтверждения или <b>нет</b> для отмены.")

def handle_unban_command(chat_id, user_id, target_id):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    set_admin_state(user_id, {"action": "unban", "target": target_id})
    with get_db() as conn:
        row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()
        name = row["first_name"] if row else "?"
        uname = f"@{row['username']}" if row and row["username"] else "нет"

    send_msg(chat_id,
        f"⚠️ <b>Подтверди разбан</b>\n\n"
        f"👤 {name} ({uname})\n"
        f"🆔 <code>{target_id}</code>\n\n"
        f"Напиши <b>да</b> для подтверждения или <b>нет</b> для отмены.")

def handle_mute_command(chat_id, user_id, target_id):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    set_admin_state(user_id, {"action": "mute", "target": target_id})
    with get_db() as conn:
        row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()
        name = row["first_name"] if row else "?"
        uname = f"@{row['username']}" if row and row["username"] else "нет"

    send_msg(chat_id,
        f"⚠️ <b>Подтверди мьют</b>\n\n"
        f"👤 {name} ({uname})\n"
        f"🆔 <code>{target_id}</code>\n\n"
        f"Напиши <b>да</b> для подтверждения или <b>нет</b> для отмены.")

def handle_unmute_command(chat_id, user_id, target_id):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    set_admin_state(user_id, {"action": "unmute", "target": target_id})
    with get_db() as conn:
        row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()
        name = row["first_name"] if row else "?"
        uname = f"@{row['username']}" if row and row["username"] else "нет"

    send_msg(chat_id,
        f"⚠️ <b>Подтверди размьют</b>\n\n"
        f"👤 {name} ({uname})\n"
        f"🆔 <code>{target_id}</code>\n\n"
        f"Напиши <b>да</b> для подтверждения или <b>нет</b> для отмены.")

def handle_broadcast_command(chat_id, user_id):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    set_admin_state(user_id, {"action": "broadcast_text"})
    send_msg(chat_id, "📢 <b>Рассылка</b>\n\nВведи текст сообщения:")

def handle_admin_confirm(chat_id, user_id, text):
    state = get_admin_state(user_id) or {}
    if not state:
        return False

    action = state.get("action")

    # Обработка отмены для дизайн-панели
    if action == "design_edit" and text.lower() == "отмена":
        clear_admin_state(user_id)
        send_msg(chat_id, "❌ Редактирование отменено.")
        return True

    if text.lower() == "нет" and action not in ("whitelist_on_broadcast", "whitelist_off_broadcast"):
        clear_admin_state(user_id)
        send_msg(chat_id, "❌ Отменено.")
        return True

    if action == "broadcast_text":
        if text.lower() in ("да", "нет"):
            send_msg(chat_id, "❌ Введи текст рассылки:")
            return True
        set_admin_state(user_id, {"action": "broadcast_confirm", "text": text})
        with get_db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=0").fetchone()[0]
        send_msg(chat_id,
            f"📢 <b>Подтверди рассылку</b>\n\n"
            f"Текст:\n<blockquote>{text[:300]}</blockquote>\n\n"
            f"Получателей: <b>{count}</b>\n\n"
            f"Напиши <b>да</b> для отправки или <b>нет</b> для отмены.")
        return True

    if action == "broadcast_confirm":
        if text.lower() not in ("да", "нет", "да.", "нет."):
            send_msg(chat_id, "⚠️ Напиши <b>да</b> для отправки или <b>нет</b> для отмены.")
            return True
        if text.lower() == "да":
            broadcast_text = state.get("text", "")
            clear_admin_state(user_id)

            # Получаем всех незабаненных пользователей
            with get_db() as conn:
                users = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()

            send_msg(chat_id, f"📢 Начинаю рассылку для {len(users)} пользователей...")

            sent, failed = 0, 0
            errors = []

            # Отправляем каждому пользователю
            for u in users:
                try:
                    r = send_msg(u["user_id"], f"📢 <b>Сообщение от администратора:</b>\n\n{broadcast_text}")
                    if r and r.get("ok"):
                        sent += 1
                    else:
                        failed += 1
                        error_desc = r.get("description", "unknown") if r else "no response"
                        errors.append(f"User {u['user_id']}: {error_desc}")
                except Exception as e:
                    failed += 1
                    errors.append(f"User {u['user_id']}: {str(e)}")

            # Отправляем отчет админу
            report = f"📢 <b>Рассылка завершена</b>\n\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}"

            if errors and len(errors) <= 10:
                report += f"\n\n<b>Ошибки:</b>\n"
                for err in errors[:10]:
                    report += f"• {err}\n"
            elif errors:
                report += f"\n\n<b>Первые 10 ошибок:</b>\n"
                for err in errors[:10]:
                    report += f"• {err}\n"

            send_msg(chat_id, report)
        else:
            clear_admin_state(user_id)
            send_msg(chat_id, "❌ Рассылка отменена.")
        return True

    if action == "whitelist_on":
        if text.lower() == "да":
            set_admin_state(user_id, {"action": "whitelist_on_broadcast"})
            send_msg(chat_id,
                "📢 <b>Отправить рассылку всем пользователям или тихий режим?</b>\n\n"
                "Напиши <b>да</b> — отправить рассылку\n"
                "Напиши <b>нет</b> — тихий режим (без уведомлений)")
            return True

    if action == "whitelist_on_broadcast":
        set_whitelist_mode(True)
        whitelist_notified.clear()
        clear_admin_state(user_id)
        send_msg(chat_id, "✅ Белый список включён.")
        if text.lower() == "да":
            with get_db() as conn:
                users = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
            sent = 0
            whitelist_on_image = get_custom_setting('whitelist_on_image')
            whitelist_on_text = get_custom_setting('whitelist_on_text')
            for u in users:
                if u["user_id"] != ADMIN_ID:
                    r = send_photo_msg(u["user_id"], whitelist_on_image, caption=whitelist_on_text)
                    if r and r.get("ok"):
                        sent += 1
            send_msg(chat_id, f"📢 Рассылка отправлена: {sent} пользователей")
        else:
            send_msg(chat_id, "🔇 Тихий режим — пользователи не уведомлены.")
        return True

    if action == "whitelist_off":
        if text.lower() == "да":
            set_admin_state(user_id, {"action": "whitelist_off_broadcast"})
            send_msg(chat_id,
                "📢 <b>Отправить рассылку всем пользователям или тихий режим?</b>\n\n"
                "Напиши <b>да</b> — отправить рассылку\n"
                "Напиши <b>нет</b> — тихий режим (без уведомлений)")
            return True

    if action == "whitelist_off_broadcast":
        set_whitelist_mode(False)
        whitelist_notified.clear()
        clear_admin_state(user_id)
        send_msg(chat_id, "✅ Белый список выключен.")
        if text.lower() == "да":
            with get_db() as conn:
                users = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
            sent = 0
            whitelist_off_image = get_custom_setting('whitelist_off_image')
            whitelist_off_text = get_custom_setting('whitelist_off_text')
            for u in users:
                if u["user_id"] != ADMIN_ID:
                    r = send_photo_msg(u["user_id"], whitelist_off_image, caption=whitelist_off_text)
                    if r and r.get("ok"):
                        sent += 1
            send_msg(chat_id, f"📢 Рассылка отправлена: {sent} пользователей")
        else:
            send_msg(chat_id, "🔇 Тихий режим — пользователи не уведомлены.")
        return True

    if action == "wladd":
        if text.lower() == "да":
            target = state.get("target")
            clear_admin_state(user_id)
            whitelist_users.add(target)
            with get_db() as conn:
                conn.execute("INSERT OR IGNORE INTO whitelist (user_id) VALUES (?)", (target,))
                conn.commit()
            send_msg(chat_id, f"✅ <code>{target}</code> добавлен в белый список.")
            send_msg(target,
                "✅ <b>Вы добавлены в белый список.</b>\n\n"
                "При включении белого списка вы сможете пользоваться ботом как раньше.")
            return True

    if action == "wlremove":
        if text.lower() == "да":
            target = state.get("target")
            clear_admin_state(user_id)
            whitelist_users.discard(target)
            with get_db() as conn:
                conn.execute("DELETE FROM whitelist WHERE user_id=?", (target,))
                conn.commit()
            send_msg(chat_id, f"✅ <code>{target}</code> убран из белого списка.")
            send_msg(target,
                "⚠️ <b>Вы были отключены от белого списка.</b>\n\n"
                "Работа и функционал бота будет прекращена при включённом списке.")
            return True

    if action in ("ban", "unban", "mute", "unmute"):
        if text.lower() == "да":
            target = state.get("target")
            clear_admin_state(user_id)
            with get_db() as conn:
                if action == "ban":
                    conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (target,))
                    conn.commit()
                    send_msg(chat_id, f"🚫 <code>{target}</code> забанен.")
                    send_msg(target, "🚫 Вы заблокированы администратором.")
                elif action == "unban":
                    conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (target,))
                    conn.commit()
                    send_msg(chat_id, f"✅ <code>{target}</code> разбанен.")
                    send_msg(target, "✅ Вы разблокированы.")
                elif action == "mute":
                    conn.execute("UPDATE users SET is_muted=1 WHERE user_id=?", (target,))
                    conn.commit()
                    send_msg(chat_id, f"🔇 <code>{target}</code> замьючен.")
                elif action == "unmute":
                    conn.execute("UPDATE users SET is_muted=0 WHERE user_id=?", (target,))
                    conn.commit()
                    send_msg(chat_id, f"🔔 <code>{target}</code> размьючен.")
            return True

    return False

def handle_msg_command(chat_id, user_id, args):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    parts = args.strip().split(" ", 1)
    if len(parts) < 2:
        send_msg(chat_id, "❌ Использование: /msg ID текст")
        return

    try:
        target_id = int(parts[0])
        msg_text = parts[1]
        r = send_msg(target_id, f"📩 <b>Сообщение от администратора:</b>\n\n{msg_text}")
        if r and r.get("ok"):
            send_msg(chat_id, f"✅ Сообщение отправлено пользователю <code>{target_id}</code>")
        else:
            send_msg(chat_id, f"❌ Не удалось отправить. Пользователь заблокировал бота?")
    except ValueError:
        send_msg(chat_id, "❌ Неверный ID пользователя")

def handle_info_command(chat_id, user_id, target_id):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (target_id,)).fetchone()

        if not row:
            send_msg(chat_id, f"❌ Пользователь <code>{target_id}</code> не найден.")
            return

        # Базовая информация
        connected = conn.execute("SELECT COUNT(*) FROM connections WHERE user_id=?", (target_id,)).fetchone()[0]
        msg_count = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=?", (target_id,)).fetchone()[0]
        del_count = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=? AND deleted=1", (target_id,)).fetchone()[0]
        edit_count = conn.execute("SELECT COUNT(*) FROM edits WHERE owner_id=?", (target_id,)).fetchone()[0]

        # Дополнительная статистика
        # Последнее удаление
        last_del = conn.execute("""
            SELECT timestamp, chat_name, content FROM messages
            WHERE owner_id=? AND deleted=1
            ORDER BY timestamp DESC LIMIT 1
        """, (target_id,)).fetchone()

        # Последнее редактирование
        last_edit = conn.execute("""
            SELECT edited_at, chat_name FROM edits
            WHERE owner_id=?
            ORDER BY edited_at DESC LIMIT 1
        """, (target_id,)).fetchone()

        # Статистика по типам медиа
        media_stats = conn.execute("""
            SELECT media_type, COUNT(*) as count
            FROM messages
            WHERE owner_id=? AND deleted=1 AND media_type IS NOT NULL
            GROUP BY media_type
        """, (target_id,)).fetchall()

        # Топ чатов по удалениям
        top_chats = conn.execute("""
            SELECT chat_name, COUNT(*) as count
            FROM messages
            WHERE owner_id=? AND deleted=1 AND chat_name IS NOT NULL
            GROUP BY chat_name
            ORDER BY count DESC
            LIMIT 5
        """, (target_id,)).fetchall()

        # Plus подписка
        plus_info = get_plus_info(target_id)
        has_plus = check_plus_subscription(target_id)

        name = row["first_name"] or "Без имени"
        uname = f"@{row['username']}" if row["username"] else "нет"
        joined = (row["joined_at"] or "")[:10]

        # Формируем отчет
        report = f"👤 <b>Информация о пользователе</b>\n\n"

        # Основная информация
        report += f"━━━━━━━━━━━━━━━\n"
        report += f"<b>📋 Основное:</b>\n"
        report += f"• Имя: <b>{name}</b>\n"
        report += f"• Username: {uname}\n"
        report += f"• ID: <code>{target_id}</code>\n"
        report += f"• Регистрация: {joined}\n"

        # Статус
        report += f"\n<b>🔧 Статус:</b>\n"
        report += f"• Подключён: {'✅ Да' if connected else '❌ Нет'}\n"
        report += f"• Забанен: {'🚫 Да' if row['is_banned'] else '✅ Нет'}\n"
        report += f"• Заглушен: {'🔇 Да' if row['is_muted'] else '✅ Нет'}\n"
        report += f"• Plus: {'✨ Активна' if has_plus else '❌ Нет'}\n"

        if has_plus and plus_info:
            expires = plus_info.get('expires_at', '')[:10]
            report += f"  └ Истекает: {expires}\n"

        # Общая статистика
        report += f"\n<b>  Общая статистика:</b>\n"
        report += f"• Всего сообщений: <b>{msg_count}</b>\n"
        report += f"• Удалено: <b>{del_count}</b>\n"
        report += f"• Отредактировано: <b>{edit_count}</b>\n"

        if msg_count > 0:
            del_percent = round((del_count / msg_count) * 100, 1)
            report += f"• % удалений: <b>{del_percent}%</b>\n"

        report += f"\n━━━━━━━━━━━━━━━"

        send_msg(chat_id, report)

def check_whitelist(user_id):
    if not get_whitelist_mode():
        return True
    if user_id == ADMIN_ID:
        return True
    with get_db() as conn:
        row = conn.execute("SELECT user_id FROM whitelist WHERE user_id=?", (user_id,)).fetchone()
        return row is not None

def handle_spy_command(chat_id, user_id, target_id):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    with get_db() as conn:
        rows = conn.execute("""
            SELECT sender_name, content, media_type, chat_name, timestamp
            FROM messages WHERE owner_id=? AND deleted=1
            ORDER BY timestamp DESC LIMIT 10
        """, (target_id,)).fetchall()

        u = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()
        name = u["first_name"] if u else "?"
        uname = f"@{u['username']}" if u and u["username"] else "нет"

        if not rows:
            send_msg(chat_id, f"👁 У {name} ({uname}) нет удалённых сообщений.")
            return

        text = f"👁 <b>Удалённые юзера {name} ({uname}):</b>\n\n"
        for r in rows:
            ts = (r["timestamp"] or "")[:16].replace("T", " ")
            content = (r["content"] or "")[:60]
            icon = "📷" if r["media_type"] else "💬"
            text += f"{icon} <b>{r['sender_name']}</b> → {r['chat_name'] or '?'}\n   {content}\n   🕐 {ts}\n\n"

        send_msg(chat_id, text)

def handle_spyedits_command(chat_id, user_id, target_id):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    with get_db() as conn:
        rows = conn.execute("""
            SELECT e.old_content, e.new_content, e.edited_at, m.sender_name, m.chat_name
            FROM edits e JOIN messages m ON e.message_id=m.message_id AND e.owner_id=m.owner_id
            WHERE e.owner_id=? ORDER BY e.edited_at DESC LIMIT 10
        """, (target_id,)).fetchall()

        u = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()
        name = u["first_name"] if u else "?"
        uname = f"@{u['username']}" if u and u["username"] else "нет"

        if not rows:
            send_msg(chat_id, f"✏️ У {name} ({uname}) нет редактирований.")
            return

        text = f"✏️ <b>Редактирования юзера {name} ({uname}):</b>\n\n"
        for r in rows:
            ts = (r["edited_at"] or "")[:16].replace("T", " ")
            old = (r["old_content"] or "")[:40]
            new = (r["new_content"] or "")[:40]
            text += f"👤 <b>{r['sender_name']}</b> → {r['chat_name'] or '?'}\n   ❌ {old}\n   ✅ {new}\n   🕐 {ts}\n\n"

        send_msg(chat_id, text)

def handle_spystats_command(chat_id, user_id, target_id):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    with get_db() as conn:
        u = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()
        total = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=?", (target_id,)).fetchone()[0]
        deleted = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=? AND deleted=1", (target_id,)).fetchone()[0]
        edited = conn.execute("SELECT COUNT(*) FROM edits WHERE owner_id=?", (target_id,)).fetchone()[0]

        top_chats = conn.execute("""
            SELECT chat_name, COUNT(*) as c FROM messages
            WHERE owner_id=? AND deleted=1 AND chat_name IS NOT NULL
            GROUP BY chat_name ORDER BY c DESC LIMIT 5
        """, (target_id,)).fetchall()

        top_senders = conn.execute("""
            SELECT sender_name, COUNT(*) as c FROM messages
            WHERE owner_id=? AND deleted=1
            GROUP BY sender_name ORDER BY c DESC LIMIT 5
        """, (target_id,)).fetchall()

        name = u["first_name"] if u else "?"
        uname = f"@{u['username']}" if u and u["username"] else "нет"

        text = (f"📊 <b>Статистика юзера {name} ({uname})</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"💾 Сообщений в БД: <b>{total}</b>\n"
                f"🗑 Удалений поймано: <b>{deleted}</b>\n"
                f"✏️ Редактирований: <b>{edited}</b>\n")

        if top_chats:
            text += "━━━━━━━━━━━━━━━\n🏆 <b>Топ чатов:</b>\n"
            for i, r in enumerate(top_chats, 1):
                text += f"  {i}. {r['chat_name']} — {r['c']} шт.\n"

        if top_senders:
            text += "━━━━━━━━━━━━━━━\n👤 <b>Топ отправителей:</b>\n"
            for i, r in enumerate(top_senders, 1):
                text += f"  {i}. {r['sender_name']} — {r['c']} шт.\n"

        send_msg(chat_id, text)

def handle_getfile_command(chat_id, user_id, file_id):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    with get_db() as conn:
        row = conn.execute("""
            SELECT media_type, file_id, sender_name, chat_name, content, timestamp
            FROM messages WHERE file_id=? LIMIT 1
        """, (file_id,)).fetchone()

        if not row:
            send_msg(chat_id, f"❌ Файл <code>{file_id}</code> не найден в БД.")
            return

        mt = row["media_type"]
        fid = row["file_id"]
        ts = (row["timestamp"] or "")[:16].replace("T", " ")
        caption = (f"📎 <b>Файл из БД</b>\n"
                   f"👤 От: {row['sender_name']}\n"
                   f"💬 Чат: {row['chat_name'] or '?'}\n"
                   f"🕐 {ts}")

        if mt == "photo":
            send_photo_msg(chat_id, fid, caption=caption)
        elif mt == "video":
            send_video_msg(chat_id, fid, caption=caption)
        elif mt == "voice":
            send_voice_msg(chat_id, fid, caption=caption)
        elif mt == "audio":
            send_audio_msg(chat_id, fid, caption=caption)
        elif mt == "document":
            send_doc_msg(chat_id, fid, caption=caption)
        elif mt == "animation":
            send_anim_msg(chat_id, fid, caption=caption)
        elif mt == "video_note":
            send_msg(chat_id, caption)
            send_vnote_msg(chat_id, fid)
        elif mt == "sticker":
            send_msg(chat_id, caption)
            send_sticker_msg(chat_id, fid)
        else:
            send_msg(chat_id, f"❓ Неизвестный тип: {mt}\n{caption}")

def handle_media_command(chat_id, user_id, target_id, limit=10):
    if not is_admin(user_id):
        send_msg(chat_id, "⛔ Нет доступа.")
        return

    with get_db() as conn:
        rows = conn.execute("""
            SELECT media_type, file_id, sender_name, chat_name, timestamp
            FROM messages WHERE owner_id=? AND media_type IS NOT NULL
            ORDER BY timestamp DESC LIMIT ?
        """, (target_id, limit)).fetchall()

        u = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()
        name = u["first_name"] if u else "?"
        uname = f"@{u['username']}" if u and u["username"] else "нет"

        if not rows:
            send_msg(chat_id, f"📎 У {name} нет медиафайлов в БД.")
            return

        icons = {"photo":"📷","video":"🎥","voice":"🎤","audio":"🎵","document":"📎","animation":"🎞","video_note":"⭕","sticker":"🎭"}
        text = f"📎 <b>Медиафайлы юзера {name} ({uname}):</b>\n\n"
        for r in rows:
            ts = (r["timestamp"] or "")[:16].replace("T", " ")
            icon = icons.get(r["media_type"] or "", "📎")
            text += (f"{icon} <b>{r['media_type']}</b> от {r['sender_name']}\n"
                     f"   💬 {r['chat_name'] or '?'} | 🕐 {ts}\n"
                     f"   <code>{r['file_id']}</code>\n\n")

        text += "\n📥 Получить файл: /getfile file_id"
        send_msg(chat_id, text)

def on_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    u = msg.get("from") or {}
    text = msg.get("text", "")

    register_user(user_id, u.get("username"), u.get("first_name"))

    if is_banned(user_id):
        return

    if not is_admin(user_id) and not check_whitelist(user_id):
        send_msg(chat_id, "🔒 Включен белый список/технические работы. Вернитесь позже.")
        return

    # ИСПРАВЛЕНИЕ: Обработка дизайн-панели ПЕРЕД обработкой команд
    if is_admin(user_id):
        # Сначала проверяем дизайн-панель
        if handle_design_message(chat_id, user_id, msg):
            return

        # Затем проверяем подтверждения админа
        if get_admin_state(user_id) is not None and not text.startswith("/"):
            if handle_admin_confirm(chat_id, user_id, text):
                return

    # Обычные команды
    if text == "/start":
        if is_command_enabled("/start"):
            on_start(chat_id, user_id, u.get("username",""), u.get("first_name",""))
        else:
            send_msg(chat_id, "⚠️ Эта команда временно отключена администратором.")
    elif text == "/settings":
        if is_command_enabled("/settings"):
            on_settings(chat_id, user_id)
        else:
            send_msg(chat_id, "⚠️ Эта команда временно отключена администратором.")
    elif text == "/stats":
        if is_command_enabled("/stats"):
            # Проверяем Plus подписку
            is_plus = check_plus_subscription(user_id)

            with get_db() as conn:
                total_del = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=? AND deleted=1", (user_id,)).fetchone()[0]
                total_edit = conn.execute("SELECT COUNT(*) FROM edits WHERE owner_id=?", (user_id,)).fetchone()[0]
                total_msg = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=?", (user_id,)).fetchone()[0]

                if is_plus:
                    # РАСШИРЕННАЯ СТАТИСТИКА ДЛЯ PLUS
                    # Статистика по типам медиа
                    media_stats = conn.execute("""
                        SELECT media_type, COUNT(*) as count
                        FROM messages
                        WHERE owner_id=? AND media_type IS NOT NULL AND deleted=1
                        GROUP BY media_type
                    """, (user_id,)).fetchall()

                    # Топ чаты по удалениям
                    top_chats = conn.execute("""
                        SELECT chat_name, COUNT(*) as count
                        FROM messages
                        WHERE owner_id=? AND deleted=1 AND chat_name IS NOT NULL
                        GROUP BY chat_name
                        ORDER BY count DESC
                        LIMIT 5
                    """, (user_id,)).fetchall()

                    # Статистика за последние 7 дней
                    from datetime import datetime, timedelta
                    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                    recent_del = conn.execute("""
                        SELECT COUNT(*) FROM messages
                        WHERE owner_id=? AND deleted=1 AND timestamp > ?
                    """, (user_id, week_ago)).fetchone()[0]

                    recent_edit = conn.execute("""
                        SELECT COUNT(*) FROM edits
                        WHERE owner_id=? AND edited_at > ?
                    """, (user_id, week_ago)).fetchone()[0]

            plus_badge = " ✨ <b>Plus</b>" if is_plus else ""

            stats_text = (
                f'<tg-emoji emoji-id="5936143551854285132">📊</tg-emoji> <b>Ваша статистика{plus_badge}</b>\n'
                f"━━━━━━━━━━━━━━━\n"
                f'<tg-emoji emoji-id="6032924188828767321">📨</tg-emoji> <b>Сообщений всего:</b> {total_msg}\n'
                f'<tg-emoji emoji-id="6039522349517115015">🗑</tg-emoji> <b>Удаленных сообщений:</b> {total_del}\n'
                f'<tg-emoji emoji-id="6039779802741739617">✏️</tg-emoji> <b>Редактированных сообщений:</b> {total_edit}'
            )

            if is_plus:
                # ДОБАВЛЯЕМ РАСШИРЕННУЮ СТАТИСТИКУ
                stats_text += f"\n\n✨ <b>Plus статистика:</b>\n"
                stats_text += f"📅 За последние 7 дней:\n"
                stats_text += f"   🗑 Удалений: <b>{recent_del}</b>\n"
                stats_text += f"   ✏️ Редактирований: <b>{recent_edit}</b>\n"

                if media_stats:
                    stats_text += f"\n📎 <b>Удаленные медиа:</b>\n"
                    media_icons = {
                        "photo": "📷",
                        "video": "🎥",
                        "voice": "🎤",
                        "audio": "🎵",
                        "document": "📎",
                        "animation": "🎞",
                        "video_note": "⭕",
                        "sticker": "🎭"
                    }
                    for m in media_stats[:5]:
                        icon = media_icons.get(m["media_type"], "📎")
                        stats_text += f"   {icon} {m['media_type']}: <b>{m['count']}</b>\n"

                if top_chats:
                    stats_text += f"\n🔥 <b>Топ чатов по удалениям:</b>\n"
                    for i, chat in enumerate(top_chats, 1):
                        chat_name = chat["chat_name"][:20]
                        stats_text += f"   {i}. {chat_name}: <b>{chat['count']}</b>\n"

            send_msg(chat_id, stats_text)
        else:
            send_msg(chat_id, "⚠️ Эта команда временно отключена администратором.")
    elif text == "/plus":
        if is_command_enabled("/plus"):
            handle_plus_command(chat_id, user_id)
        else:
            send_msg(chat_id, "⚠️ Эта команда временно отключена администратором.")

    elif text == "/plusstats":
        # ЭКСКЛЮЗИВНАЯ КОМАНДА ДЛЯ PLUS ПОДПИСЧИКОВ
        if not check_plus_subscription(user_id):
            send_msg(chat_id,
                "🔒 <b>Эта команда доступна только с подпиской Plus</b>\n\n"
                "Используйте /plus для получения информации о подписке")
            return

        # Детальная статистика для Plus
        with get_db() as conn:
            from datetime import datetime, timedelta

            # Статистика по дням недели
            day_stats = conn.execute("""
                SELECT strftime('%w', timestamp) as day, COUNT(*) as count
                FROM messages
                WHERE owner_id=? AND deleted=1
                GROUP BY day
            """, (user_id,)).fetchall()

            # Статистика по часам
            hour_stats = conn.execute("""
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                FROM messages
                WHERE owner_id=? AND deleted=1
                GROUP BY hour
                ORDER BY count DESC
                LIMIT 3
            """, (user_id,)).fetchall()

            # Самые активные отправители (кто больше всего удаляет)
            top_senders = conn.execute("""
                SELECT sender_name, COUNT(*) as count
                FROM messages
                WHERE owner_id=? AND deleted=1 AND sender_name IS NOT NULL
                GROUP BY sender_name
                ORDER BY count DESC
                LIMIT 5
            """, (user_id,)).fetchall()

            # Средняя скорость редактирования (сколько раз редактируют)
            avg_edits = conn.execute("""
                SELECT AVG(edit_count) as avg
                FROM messages
                WHERE owner_id=? AND edited=1
            """, (user_id,)).fetchone()

            total_del = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=? AND deleted=1", (user_id,)).fetchone()[0]

        days_map = {
            "0": "Воскресенье", "1": "Понедельник", "2": "Вторник",
            "3": "Среда", "4": "Четверг", "5": "Пятница", "6": "Суббота"
        }

        stats_text = (
            f"✨ <b>Plus: Детальная статистика</b>\n"
            f"━━━━━━━━━━━━━━━\n"
        )

        if hour_stats:
            stats_text += f"\n⏰ <b>Пиковые часы удалений:</b>\n"
            for h in hour_stats:
                stats_text += f"   {h['hour']}:00 — <b>{h['count']}</b> удалений\n"

        if day_stats and total_del > 0:
            stats_text += f"\n📅 <b>Статистика по дням недели:</b>\n"
            sorted_days = sorted(day_stats, key=lambda x: x['count'], reverse=True)[:3]
            for d in sorted_days:
                day_name = days_map.get(d['day'], d['day'])
                percentage = round((d['count'] / total_del) * 100, 1)
                stats_text += f"   {day_name}: <b>{d['count']}</b> ({percentage}%)\n"

        if top_senders:
            stats_text += f"\n👥 <b>Топ по удалениям:</b>\n"
            for i, sender in enumerate(top_senders, 1):
                name = sender['sender_name'][:15]
                stats_text += f"   {i}. {name}: <b>{sender['count']}</b>\n"

        if avg_edits and avg_edits['avg']:
            stats_text += f"\n✏️ <b>Среднее редактирований:</b> {round(avg_edits['avg'], 1)} раз на сообщение\n"

        stats_text += f"\n💡 <i>Эта статистика доступна только подписчикам Plus</i>"

        send_msg(chat_id, stats_text)

    elif text in ("/admin", "/admin@v373ments_bot"):
        handle_admin_command(chat_id, user_id)
    elif text == "/export_settings" and is_admin(user_id):
        try:
            with get_db() as conn:
                # Экспортируем настройки дизайна
                rows = conn.execute("SELECT * FROM bot_customization").fetchall()
                settings_data = {}
                for row in rows:
                    settings_data[row["setting_key"]] = row["setting_value"]

                import json
                json_data = json.dumps(settings_data, ensure_ascii=False, indent=2)

                # Отправляем как файл
                api("sendDocument", chat_id=chat_id,
                    document=("bot_settings.json", json_data.encode('utf-8')),
                    caption="📤 Настройки дизайна бота")
        except Exception as e:
            send_msg(chat_id, f"❌ Ошибка экспорта: {e}")

    elif text == "/download_db" and is_admin(user_id):
        try:
            import os
            if os.path.exists(DB_PATH):
                # Отправляем файл БД через Telegram
                with open(DB_PATH, 'rb') as f:
                    api("sendDocument", chat_id=chat_id,
                        document=("spy.db", f.read()),
                        caption="📥 База данных бота")
            else:
                send_msg(chat_id, "❌ База данных не найдена")
        except Exception as e:
            send_msg(chat_id, f"❌ Ошибка: {e}")

    elif text == "/design" and is_admin(user_id):
        handle_design_command(chat_id, user_id)

    elif text == "/getdb" and is_admin(user_id):
        try:
            import os
            if os.path.exists(DB_PATH):
                with open(DB_PATH, 'rb') as f:
                    db_data = f.read()
                # Отправляем БД как документ
                files = {'document': ('spy.db', db_data, 'application/octet-stream')}
                response = api("sendDocument", chat_id=chat_id, caption="📥 База данных бота")
                if not response.get('ok'):
                    # Если не получилось через API, попробуем другой способ
                    send_msg(chat_id, f"📊 Размер БД: {len(db_data)} байт\n💾 Отправляю файл...")
                    with open(DB_PATH, 'rb') as f:
                        import requests
                        files = {'document': f}
                        data = {'chat_id': chat_id, 'caption': '📥 База данных'}
                        requests.post(f"{API_URL}sendDocument", files=files, data=data)
            else:
                send_msg(chat_id, "❌ БД не найдена")
        except Exception as e:
            send_msg(chat_id, f"❌ Ошибка: {e}")

    elif text == "/messages" and is_admin(user_id):
        try:
            with get_db() as conn:
                rows = conn.execute("SELECT * FROM messages ORDER BY timestamp DESC LIMIT 1000").fetchall()
                if rows:
                    import json
                    messages_data = []
                    for row in rows:
                        messages_data.append(dict(row))

                    json_data = json.dumps(messages_data, ensure_ascii=False, indent=2)

                    # Отправляем как текстовый файл
                    import requests
                    files = {'document': ('messages.json', json_data.encode('utf-8'), 'application/json')}
                    data = {'chat_id': chat_id, 'caption': '📨 Последние 1000 сообщений'}
                    requests.post(f"{API_URL}sendDocument", files=files, data=data)
                else:
                    send_msg(chat_id, "❌ Сообщений не найдено")
        except Exception as e:
            send_msg(chat_id, f"❌ Ошибка: {e}")

    elif text == "/db" and is_admin(user_id):
        # ПРОСТАЯ КОМАНДА ДЛЯ СКАЧИВАНИЯ ПОЛНОЙ БД
        try:
            with open(DB_PATH, 'rb') as f:
                import requests
                files = {'document': ('spy_full.db', f, 'application/octet-stream')}
                data = {'chat_id': chat_id, 'caption': '💾 ПОЛНАЯ БАЗА ДАННЫХ (все сообщения)'}
                response = requests.post(f"{API_URL}sendDocument", files=files, data=data)
                if response.status_code == 200:
                    send_msg(chat_id, "✅ БД отправлена!")
                else:
                    send_msg(chat_id, f"❌ Ошибка отправки: {response.text}")
        except Exception as e:
            send_msg(chat_id, f"❌ Ошибка: {e}")

    elif text == "/users":
        handle_users_command(chat_id, user_id)
    elif text.startswith("/find "):
        handle_find_command(chat_id, user_id, text[6:])
    elif text.startswith("/ban "):
        try:
            handle_ban_command(chat_id, user_id, int(text[5:].strip()))
        except:
            send_msg(chat_id, "❌ Использование: /ban <id>")
    elif text.startswith("/unban "):
        try:
            handle_unban_command(chat_id, user_id, int(text[7:].strip()))
        except:
            send_msg(chat_id, "❌ Использование: /unban <id>")
    elif text.startswith("/mute "):
        try:
            handle_mute_command(chat_id, user_id, int(text[6:].strip()))
        except:
            send_msg(chat_id, "❌ Использование: /mute <id>")
    elif text.startswith("/unmute "):
        try:
            handle_unmute_command(chat_id, user_id, int(text[8:].strip()))
        except:
            send_msg(chat_id, "❌ Использование: /unmute <id>")
    elif text == "/broadcast":
        handle_broadcast_command(chat_id, user_id)
    elif text.startswith("/msg ") and is_admin(user_id):
        handle_msg_command(chat_id, user_id, text[5:])
    elif text.startswith("/info ") and is_admin(user_id):
        try:
            handle_info_command(chat_id, user_id, int(text[6:].strip()))
        except:
            send_msg(chat_id, "❌ Использование: /info ID")
    elif text.startswith("/getfile ") and is_admin(user_id):
        handle_getfile_command(chat_id, user_id, text[9:].strip())
    elif text.startswith("/media ") and is_admin(user_id):
        try:
            handle_media_command(chat_id, user_id, int(text[7:].strip()))
        except:
            send_msg(chat_id, "❌ Использование: /media ID")
    elif text.startswith("/spy ") and is_admin(user_id):
        try:
            handle_spy_command(chat_id, user_id, int(text[5:].strip()))
        except:
            send_msg(chat_id, "❌ Использование: /spy ID")
    elif text.startswith("/spyedits ") and is_admin(user_id):
        try:
            handle_spyedits_command(chat_id, user_id, int(text[10:].strip()))
        except:
            send_msg(chat_id, "❌ Использование: /spyedits ID")
    elif text.startswith("/spystats ") and is_admin(user_id):
        try:
            handle_spystats_command(chat_id, user_id, int(text[10:].strip()))
        except:
            send_msg(chat_id, "❌ Использование: /spystats ID")
    elif text == "/chat":
        if is_command_enabled("/chat"):
            help_text = (
                '<tg-emoji emoji-id="6034831751308644168">🔥</tg-emoji> <b>Правильное использование команды /chat:</b>\n\n'
                '/chat ID (пользователя или @username)'
            )
            send_msg(chat_id, help_text)
        else:
            send_msg(chat_id, "⚠️ Эта команда временно отключена администратором.")
    elif text.startswith("/chat "):
        if is_command_enabled("/chat"):
            handle_chat_export(chat_id, user_id, text[6:])
        else:
            send_msg(chat_id, "⚠️ Эта команда временно отключена администратором.")
    elif text == "/whitelist" and is_admin(user_id):
        if get_whitelist_mode():
            set_admin_state(user_id, {"action": "whitelist_off"})
            send_msg(chat_id,
                "⚠️ <b>Подтверди выключение белого списка</b>\n\n"
                "Всем пользователям придёт уведомление о возобновлении работы.\n\n"
                "Напиши <b>да</b> для подтверждения или <b>нет</b> для отмены.")
        else:
            set_admin_state(user_id, {"action": "whitelist_on"})
            send_msg(chat_id,
                "⚠️ <b>Подтверди включение белого списка</b>\n\n"
                "Всем пользователям придёт уведомление о технических работах.\n\n"
                "Напиши <b>да</b> для подтверждения или <b>нет</b> для отмены.")
    elif text.startswith("/wladd") and is_admin(user_id):
        parts = text.split()
        if len(parts) < 2:
            send_msg(chat_id, "❌ Использование: /wladd ID")
        else:
            try:
                target_id = int(parts[1].strip())
                with get_db() as conn:
                    row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()
                name = row["first_name"] if row else "?"
                uname = f"@{row['username']}" if row and row["username"] else "нет"
                set_admin_state(user_id, {"action": "wladd", "target": target_id})
                send_msg(chat_id,
                    f"⚠️ <b>Добавить в белый список?</b>\n\n"
                    f"👤 {name} ({uname})\n"
                    f"🆔 <code>{target_id}</code>\n\n"
                    f"Напиши <b>да</b> или <b>нет</b>.")
            except ValueError:
                send_msg(chat_id, "❌ Использование: /wladd ID")
    elif text.startswith("/wlremove") and is_admin(user_id):
        parts = text.split()
        if len(parts) < 2:
            send_msg(chat_id, "❌ Использование: /wlremove ID")
        else:
            try:
                target_id = int(parts[1].strip())
                with get_db() as conn:
                    row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()
                name = row["first_name"] if row else "?"
                uname = f"@{row['username']}" if row and row["username"] else "нет"
                set_admin_state(user_id, {"action": "wlremove", "target": target_id})
                send_msg(chat_id,
                    f"⚠️ <b>Убрать из белого списка?</b>\n\n"
                    f"👤 {name} ({uname})\n"
                    f"🆔 <code>{target_id}</code>\n\n"
                    f"Напиши <b>да</b> или <b>нет</b>.")
            except ValueError:
                send_msg(chat_id, "❌ Использование: /wlremove ID")
    elif text == "/wllist" and is_admin(user_id):
        load_whitelist()
        if not whitelist_users:
            send_msg(chat_id, "📋 Белый список пуст.")
        else:
            with get_db() as conn:
                text_out = f"📋 <b>Белый список ({len(whitelist_users)}):</b>\n\n"
                for uid in whitelist_users:
                    row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (uid,)).fetchone()
                    name = row["first_name"] if row else "?"
                    uname = f"@{row['username']}" if row and row["username"] else "нет"
                    text_out += f"👤 {name} ({uname}) — <code>{uid}</code>\n"
            send_msg(chat_id, text_out)

    # ===== PLUS ПОДПИСКИ =====
    elif text.startswith("/plusadd") and is_admin(user_id):
        parts = text.split()
        if len(parts) < 3:
            send_msg(chat_id, "❌ Использование: /plusadd ID дни\n\nПример: /plusadd 123456789 30")
        else:
            try:
                target_id = int(parts[1].strip())
                days = int(parts[2].strip())

                with get_db() as conn:
                    row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

                if row:
                    name = row["first_name"] or "?"
                    uname = f"@{row['username']}" if row["username"] else "нет"

                    add_plus_subscription(target_id, days)

                    send_msg(chat_id,
                        f"✅ <b>Plus подписка добавлена!</b>\n\n"
                        f"👤 {name} ({uname})\n"
                        f"🆔 <code>{target_id}</code>\n"
                        f"⏰ На <b>{days}</b> дней")

                    # Уведомляем пользователя
                    send_msg(target_id,
                        f"✨ <b>Поздравляем!</b>\n\n"
                        f"Вам активирована подписка <b>Plus</b> на {days} дней!\n\n"
                        f"🎁 Используйте /plus чтобы узнать о преимуществах")
                else:
                    send_msg(chat_id, f"❌ Пользователь с ID {target_id} не найден в базе")
            except ValueError:
                send_msg(chat_id, "❌ Неверный формат. Использование: /plusadd ID дни")

    elif text.startswith("/plusremove") and is_admin(user_id):
        parts = text.split()
        if len(parts) < 2:
            send_msg(chat_id, "❌ Использование: /plusremove ID")
        else:
            try:
                target_id = int(parts[1].strip())

                with get_db() as conn:
                    row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

                if row:
                    name = row["first_name"] or "?"
                    uname = f"@{row['username']}" if row["username"] else "нет"

                    remove_plus_subscription(target_id)

                    send_msg(chat_id,
                        f"✅ <b>Plus подписка удалена</b>\n\n"
                        f"👤 {name} ({uname})\n"
                        f"🆔 <code>{target_id}</code>")

                    # Уведомляем пользователя
                    send_msg(target_id,
                        f"⚠️ <b>Ваша подписка Plus была отменена администратором</b>\n\n"
                        f"По вопросам обращайтесь к администратору.")
                else:
                    send_msg(chat_id, f"❌ Пользователь с ID {target_id} не найден")
            except ValueError:
                send_msg(chat_id, "❌ Использование: /plusremove ID")

    elif text == "/pluslist" and is_admin(user_id):
        with get_db() as conn:
            rows = conn.execute("""
                SELECT p.user_id, p.expires_at, u.first_name, u.username
                FROM plus_subscriptions p
                LEFT JOIN users u ON p.user_id = u.user_id
                ORDER BY p.expires_at DESC
            """).fetchall()

            if not rows:
                send_msg(chat_id, "📋 Нет активных Plus подписок")
            else:
                from datetime import datetime
                text_out = f"✨ <b>Plus подписки ({len(rows)}):</b>\n\n"

                active_count = 0
                expired_count = 0

                for r in rows:
                    name = r["first_name"] or "?"
                    uname = f"@{r['username']}" if r["username"] else "нет"
                    expires_at = datetime.fromisoformat(r["expires_at"])

                    if expires_at > datetime.now():
                        days_left = (expires_at - datetime.now()).days
                        status = f"✅ {days_left}д"
                        active_count += 1
                    else:
                        status = "❌ истекла"
                        expired_count += 1

                    text_out += f"{status} {name} ({uname})\n   🆔 <code>{r['user_id']}</code>\n   ⏰ до {expires_at.strftime('%d.%m.%Y')}\n\n"

                text_out += f"━━━━━━━━━━━━━━━\n"
                text_out += f"✅ Активных: <b>{active_count}</b>\n"
                text_out += f"❌ Истекших: <b>{expired_count}</b>"

                send_msg(chat_id, text_out)

    elif text.startswith("/pluscheck") and is_admin(user_id):
        parts = text.split()
        if len(parts) < 2:
            send_msg(chat_id, "❌ Использование: /pluscheck ID")
        else:
            try:
                target_id = int(parts[1].strip())
                plus_info = get_plus_info(target_id)

                with get_db() as conn:
                    row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

                if row:
                    name = row["first_name"] or "?"
                    uname = f"@{row['username']}" if row["username"] else "нет"

                    if plus_info:
                        from datetime import datetime
                        expires_at = datetime.fromisoformat(plus_info['expires_at'])
                        activated_at = datetime.fromisoformat(plus_info['activated_at'])

                        if expires_at > datetime.now():
                            days_left = (expires_at - datetime.now()).days
                            status_icon = "✅"
                            status_text = "Активна"
                        else:
                            days_left = 0
                            status_icon = "❌"
                            status_text = "Истекла"

                        send_msg(chat_id,
                            f"✨ <b>Plus подписка</b>\n\n"
                            f"👤 {name} ({uname})\n"
                            f"🆔 <code>{target_id}</code>\n"
                            f"━━━━━━━━━━━━━━━\n"
                            f"📊 Статус: {status_icon} <b>{status_text}</b>\n"
                            f"📅 Активирована: {activated_at.strftime('%d.%m.%Y')}\n"
                            f"⏰ Действует до: {expires_at.strftime('%d.%m.%Y %H:%M')}\n"
                            f"⏳ Осталось: <b>{days_left}</b> дней")
                    else:
                        send_msg(chat_id,
                            f"👤 {name} ({uname})\n"
                            f"🆔 <code>{target_id}</code>\n\n"
                            f"❌ Plus подписки нет")
                else:
                    send_msg(chat_id, f"❌ Пользователь с ID {target_id} не найден")
            except ValueError:
                send_msg(chat_id, "❌ Использование: /pluscheck ID")

    elif text == "/help":
        if is_command_enabled("/help"):
            help_text = get_custom_setting('help_text')
            send_msg(chat_id, help_text)
        else:
            send_msg(chat_id, "⚠️ Эта команда временно отключена администратором.")

    elif text == "/updatehelp" and is_admin(user_id):
        # ОБНОВЛЕНИЕ HELP ТЕКСТА В БД
        try:
            new_help = '<tg-emoji emoji-id="5962952497197748583">🔥</tg-emoji> <b>Помощь по командам</b>\n━━━━━━━━━━━━━━━\n/start — Главное меню\n/settings — Настройки уведомлений\n/stats — Ваша статистика\n/chat @username или ID — Экспорт чата\n\n<tg-emoji emoji-id="5776078972659962594">🔥</tg-emoji> <b>Помощь по подключению</b>\n━━━━━━━━━━━━━━━\n<b>Как подключить:</b>\n1. Откройте <b>Ваш профиль</b> в Telegram\n2. Перейдите в <b>Автоматизация чатов</b>\n3. В поисковую строку напишите: <b>@v373ments_bot</b>\n4. Выберите <b>@v373ments_bot</b>\n5. <b>Разрешите</b> доступ ко всем чатам и сообщениям.'

            from datetime import datetime as dt
            with get_db() as conn:
                now = dt.now().isoformat()
                conn.execute("""UPDATE bot_customization
                    SET setting_value=?, updated_at=?
                    WHERE setting_key='help_text'""",
                    (new_help, now))
                conn.commit()

            send_msg(chat_id, "✅ Текст /help обновлён!\n\nПроверь командой /help")
        except Exception as e:
            send_msg(chat_id, f"❌ Ошибка: {e}")

    elif text == "/updatewelcome" and is_admin(user_id):
        # ОБНОВЛЕНИЕ WELCOME ТЕКСТА В БД
        try:
            new_welcome = '<tg-emoji emoji-id="6037249452824072506">🔥</tg-emoji> <b>Бот успешно подключен к вам!</b>\n\n<tg-emoji emoji-id="5904258298764334001">🔥</tg-emoji> Настроить уведомления <b>Вы</b> можете через <b>/settings</b>.'

            from datetime import datetime as dt
            with get_db() as conn:
                now = dt.now().isoformat()
                conn.execute("""UPDATE bot_customization
                    SET setting_value=?, updated_at=?
                    WHERE setting_key='welcome_text'""",
                    (new_welcome, now))
                conn.commit()

            send_msg(chat_id, "✅ Текст приветствия обновлён!\n\nПодключи бота заново чтобы увидеть новый текст.")
        except Exception as e:
            send_msg(chat_id, f"❌ Ошибка: {e}")

    elif text == "/updatedisconnect" and is_admin(user_id):
        # ОБНОВЛЕНИЕ DISCONNECT ТЕКСТА В БД
        try:
            new_disconnect = '<tg-emoji emoji-id="6037496202990194718">🔥</tg-emoji> <b>Бот был отключён.</b>\n\nЕсли это произошло случайно, вы можете подключить бота повторно. Будьте осторожны и остерегайтесь других ботов, которые могут оказаться предназначены для мошенничества с вашим аккаунтом.'

            from datetime import datetime as dt
            with get_db() as conn:
                # Проверяем есть ли уже такая настройка
                existing = conn.execute("SELECT setting_key FROM bot_customization WHERE setting_key='disconnect_text'").fetchone()

                now = dt.now().isoformat()
                if existing:
                    conn.execute("""UPDATE bot_customization
                        SET setting_value=?, updated_at=?
                        WHERE setting_key='disconnect_text'""",
                        (new_disconnect, now))
                else:
                    conn.execute("""INSERT INTO bot_customization
                        (setting_key, setting_value, setting_type, description, created_at, updated_at)
                        VALUES (?,?,?,?,?,?)""",
                        ('disconnect_text', new_disconnect, 'text', 'Текст при отключении бота', now, now))

                conn.commit()

            send_msg(chat_id, "✅ Текст отключения обновлён!\n\nОтключи и подключи бота чтобы увидеть новый текст.")
        except Exception as e:
            send_msg(chat_id, f"❌ Ошибка: {e}")

    elif text == "/initstyles" and is_admin(user_id):
        # ИНИЦИАЛИЗАЦИЯ СТИЛЕЙ ИНЛАЙН КНОПОК В БД
        try:
            from datetime import datetime as dt
            with get_db() as conn:
                now = dt.now().isoformat()

                styles = {
                    'style_edits_on': 'success',
                    'style_edits_off': 'danger',
                    'style_deletes_on': 'success',
                    'style_deletes_off': 'danger',
                    'style_blur_on': 'success',
                    'style_blur_off': 'danger'
                }

                for key, value in styles.items():
                    existing = conn.execute("SELECT setting_key FROM bot_customization WHERE setting_key=?", (key,)).fetchone()

                    if existing:
                        conn.execute("""UPDATE bot_customization
                            SET setting_value=?, updated_at=?
                            WHERE setting_key=?""",
                            (value, now, key))
                    else:
                        conn.execute("""INSERT INTO bot_customization
                            (setting_key, setting_value, setting_type, description, created_at, updated_at)
                            VALUES (?,?,?,?,?,?)""",
                            (key, value, 'style', f'Стиль кнопки {key}', now, now))

                conn.commit()

            send_msg(chat_id, "✅ Стили инлайн кнопок инициализированы!\n\nТеперь зайди в /design → 🎨 Инлайн кнопки")
        except Exception as e:
            send_msg(chat_id, f"❌ Ошибка: {e}")

# ===== WEBHOOK =====
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json(silent=True)
        if not update:
            return "OK", 200

        print(f"[WEBHOOK] keys: {list(update.keys())}", flush=True)

        if "business_connection" in update:
            on_business_connection(update["business_connection"])
        elif "business_message" in update:
            msg = update["business_message"]
            bc_id = msg.get("business_connection_id")
            owner_id = get_owner(bc_id)
            if owner_id:
                on_business_message(msg, owner_id)
        elif "edited_business_message" in update:
            msg = update["edited_business_message"]
            bc_id = msg.get("business_connection_id")
            owner_id = get_owner(bc_id)
            if owner_id:
                on_edited_business_message(msg, owner_id)
        elif "deleted_business_messages" in update:
            on_deleted_business_messages(update["deleted_business_messages"])
        elif "message" in update:
            on_message(update["message"])
        elif "callback_query" in update:
            on_callback(update["callback_query"])
    except Exception as e:
        import traceback
        print(f"[WEBHOOK ERROR] {e}")
        traceback.print_exc()

    return "OK", 200

@app.route('/')
def index():
    return "Bot is running!"

@app.route('/test')
def test():
    return f"<h1>Бот работает!</h1><p>DB_PATH: {DB_PATH}</p><p>WEBHOOK_URL: {WEBHOOK_URL}</p>"

@app.route('/download-db')
def download_database():
    """СКАЧАТЬ БД ПРЯМО В БРАУЗЕР"""
    try:
        return send_file(DB_PATH, as_attachment=True, download_name='spy_database.db')
    except Exception as e:
        return f"Ошибка: {e}"

@app.route('/db-info')
def database_info():
    """ИНФО О БД"""
    try:
        import os
        size = os.path.getsize(DB_PATH)
        with get_db() as conn:
            msg_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        return f"""
        <h2>База данных бота</h2>
        <p>Размер файла: {size} байт</p>
        <p>Сообщений: {msg_count}</p>
        <p>Пользователей: {user_count}</p>
        <a href="/download-db">📥 Скачать БД</a>
        """
    except Exception as e:
        return f"Ошибка: {e}"

# ===== ЗАПУСК =====
# Установка webhook при запуске (только если WEBHOOK_URL задан)
if WEBHOOK_URL:
    api("setWebhook", url=WEBHOOK_URL)
api("setMyCommands", commands=[
    {"command": "start", "description": "Главное меню"},
    {"command": "settings", "description": "Настройки уведомлений"},
    {"command": "stats", "description": "Моя статистика"},
    {"command": "chat", "description": "Экспорт истории чата"},
    {"command": "help", "description": "Помощь и инструкция"},
])

# Для PythonAnywhere НЕ НУЖНО app.run()
# if __name__ == "__main__":
#     port = int(os.environ.get('PORT', 5000))
#     app.run(host='0.0.0.0', port=port, debug=False)