import os
import logging
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

PLATFORMS = {
    "VK": "https://vk.com/{}",
    "Telegram": "https://t.me/{}",
    "Instagram": "https://instagram.com/{}",
    "GitHub": "https://github.com/{}",
    "GitLab": "https://gitlab.com/{}",
    "Reddit": "https://reddit.com/user/{}",
    "YouTube": "https://youtube.com/@{}",
    "TikTok": "https://tiktok.com/@{}",
    "Steam": "https://steamcommunity.com/id/{}",
    "Pinterest": "https://pinterest.com/{}",
    "Flickr": "https://flickr.com/people/{}",
    "Tumblr": "https://{}.tumblr.com",
    "Medium": "https://medium.com/@{}",
    "SoundCloud": "https://soundcloud.com/{}",
    "Twitch": "https://twitch.tv/{}",
    "Twitter": "https://x.com/{}",
    "LinkedIn": "https://linkedin.com/in/{}",
    "Habr": "https://habr.com/ru/users/{}/",
    "Пикабу": "https://pikabu.ru/@{}",
    "DeviantArt": "https://deviantart.com/{}",
    "Last.fm": "https://last.fm/user/{}",
    "Mastodon": "https://mastodon.social/@{}",
    "Behance": "https://behance.net/{}",
    "Dribbble": "https://dribbble.com/{}",
}

logging.basicConfig(level=logging.INFO)

async def check(session, name, url):
    try:
        async with session.get(url, timeout=8, allow_redirects=True) as r:
            return (name, url, r.status == 200)
    except Exception:
        return (name, url, False)

async def scan(session, username):
    tasks = [check(session, name, url.format(username)) for name, url in PLATFORMS.items()]
    return await asyncio.gather(*tasks)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Sherlock-бот\n\nОтправь ник — проверю на 24 платформах.")

async def handle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lstrip("@")
    if not username or " " in username:
        await update.message.reply_text("Пришли один ник без пробелов.")
        return
    msg = await update.message.reply_text(f"Ищу «{username}»...")
    async with aiohttp.ClientSession(headers={"User-Agent":"Mozilla/5.0"}) as s:
        results = await scan(s, username)
    found = [(n,u) for n,u,ok in results if ok]
    lines = [f"🔍 Результаты для «{username}»\n"]
    if found:
        lines.append(f"✅ Найдено: {len(found)}\n")
        for n,u in found:
            lines.append(f"• {n} — {u}")
    else:
        lines.append("❌ Ничего не найдено.")
    lines.append(f"\nПроверено: {len(results)}")
    await msg.edit_text("\n".join(lines), disable_web_page_preview=True)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
