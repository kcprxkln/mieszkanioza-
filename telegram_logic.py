import asyncio
import re
import time
from pathlib import Path

from telegram import Bot, LinkPreviewOptions, Update
from telegram.error import TelegramError
from telegram.ext import Application, ContextTypes, MessageHandler, filters

BOT_TOKEN = ""
CHAT_ID_FILE = Path(__file__).with_name("chat_id.txt")
SUBSCRIBE_COMMAND = "!mieszkanioza"


def send_alert(flat: dict) -> bool:
    chat_id = _read_chat_id()
    if chat_id is None:
        print(f"[telegram] no chat registered, send {SUBSCRIBE_COMMAND} to the bot")
        return False

    text = _format(flat)

    try:
        asyncio.run(_send(chat_id, flat.get("image", ""), text))
        sent = True
    except Exception as error:
        print(f"[telegram] send failed: {error}")
        sent = False

    time.sleep(1)
    return sent


def start_listener() -> None:
    _build_application().run_polling(stop_signals=None)


def _build_application() -> Application:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(
        MessageHandler(
            filters.Regex(rf"^{re.escape(SUBSCRIBE_COMMAND)}"), _handle_subscribe
        )
    )
    return application


async def _handle_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    CHAT_ID_FILE.write_text(str(update.effective_chat.id), encoding="utf-8")
    await update.message.reply_text(
        "Zapisane! Od teraz nowe oferty będą wysyłane na ten czat."
    )


def _read_chat_id() -> int | None:
    try:
        value = CHAT_ID_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return int(value) if value else None


def _format(flat: dict) -> str:
    price = flat["price"]
    if flat.get("price_per_m2"):
        price += f" ({flat['price_per_m2']})"

    lines = [
        f"🏠 *[{flat['platform']}]*  Nowa oferta",
        "",
        f"*{flat['title']}*",
        f"💰 Cena: {price}",
    ]

    if flat.get("area"):
        lines.append(f"📐 Powierzchnia: {flat['area']}")
    if flat.get("location"):
        lines.append(f"📍 Lokalizacja: {flat['location']}")

    lines += ["", f"🔗 [Zobacz ogłoszenie]({flat['link']})"]
    return "\n".join(lines)


async def _send(chat_id: int, image_url: str, text: str) -> None:
    async with Bot(BOT_TOKEN) as bot:
        if image_url:
            try:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=image_url,
                    caption=text,
                    parse_mode="Markdown",
                )
                return
            except TelegramError as error:
                print(f"[telegram] photo failed, sending text: {error}")

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
