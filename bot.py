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

# ---------------- 30+ площадок для проверки ----------------
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
    "Steam": "https://steamcommunity.com/id/{}",
    "Roblox": "https://roblox.com/user.aspx?username={}",
    "Fiverr": "https://fiverr.com/{}",
    "Kaggle": "https://kaggle.com/{}",
    "CodePen": "https://codepen.io/{}",
    "Replit": "https://replit.com/@{}",
    "ProductHunt": "https://producthunt.com/@{}",
}

logging.basicConfig(level=logging.INFO)

# ---------------- СОСТОЯНИЕ ----------------
user_mode = {}

# ---------------- HTTP-проверка ----------------
async def check_url(session, name, url):
    try:
        async with session.get(url, timeout=10, allow_redirects=True) as r:
            return (name, url, r.status == 200)
    except Exception:
        return (name, url, False)

# ---------------- СБОР ПО API ----------------
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
                "gists": j.get("public_gists", 0),
                "followers": j.get("followers", 0),
                "following": j.get("following", 0),
                "created": (j.get("created_at") or "")[:10],
                "updated": (j.get("updated_at") or "")[:10],
                "avatar": j.get("avatar_url"),
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
                "created": d.get("created_utc", 0),
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

# ---------------- СБОР ПО НИКУ ----------------
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
    out = [f"🔍 <b>Поиск: {u}</b>\n"]

    if gh:
        out.append("<b>━━ GitHub ━━</b>")
        out.append(f"👤 Имя: {gh['name']}")
        out.append(f"📝 Bio: {gh['bio']}")
        out.append(f"📍 Локация: {gh['location']}")
        out.append(f"🏢 Компания: {gh['company']}")
        if gh['email'] != "—": out.append(f"✉️ Email: {gh['email']}")
        if gh['blog'] != "—": out.append(f"🔗 Сайт: {gh['blog']}")
        out.append(f"📦 Репы: {gh['repos']} | Gists: {gh['gists']}")
        out.append(f"👥 Followers: {gh['followers']} | Following: {gh['following']}")
        out.append(f"📅 Создан: {gh['created']}")
        out.append(f"🌐 {gh['url']}")
        out.append("")

    if rd:
        out.append("<b>━━ Reddit ━━</b>")
        out.append(f"👤 Имя: {rd['name']}")
        out.append(f"⭐ Карма: {rd['karma_post']} постов + {rd['karma_comment']} комментов")
        out.append(f"🌐 {rd['url']}")
        out.append("")

    if gl:
        out.append("<b>━━ GitLab ━━</b>")
        out.append(f"👤 Имя: {gl['name']}")
        out.append(f"📝 Bio: {gl['bio']}")
        out.append(f"📍 Локация: {gl['location']}")
        out.append(f"📅 Создан: {gl['created']}")
        out.append(f"🌐 {gl['url']}")
        out.append("")

    if hb:
        out.append("<b>━━ Habr ━━</b>")
        out.append(f"👤 Имя: {hb['name']}")
        out.append(f"⭐ Рейтинг: {hb['rating']} | Карма: {hb['karma']}")
        out.append(f"🌐 {hb['url']}")
        out.append("")

    if found:
        out.append(f"<b>━━ Профили ({len(found)}) ━━</b>")
        for n, url in found:
            out.append(f"• <a href='{url}'>{n}</a>")
    else:
        out.append("❌ Публичных профилей не найдено.")

    out.append(f"\n✅ Проверено: {len(CHECK_URLS)} платформ")
    text = "\n".join(out)
    if len(text) > 4000:
        text = text[:4000] + "\n… обрезано"
    return text

# ---------------- ПО НОМЕРУ ----------------
def gather_by_phone(phone):
    d = "".join(c for c in phone if c.isdigit())
    t = f"📱 <b>Номер: {phone}</b>\n\n"
    t += "<b>━━ Проверь по ссылкам ━━</b>\n\n"
    t += f"• <a href='https://www.truecaller.com/search/ru/{d}'>Truecaller</a>\n"
    t += f"• <a href='https://www.getcontact.com/en/search?q={d}'>Getcontact</a>\n"
    t += f"• <a href='https://www.numlookup.com/?q={d}'>NumLookup</a>\n"
    t += f"• <a href='https://sync.me/search/?number=%2B{d}'>Sync.me</a>\n"
    t += f"• <a href='https://wa.me/{d}'>WhatsApp</a>\n"
    t += f"• <a href='https://t.me/+{d}'>Telegram</a>\n"
    t += f"• <a href='https://www.google.com/search?q=%22{d}%22'>Google</a>\n"
    t += f"• <a href='https://yandex.ru/search/?text=%22{d}%22'>Yandex</a>\n"
    t += f"• <a href='https://haveibeenpwned.com/'>HIBP</a>\n\n"
    t += "⚠️ Автоматический сбор по номеру бесплатно невозможен — нужны платные API."
    return t

# ---------------- ПО EMAIL ----------------
def gather_by_email(email):
    e = email.strip()
    t = f"📧 <b>Email: {e}</b>\n\n"
    t += "<b>━━ Проверь по ссылкам ━━</b>\n\n"
    t += f"• <a href='https://haveibeenpwned.com/account/{e}'>HIBP</a>\n"
    t += f"• <a href='https://hunter.io/email-verifier/{e}'>Hunter</a>\n"
    t += f"• <a href='https://epieos.com/?q={e}'>Epieos</a>\n"
    t += f"• <a href='https://www.gravatar.com/{e}'>Gravatar</a>\n"
    t += f"• <a href='https://www.google.com/search?q=%22{e}%22'>Google</a>\n"
    t += f"• <a href='https://yandex.ru/search/?text=%22{e}%22'>Yandex</a>\n\n"
    t += "⚠️ Автоматический сбор по email бесплатно ограничен."
    return t

# ---------------- МЕНЮ ----------------
def main_menu():
    kb = [
        [InlineKeyboardButton("👤 По юзернейму", callback_data="mode_username")],
        [InlineKeyboardButton("📱 По номеру", callback_data="mode_phone")],
        [InlineKeyboardButton("📧 По email", callback_data="mode_email")],
        [InlineKeyboardButton("ℹ️ Что умею", callback_data="about")],
    ]
    return InlineKeyboardMarkup(kb)

def back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")]])

# ---------------- ХЭНДЛЕРЫ ----------------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 <b>Sherlock Bot</b>\n\n"
        "Привет! Я ищу публичную информацию по нику, номеру и email.\n\n"
        "Выбери режим ниже 👇",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

async def about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "ℹ️ <b>Что я умею</b>\n\n"
        "<b>👤 По юзернейму:</b>\n"
        "Автоматически собираю данные с GitHub, Reddit, GitLab, Habr.\n"
        "Проверяю 34+ платформы: занят ник или нет.\n\n"
        "<b>📱 По номеру:</b>\n"
        "Даю ссылки на Truecaller, Getcontact, NumLookup, HIBP и др.\n\n"
        "<b>📧 По email:</b>\n"
        "Даю ссылки на HIBP, Hunter, Epieos, Gravatar и др.\n\n"
        "Бесплатно работает всё, кроме автоматического поиска по номеру и email — для них нужны платные API.",
        reply_markup=back_menu(),
        parse_mode="HTML"
    )

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id

    if q.data == "mode_username":
        user_mode[chat_id] = "username"
        await q.edit_message_text(
            "👤 <b>Режим: юзернейм</b>\n\nОтправь ник (например: torvalds)",
            reply_markup=back_menu(), parse_mode="HTML"
        )
    elif q.data == "mode_phone":
        user_mode[chat_id] = "phone"
        await q.edit_message_text(
            "📱 <b>Режим: номер</b>\n\nОтправь телефон (например: +79001234567)",
            reply_markup=back_menu(), parse_mode="HTML"
        )
    elif q.data == "mode_email":
        user_mode[chat_id] = "email"
        await q.edit_message_text(
            "📧 <b>Режим: email</b>\n\nОтправь email (например: user@mail.com)",
            reply_markup=back_menu(), parse_mode="HTML"
        )
    elif q.data == "about":
        await about(update, ctx)
    elif q.data == "back":
        user_mode.pop(chat_id, None)
        await q.edit_message_text(
            "🔍 <b>Sherlock Bot</b>\n\nВыбери режим:",
            reply_markup=main_menu(), parse_mode="HTML"
        )

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
            await msg.edit_text(result, disable_web_page_preview=True, parse_mode="HTML")
        except Exception as e:
            await msg.edit_text(f"Ошибка: {e}")

    elif mode == "phone":
        if not any(c.isdigit() for c in text):
            await update.message.reply_text("Похоже, это не номер.")
            return
        await update.message.reply_text(gather_by_phone(text), disable_web_page_preview=True, parse_mode="HTML")

    elif mode == "email":
        if "@" not in text:
            await update.message.reply_text("Похоже, это не email.")
            return
        await update.message.reply_text(gather_by_email(text), disable_web_page_preview=True, parse_mode="HTML")

    else:
        await update.message.reply_text("Сначала выбери режим:", reply_markup=main_menu())

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Sherlock Bot запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
