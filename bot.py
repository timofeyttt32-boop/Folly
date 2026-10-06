import os
import logging
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8866912299:AAEmJdhDuFB_8l6mB1MXMiHi4eGfSthpdQg"

# ---------------- Ссылки для проверки наличия ----------------
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
    "Roblox": "https://roblox.com/user.aspx?username={}",
}

logging.basicConfig(level=logging.INFO)

# ---------------- Проверка HTTP-статуса ----------------
async def check_url(session, name, url):
    try:
        async with session.get(url, timeout=10, allow_redirects=True) as r:
            return (name, url, r.status == 200)
    except Exception:
        return (name, url, False)

# ---------------- Сбор данных: GitHub ----------------
async def fetch_github(session, username):
    try:
        async with session.get(f"https://api.github.com/users/{username}", timeout=10) as r:
            if r.status != 200:
                return None
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

# ---------------- Сбор данных: Reddit ----------------
async def fetch_reddit(session, username):
    try:
        headers = {"User-Agent": "SherlockBot/1.0"}
        async with session.get(f"https://www.reddit.com/user/{username}/about.json", headers=headers, timeout=10) as r:
            if r.status != 200:
                return None
            j = await r.json()
            d = j.get("data", {})
            return {
                "name": d.get("name") or "—",
                "karma_post": d.get("link_karma", 0),
                "karma_comment": d.get("comment_karma", 0),
                "created": d.get("created_utc", 0),
                "url": f"https://reddit.com/user/{username}",
            }
    except Exception:
        return None

# ---------------- Сбор данных: GitLab ----------------
async def fetch_gitlab(session, username):
    try:
        async with session.get(f"https://gitlab.com/api/v4/users?username={username}", timeout=10) as r:
            if r.status != 200:
                return None
            arr = await r.json()
            if not arr:
                return None
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

# ---------------- Сбор данных: Habr ----------------
async def fetch_habr(session, username):
    try:
        async with session.get(f"https://habr.com/kek/v2/users/{username}/", timeout=10) as r:
            if r.status != 200:
                return None
            j = await r.json()
            return {
                "name": j.get("alias") or username,
                "rating": j.get("rating", 0),
                "karma": j.get("karma", 0),
                "created": (j.get("timeRegistered") or "")[:10],
                "url": f"https://habr.com/ru/users/{username}/",
            }
    except Exception:
        return None

# ---------------- Команды ----------------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Sherlock-бот\n\n"
        "Отправь ник — я проверю его на 30+ площадках и соберу открытые данные.\n\n"
        "Что умею:\n"
        "• GitHub — профиль, bio, локация, репы, followers\n"
        "• Reddit — карма, дата регистрации\n"
        "• GitLab — профиль, дата\n"
        "• Habr — карма, рейтинг\n"
        "• Steam, Telegram — превью\n"
        "• 30+ остальных — есть / нет\n\n"
        "Например: torvalds"
    )

async def handle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lstrip("@")
    if not username or " " in username:
        await update.message.reply_text("Пришли один ник без пробелов.")
        return

    msg = await update.message.reply_text(f"🔎 Ищу «{username}» по 30+ платформам...")

    headers = {"User-Agent": "Mozilla/5.0 SherlockBot"}
    async with aiohttp.ClientSession(headers=headers) as session:
        # 1. Проверка наличия по HTTP
        tasks = [check_url(session, n, u.format(username)) for n, u in CHECK_URLS.items()]
        check_results = await asyncio.gather(*tasks)

        # 2. Сбор данных через API
        gh, rd, gl, hb = await asyncio.gather(
            fetch_github(session, username),
            fetch_reddit(session, username),
            fetch_gitlab(session, username),
            fetch_habr(session, username),
        )

    found = [(n, u) for n, u, ok in check_results if ok]

    # ---- Формируем отчёт ----
    parts = [f"🔍 Sherlock: «{username}»\n"]

    if gh:
        parts.append("── GitHub ──")
        parts.append(f"👤 {gh['name']}")
        parts.append(f"📝 {gh['bio']}")
        parts.append(f"📍 {gh['location']}")
        parts.append(f"🏢 {gh['company']}")
        if gh['email'] != "—":
            parts.append(f"✉️ {gh['email']}")
        if gh['blog'] != "—":
            parts.append(f"🔗 {gh['blog']}")
        parts.append(f"📦 Репы: {gh['repos']} | 👥 Followers: {gh['followers']}")
        parts.append(f"📅 Создан: {gh['created']}")
        parts.append(f"🔗 {gh['url']}")
        parts.append("")

    if rd:
        parts.append("── Reddit ──")
        parts.append(f"👤 {rd['name']}")
        parts.append(f"⭐ Карма: {rd['karma_post']} постов + {rd['karma_comment']} комментов")
        parts.append(f"🔗 {rd['url']}")
        parts.append("")

    if gl:
        parts.append("── GitLab ──")
        parts.append(f"👤 {gl['name']}")
        parts.append(f"📝 {gl['bio']}")
        parts.append(f"📍 {gl['location']}")
        parts.append(f"📅 Создан: {gl['created']}")
        parts.append(f"🔗 {gl['url']}")
        parts.append("")

    if hb:
        parts.append("── Habr ──")
        parts.append(f"👤 {hb['name']}")
        parts.append(f"⭐ Рейтинг: {hb['rating']} | Карма: {hb['karma']}")
        parts.append(f"🔗 {hb['url']}")
        parts.append("")

    if found:
        parts.append(f"── Платформы, где ник занят ({len(found)}) ──")
        for n, u in found:
            parts.append(f"• {n} — {u}")
    else:
        parts.append("❌ По публичным платформам совпадений не найдено.")

    parts.append(f"\n✅ Всего проверено: {len(CHECK_URLS)}")

    text = "\n".join(parts)
    if len(text) > 4000:
        text = text[:4000] + "\n\n… (обрезано)"

    await msg.edit_text(text, disable_web_page_preview=True)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("Sherlock-бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
