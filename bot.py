import os
import re
from datetime import datetime, date
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== НАСТРОЙКИ ==================
TOTAL_YEARS = 90
WEEKS_PER_YEAR = 52
TOTAL_WEEKS = TOTAL_YEARS * WEEKS_PER_YEAR

WIDTH = 1080
HEIGHT = 1920

BG = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (180, 180, 180)

CELL = 14
GAP = 4

GRID_TOP = 260
GRID_LEFT = 140

DATE_PATTERNS = [
    r"^\s*(\d{2})[.\-/](\d{2})[.\-/](\d{4})\s*$",
    r"^\s*(\d{4})[.\-/](\d{2})[.\-/](\d{2})\s*$",
]

# ================== УТИЛИТЫ ==================
def parse_birthdate(text: str) -> date | None:
    text = (text or "").strip()
    for pat in DATE_PATTERNS:
        m = re.match(pat, text)
        if not m:
            continue
        parts = list(map(int, m.groups()))
        try:
            if pat.startswith(r"^\s*(\d{2})"):
                dd, mm, yyyy = parts
            else:
                yyyy, mm, dd = parts
            return date(yyyy, mm, dd)
        except ValueError:
            return None
    return None


def weeks_lived(born: date, today: date) -> int:
    return max(0, (today - born).days // 7)


# ================== КАРТИНКА ==================
def make_story_image(born: date, today: date) -> bytes:
    lived = min(weeks_lived(born, today), TOTAL_WEEKS)

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Заголовок
    d.text((WIDTH // 2 - 320, 120), "НЕДЕЛИ МОЕЙ ЖИЗНИ", fill=BLACK, font=title_font)

    # Подписи недель сверху
    for i in range(0, 53, 4):
        x = GRID_LEFT + i * (CELL + GAP)
        d.text((x, GRID_TOP - 40), str(i), fill=GRAY, font=text_font)

    # Подписи лет слева
    for year in range(0, TOTAL_YEARS + 1, 5):
        y = GRID_TOP + year * (CELL + GAP)
        d.text((60, y - 6), str(year), fill=GRAY, font=text_font)

    # Сетка
    for i in range(TOTAL_WEEKS):
        r = i // WEEKS_PER_YEAR
        c = i % WEEKS_PER_YEAR

        x = GRID_LEFT + c * (CELL + GAP)
        y = GRID_TOP + r * (CELL + GAP)

        fill = BLACK if i < lived else BG
        d.rectangle(
            [x, y, x + CELL, y + CELL],
            fill=fill,
            outline=GRAY,
            width=1,
        )

    # Нижний текст
    d.text(
        (WIDTH // 2 - 260, HEIGHT - 120),
        "90 ЛЕТ ЖИЗНИ В НЕДЕЛЯХ",
        fill=BLACK,
        font=text_font,
    )

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ================== TELEGRAM ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет. Напиши мне свою дату рождения в формате 01.01.1990 "
        "и я пришлю тебе твой календарь жизни"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    born = parse_birthdate(update.message.text if update.message else "")
    if not born:
        await update.message.reply_text("Формат даты: 01.01.1990")
        return

    today = datetime.utcnow().date()
    img = make_story_image(born, today)

    await update.message.reply_photo(photo=img)


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не найден")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()


if __name__ == "__main__":
    main()
