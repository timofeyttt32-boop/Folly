import os
import logging
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

TOKEN = "8866912299:AAEmJdhDuFB_8l6mB1MXMiHi4eGfSthpdQg"

CHECK_URLS = {
    "VK": "https://vk.com/{}",
    "Telegram": "https://t.me/{}",
    "Instagram": "https://instagram.com/{}",
    "TikTok": "https://tiktok.com/@{}",
    "YouTube": "https://youtube.com/@{}",
    "Twitter/X": "https://x.com/{}",
    "Facebook": "https://facebook.com/{}",
    "Pinterest": "https://pinterest.com/{}",
    "Flickr": "https://flickr.com/people/{}",
    "Tumblr": "https://{}.tumblr.com",
    "Medium": "https://medium.com/@{}",
    "SoundCloud": "https://soundcloud.com/{}",
    "Twitch": "https://twitch.tv/{}",
    "LinkedIn": "https://linkedin.com/in/{}",
    "Пикабу": "https://pikabu.ru/@{}",
    "DeviantArt": "https://deviantart.com/{}",
    "Last.fm": "https://last.fm/user/{}",
    "Mastodon": "https://mastodon.social/@{}",
    "Behance": "https://behance.net/{}",
    "Dribbble": "https://dribbble.com/{}",
    "Spotify": "https://open.spotify.com/user/{}",
    "Patreon": "https://patreon.com/{}",
    "Docker Hub": "https://hub.docker.com/u/{}",
    "Bluesky": "https://bsky.app/profile/{}.bsky.social",
    "Vimeo": "https://vimeo.com/{}",
    "Wattpad": "https://wattpad.com/user/{}",
    "Imgur": "https://imgur.com/user/{}",
}

logging.basicConfig(level=logging.INFO)

# ---------- СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЯ ----------
user_mode = {}  # {chat_id: "username" | "phone" | "email"}

# ---------- API-СБОР ----------
async def check_url(session, name, url):
    try:
        async with session.get(url, timeout=10, allow_redirects=True) as r:
            return (name, url, r.status == 200)
    except Exception:
        return (name, url, False)

async def fetch_github(session, u):
    try:
        async with session.get(f"https://api.github.com/users/{u}", timeout=10) as r:
            if r.status != 200: return None
            j = await r.json()
            return {
                "name": j.get("name") or "—",
                "bio": j.get("bio") or "—",
                "location": j.get("location") or "—",
                "company": j.get("company") or "—",
                "email": j.get("email") or "—",
                "blog": j.get("blog") or "—",
                "repos": j.get("public_repos", 0),
                "followers": j.get("followers", 0),
                "created": (j.get("created_at") or "")[:10],
                "url": j.get("html_url"),
            }
    except Exception:
        return None

async def fetch_reddit(session, u):
    try:
        h = {"User-Agent": "SherlockBot/1.0"}
        async with session.get(f"https://www.reddit.com/user/{u}/about.json", headers=h, timeout=10) as r:
            if r.status != 200: return None
            j = await r.json()
            d = j.get("data", {})
            return {
                "name": d.get("name") or "—",
                "karma_post": d.get("link_karma", 0),
                "karma_comment": d.get("comment_karma", 0),
                "url": f"https://reddit.com/user/{u}",
            }
    except Exception:
        return None

async def fetch_gitlab(session, u):
    try:
        async with session.get(f"https://gitlab.com/api/v4/users?username={u}", timeout=10) as r:
            if r.status != 200: return None
            arr = await r.json()
            if not arr: return None
            j = arr[0]
            return {
                "name": j.get("name") or "—",
                "bio": j.get("bio") or "—",
                "location": j.get("location") or "—",
                "created": (j.get("created_at") or "")[:10],
                "url": j.get("web_url"),
            }
    except Exception:
        return None

async def fetch_habr(session, u):
    try:
        async with session.get(f"https://habr.com/kek/v2/users/{u}/", timeout=10) as r:
            if r.status != 200: return None
            j = await r.json()
            return {
                "name": j.get("alias") or u,
                "rating": j.get("rating", 0),
                "karma": j.get("karma", 0),
                "url": f"https://habr.com/ru/users/{u}/",
            }
    except Exception:
        return None

# ---------- СБОР ПО НИКУ ----------
async def gather_by_username(u):
    headers = {"User-Agent": "Mozilla/5.0 SherlockBot"}
    async with aiohttp.ClientSession(headers=headers) as s:
        tasks = [check_url(s, n, url.format(u)) for n, url in CHECK_URLS.items()]
        check = await asyncio.gather(*tasks)
        gh, rd, gl, hb = await asyncio.gather(
            fetch_github(s, u), fetch_reddit(s, u),
            fetch_gitlab(s, u), fetch_habr(s, u),
        )

    found = [(n, url) for n, url, ok in check if ok]
    parts = [f"🔍 Поиск: «{u}»\n"]

    if gh:
        parts.append("━━ GitHub ━━")
        parts.append(f"👤 Имя: {gh['name']}")
        parts.append(f"📝 Bio: {gh['bio']}")
        parts.append(f"📍 Локация: {gh['location']}")
        parts.append(f"🏢 Компания: {gh['company']}")
        if gh['email'] != "—": parts.append(f"✉️ Email: {gh['email']}")
        if gh['blog'] != "—": parts.append(f"🔗 Сайт: {gh['blog']}")
        parts.append(f"📦 Репы: {gh['repos']} | 👥 Followers: {gh['followers']}")
        parts.append(f"📅 Создан: {gh['created']}")
        parts.append(f"🌐 {gh['url']}")
        parts.append("")

    if rd:
        parts.append("━━ Reddit ━━")
        parts.append(f"👤 Имя: {rd['name']}")
        parts.append(f"⭐ Карма: {rd['karma_post']} + {rd['karma_comment']}")
        parts.append(f"🌐 {rd['url']}")
        parts.append("")

    if gl:
        parts.append("━━ GitLab ━━")
        parts.append(f"👤 Имя: {gl['name']}")
        parts.append(f"📝 Bio: {gl['bio']}")
        parts.append(f"📍 Локация: {gl['location']}")
        parts.append(f"📅 Создан: {gl['created']}")
        parts.append(f"🌐 {gl['url']}")
        parts.append("")

    if hb:
        parts.append("━━ Habr ━━")
        parts.append(f"👤 Имя: {hb['name']}")
        parts.append(f"⭐ Рейтинг: {hb['rating']} | Карма: {hb['karma']}")
        parts.append(f"🌐 {hb['url']}")
        parts.append("")

    if found:
        parts.append(f"━━ Профили ({len(found)}) ━━")
        for n, url in found:
            parts.append(f"• {n} — {url}")
    else:
        parts.append("❌ Публичных профилей не найдено.")

    parts.append(f"\n✅ Проверено: {len(CHECK_URLS)}")
    text = "\n".join(parts)
    if len(text) > 4000:
        text = text[:4000] + "\n… обрезано"
    return text

# ---------- СБОР ПО НОМЕРУ ----------
def gather_by_phone(phone):
    d = phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    text = f"📱 Номер: {phone}\n\n"
    text += "Проверь по ссылкам (бесплатные источники):\n\n"
    text += f"• Truecaller — https://www.truecaller.com/search/ru/{d}\n"
    text += f"• Getcontact — https://www.getcontact.com/en/search?q={d}\n"
    text += f"• NumLookup — https://www.numlookup.com/?q={d}\n"
    text += f"• Sync.me — https://sync.me/search/?number=%2B{d}\n"
    text += f"• WhatsApp — https://wa.me/{d}\n"
    text += f"• Telegram — https://t.me/+{d}\n"
    text += f"• Google — https://www.google.com/search?q=%22{d}%22\n"
    text += f"• Yandex — https://yandex.ru/search/?text=%22{d}%22\n"
    text += f"• HIBP — https://haveibeenpwned.com/\n"
    text += "\n⚠️ Автоматический сбор по номеру бесплатно невозможен — нужны платные API."
    return text

# ---------- СБОР ПО EMAIL ----------
def gather_by_email(email):
    e = email.strip()
    text = f"📧 Email: {e}\n\n"
    text += "Проверь по ссылкам:\n\n"
    text += f"• HIBP — https://haveibeenpwned.com/account/{e}\n"
    text += f"• Hunter — https://hunter.io/email-verifier/{e}\n"
    text += f"• Epieos — https://epieos.com/?q={e}\n"
    text += f"• Gravatar — https://www.gravatar.com/{e}\n"
    text += f"• DeHashed — https://dehashed.com/\n"
    text += f"• Google — https://www.google.com/search?q=%22{e}%22\n"
    text += f"• Yandex — https://yandex.ru/search/?text=%22{e}%22\n"
    text += "\n⚠️ Автоматический сбор по email бесплатно ограничен."
    return text

# ---------- КОМАНДЫ ----------
def main_menu():
    kb = [
        [InlineKeyboardButton("👤 По юзернейму", callback_data="mode_username")],
        [InlineKeyboardButton("📱 По номеру", callback_data="mode_phone")],
        [InlineKeyboardButton("📧 По email", callback_data="mode_email")],
    ]
    return InlineKeyboardMarkup(kb)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Sherlock-бот\n\n"
        "Выбери режим поиска:\n\n"
        "👤 По юзернейму — соберу данные с GitHub, Reddit, GitLab, Habr + проверю 27 платформ.\n\n"
        "📱 По номеру — дам ссылки на Truecaller, Getcontact, NumLookup и др.\n\n"
        "📧 По email — дам ссылки на HIBP, Hunter, Epieos и др.",
        reply_markup=main_menu()
    )

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id

    if q.data == "mode_username":
        user_mode[chat_id] = "username"
        await q.edit_message_text("👤 Режим: поиск по юзернейму.\n\nОтправь ник (например: torvalds)")
    elif q.data == "mode_phone":
        user_mode[chat_id] = "phone"
        await q.edit_message_text("📱 Режим: поиск по номеру.\n\nОтправь номер (например: +79001234567)")
    elif q.data == "mode_email":
        user_mode[chat_id] = "email"
        await q.edit_message_text("📧 Режим: поиск по email.\n\nОтправь email (например: user@mail.com)")
    elif q.data == "back":
        user_mode.pop(chat_id, None)
        await q.edit_message_text("🔍 Sherlock-бот\n\nВыбери режим:", reply_markup=main_menu())

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    mode = user_mode.get(chat_id)
    text = update.message.text.strip()

    if mode == "username":
        u = text.lstrip("@")
        if not u or " " in u:
            await update.message.reply_text("Пришли один ник без пробелов.")
            return
        msg = await update.message.reply_text(f"🔎 Собираю данные по «{u}»...")
        try:
            result = await gather_by_username(u)
            await msg.edit_text(result, disable_web_page_preview=True)
        except Exception as e:
            await msg.edit_text(f"Ошибка: {e}")

    elif mode == "phone":
        if not any(c.isdigit() for c in text):
            await update.message.reply_text("Похоже, это не номер. Отправь телефон.")
            return
        await update.message.reply_text(gather_by_phone(text), disable_web_page_preview=True)

    elif mode == "email":
        if "@" not in text:
            await update.message.reply_text("Похоже, это не email. Отправь email.")
            return
        await update.message.reply_text(gather_by_email(text), disable_web_page_preview=True)

    else:
        await update.message.reply_text(
            "Сначала выбери режим:", reply_markup=main_menu()
        )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Sherlock-бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
