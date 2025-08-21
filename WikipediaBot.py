import os
import logging
import asyncio
from functools import partial

import wikipediaapi
import psycopg2
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, filters

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "weatherbot_db")
DB_USER = os.getenv("DB_USER", "weatherbot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
WIKI_USER_AGENT = os.getenv("WIKI_USER_AGENT", "WikiBot/1.0 (contact: your_email@example.com)")

TEXTS = {
    "ru": {
        "start": "Я бот. Отправь запрос — я найду краткое описание в Википедии.",
        "help": "/start, /help, /setlang — выбрать язык поиска (ru/en).",
        "lang_prompt": "Выберите язык:",
        "lang_set": "Язык установлен: {lang}",
        "not_found": 'Не найдено: "{q}"',
        "found": 'Результат для "{q}":\n\n{summary}',
    },
    "en": {
        "start": "I'm a bot. Send a query — I'll fetch a summary from Wikipedia.",
        "help": "/start, /help, /setlang — choose search language (ru/en).",
        "lang_prompt": "Select language:",
        "lang_set": "Language set: {lang}",
        "not_found": 'Not found: "{q}"',
        "found": 'Result for "{q}":\n\n{summary}',
    },
}

DB_KW = {
    "host": DB_HOST,
    "port": DB_PORT,
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "options": "-c client_encoding=UTF8",
}

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS user_interactions (
  id SERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  username TEXT,
  query_text TEXT,
  response_text TEXT,
  language VARCHAR(10),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

def ensure_table():
    try:
        conn = psycopg2.connect(**DB_KW)
        conn.set_client_encoding("UTF8")
        with conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_SQL)
        conn.close()
    except Exception as e:
        logger.exception("DB init failed: %r", e)
        # don't crash—bot can run even if DB not available

def _log_sync(user_id, username, q, resp, lang):
    try:
        conn = psycopg2.connect(**DB_KW)
        conn.set_client_encoding("UTF8")
        if resp and len(resp) > 4000:
            resp = resp[:4000]
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO user_interactions (user_id, username, query_text, response_text, language) VALUES (%s,%s,%s,%s,%s)",
                    (user_id, username, q, resp, lang),
                )
        conn.close()
    except Exception:
        logger.exception("Failed to write interaction")

async def log_interaction(user_id, username, q, resp, lang):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, partial(_log_sync, user_id, username, q, resp, lang))

def wiki_summary(q, lang="ru"):
    try:
        wiki = wikipediaapi.Wikipedia(user_agent=WIKI_USER_AGENT, language=lang)
        p = wiki.page(q)
        if p.exists():
            return (p.summary or "").strip()[:1000]
        return None
    except AssertionError as e:
        logger.exception("Wikipedia: user-agent error: %s", e)
        return None
    except Exception:
        logger.exception("Wikipedia error")
        return None

def get_user_lang(context: CallbackContext):
    return context.user_data.get("language", "ru")

def keyboard_commands():
    return ReplyKeyboardMarkup([["/start", "/help", "/setlang"]], resize_keyboard=True)

async def start(update: Update, context: CallbackContext):
    lang = get_user_lang(context)
    txt = TEXTS[lang]["start"]
    await update.message.reply_html(f"{update.effective_user.mention_html()} {txt}", reply_markup=keyboard_commands())
    asyncio.create_task(log_interaction(update.effective_user.id, update.effective_user.username or "", "/start", txt, lang))

async def help_cmd(update: Update, context: CallbackContext):
    lang = get_user_lang(context)
    txt = TEXTS[lang]["help"]
    await update.message.reply_text(txt, reply_markup=keyboard_commands())
    asyncio.create_task(log_interaction(update.effective_user.id, update.effective_user.username or "", "/help", txt, lang))

async def setlang(update: Update, context: CallbackContext):
    lang_cur = get_user_lang(context)
    if context.args:
        chosen = context.args[0].lower()
        if chosen in ("ru", "en"):
            context.user_data["language"] = chosen
            txt = TEXTS[chosen]["lang_set"].format(lang=chosen)
            await update.message.reply_text(txt, reply_markup=keyboard_commands())
            asyncio.create_task(log_interaction(update.effective_user.id, update.effective_user.username or "", f"/setlang {chosen}", txt, chosen))
            return
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("Русский", callback_data="setlang:ru"), InlineKeyboardButton("English", callback_data="setlang:en")]])
    await update.message.reply_text(TEXTS[lang_cur]["lang_prompt"], reply_markup=markup)

async def setlang_cb(update: Update, context: CallbackContext):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    if data.startswith("setlang:"):
        chosen = data.split(":",1)[1]
        if chosen in ("ru","en"):
            context.user_data["language"] = chosen
            txt = TEXTS[chosen]["lang_set"].format(lang=chosen)
            try:
                await q.edit_message_reply_markup(None)
            except:
                pass
            await q.message.reply_text(txt, reply_markup=keyboard_commands())
            asyncio.create_task(log_interaction(q.from_user.id, q.from_user.username or "", f"setlang_cb:{chosen}", txt, chosen))

async def on_message(update: Update, context: CallbackContext):
    q = update.message.text.strip()
    if not q:
        return
    lang = get_user_lang(context)
    summary = wiki_summary(q, lang)
    if summary:
        txt = TEXTS[lang]["found"].format(q=q, summary=summary)
        await update.message.reply_text(txt)
        asyncio.create_task(log_interaction(update.effective_user.id, update.effective_user.username or "", q, summary, lang))
    else:
        txt = TEXTS[lang]["not_found"].format(q=q)
        await update.message.reply_text(txt)
        asyncio.create_task(log_interaction(update.effective_user.id, update.effective_user.username or "", q, txt, lang))

async def error_handler(update: object, context: CallbackContext):
    logger.exception("Handler error: %s", context.error)

def main():
    if not TG_BOT_TOKEN:
        logger.error("TG_BOT_TOKEN not set")
        return
    ensure_table()
    app = Application.builder().token(TG_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("setlang", setlang))
    app.add_handler(CallbackQueryHandler(setlang_cb, pattern=r"^setlang:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_error_handler(error_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
