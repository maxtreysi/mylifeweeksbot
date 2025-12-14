import os
import re
from datetime import datetime, date
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOTAL_YEARS = 90
WEEKS_PER_YEAR = 52
TOTAL_WEEKS = TOTAL_YEARS * WEEKS_PER_YEAR

# Визуал (белый фон)
CELL = 10          # размер квадрата
GAP = 2            # расстояние между квадратами
MARGIN = 24        # отступы по краям
HEADER_H = 90      # место под заголовок/текст
BG = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (210, 210, 210)

DATE_PATTERNS = [
    r"^\s*(\d{2})[.\-\/](\d{2})[.\-\/](\d{4})\s*$",  # dd.mm.yyyy
    r"^\s*(\d{4})[.\-\/](\d{2})[.\-\/](\d{2})\s*$",  # yyyy-mm-dd
]

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
    if born > today:
        return 0
    days = (today - born).days
    return max(0, days // 7)

def make_image(born: date, today: date) -> tuple[bytes, str]:
    lived = min(weeks_lived(born, today), TOTAL_WEEKS)
    left = TOTAL_WEEKS - lived
    pct = (lived / TOTAL_WEEKS) * 100

    grid_w = WEEKS_PER_YEAR * CELL + (WEEKS_PER_YEAR - 1) * GAP
    grid_h = TOTAL_YEARS * CELL + (TOTAL_YEARS - 1) * GAP

    img_w = MARGIN * 2 + grid_w
    img_h = MARGIN * 2 + HEADER_H + grid_h

    img = Image.new("RGB", (img_w, img_h), BG)
    d = ImageDraw.Draw(img)

    # Шрифты (если DejaVu не найдётся — будет дефолт)
    try:
        font_title = ImageFont.truetype("DejaVuSans.ttf", 28)
        font_text = ImageFont.truetype("DejaVuSans.ttf", 18)
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()

    title = "Твоя жизнь в неделях (90 лет)"
    subtitle = f"Родился: {born.strftime('%d.%m.%Y')}  •  Сегодня: {today.strftime('%d.%m.%Y')}"
    stats = f"Прожито: {lived} недель ({pct:.1f}%)  •  Осталось: {left} недель"

    d.text((MARGIN, MARGIN), title, fill=BLACK, font=font_title)
    d.text((MARGIN, MARGIN + 38), subtitle, fill=BLACK, font=font_text)
    d.text((MARGIN, MARGIN + 62), stats, fill=BLACK, font=font_text)

    x0 = MARGIN
    y0 = MARGIN + HEADER_H

    for i in range(TOTAL_WEEKS):
        r = i // WEEKS_PER_YEAR
        c = i % WEEKS_PER_YEAR
        x = x0 + c * (CELL + GAP)
        y = y0 + r * (CELL + GAP)

        fill = BLACK if i < lived else BG
        d.rectangle([x, y, x + CELL, y + CELL], fill=fill, outline=GRAY)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    caption = (
        f"🗓 {born.strftime('%d.%m.%Y')}\n"
        f"⬛ Прожито: {lived} недель\n"
        f"⬜ Осталось: {left} недель\n"
        f"📌 Это грубая оценка (деление дней на 7)."
    )
    return buf.getvalue(), caption
def make_story_image(born: date, today: date) -> bytes:
    lived = min(weeks_lived(born, today), TOTAL_WEEKS)

    WIDTH = 1080
    HEIGHT = 1920
    TOP_MARGIN = 260
    GRID_TOP = 420

    CELL_S = 14
    GAP_S = 4

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("DejaVuSans.ttf", 56)
        font_text = ImageFont.truetype("DejaVuSans.ttf", 36)
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()

    d.text((WIDTH // 2 - 260, TOP_MARGIN), "ТВОЯ ЖИЗНЬ В НЕДЕЛЯХ", fill=BLACK, font=font_title)
    d.text(
        (WIDTH // 2 - 280, TOP_MARGIN + 70),
        f"Родился: {born.strftime('%d.%m.%Y')}",
        fill=BLACK,
        font=font_text,
    )

    start_x = (WIDTH - (WEEKS_PER_YEAR * (CELL_S + GAP_S))) // 2
    y = GRID_TOP

    for i in range(TOTAL_WEEKS):
        r = i // WEEKS_PER_YEAR
        c = i % WEEKS_PER_YEAR

        x = start_x + c * (CELL_S + GAP_S)
        y = GRID_TOP + r * (CELL_S + GAP_S)

        fill = BLACK if i < lived else BG
        d.rectangle([x, y, x + CELL_S, y + CELL_S], fill=fill, outline=GRAY)

    footer = "Сколько осталось — решаешь ты"
    d.text((WIDTH // 2 - 260, HEIGHT - 180), footer, fill=BLACK, font=font_text)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Пришли дату рождения в формате:\n"
        "• 02.03.2000\n"
        "или\n"
        "• 2000-03-02\n\n"
        "Я пришлю картинку: 90 лет жизни в неделях."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    born = parse_birthdate(update.message.text if update.message else "")
    if not born:
        await update.message.reply_text("Не понял дату 😅 Напиши так: 02.03.2000 (или 2000-03-02).")
        return

    today = datetime.utcnow().date()

    if born > today:
        await update.message.reply_text("Дата рождения не может быть позже сегодняшней 🙂")
        return
    if (today.year - born.year) > 120:
        await update.message.reply_text("Проверь дату, пожалуйста — выглядит слишком далёкой.")
        return

    png_bytes, caption = make_image(born, today)
    await update.message.reply_photo(photo=png_bytes, caption=caption)
story_png = make_story_image(born, today)
await update.message.reply_photo(
    photo=story_png,
    caption="📲 Версия для сторис\nОтметь себя и поделись"
)
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Не найден BOT_TOKEN в переменных окружения Render.")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
