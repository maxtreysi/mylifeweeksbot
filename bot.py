import os
import re
from datetime import datetime, date, UTC
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ====== ПАРАМЕТРЫ ======
TOTAL_YEARS = 90
WEEKS_PER_YEAR = 52
TOTAL_WEEKS = TOTAL_YEARS * WEEKS_PER_YEAR

W, H = 1080, 1920
BG = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (160, 160, 160)

CELL = 10
GAP = 3

LEFT_AREA = 90      # место под цифры лет слева
RIGHT_AREA = 120    # место под стрелку/подпись справа
TOP_TITLE_H = 170   # зона заголовка
TOP_LABEL_H = 45    # зона цифр недель сверху
BOTTOM_AREA = 220   # зона снизу под подписи/стрелку/заголовок

DATE_PATTERNS = [
    r"^\s*(\d{2})[.\-/](\d{2})[.\-/](\d{4})\s*$",  # 01.01.1990
    r"^\s*(\d{4})[.\-/](\d{2})[.\-/](\d{2})\s*$",  # 1990-01-01
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
    return max(0, (today - born).days // 7)

def load_fonts():
    # максимально близкий к твоему рефу — condensed bold
    try:
        title = ImageFont.truetype("DejaVuSansCondensed-Bold.ttf", 68)
    except:
        title = ImageFont.truetype("DejaVuSans-Bold.ttf", 68)

    try:
        small = ImageFont.truetype("DejaVuSans.ttf", 18)
        bottom = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
        axis = ImageFont.truetype("DejaVuSans.ttf", 18)
    except:
        small = ImageFont.load_default()
        bottom = ImageFont.load_default()
        axis = ImageFont.load_default()

    return title, small, bottom, axis

def text_center_x(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, center_x: int) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    return center_x - tw // 2

def draw_arrow(draw: ImageDraw.ImageDraw, x1, y1, x2, y2, color=BLACK, width=2, head=10):
    # линия
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    # стрелка (простая)
    if x1 == x2:  # вертикальная
        if y2 > y1:
            draw.polygon([(x2, y2), (x2 - head, y2 - head), (x2 + head, y2 - head)], fill=color)
        else:
            draw.polygon([(x2, y2), (x2 - head, y2 + head), (x2 + head, y2 + head)], fill=color)
    elif y1 == y2:  # горизонтальная
        if x2 > x1:
            draw.polygon([(x2, y2), (x2 - head, y2 - head), (x2 - head, y2 + head)], fill=color)
        else:
            draw.polygon([(x2, y2), (x2 + head, y2 - head), (x2 + head, y2 + head)], fill=color)

def make_story_image(born: date, today: date) -> bytes:
    lived = min(weeks_lived(born, today), TOTAL_WEEKS)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    title_f, small_f, bottom_f, axis_f = load_fonts()

    # размеры сетки
    grid_w = WEEKS_PER_YEAR * (CELL + GAP) - GAP
    grid_h = TOTAL_YEARS * (CELL + GAP) - GAP

    # позиционирование: центрируем всю “колонку” (цифры слева + сетка + стрелка справа)
    content_w = LEFT_AREA + grid_w + RIGHT_AREA
    content_x = (W - content_w) // 2

    grid_x = content_x + LEFT_AREA
    grid_y = TOP_TITLE_H + TOP_LABEL_H

    center_x = W // 2

    # Заголовок
    title = "НЕДЕЛИ МОЕЙ ЖИЗНИ"
    tx = text_center_x(d, title, title_f, center_x)
    d.text((tx, 70), title, fill=BLACK, font=title_f)

    # Цифры недель сверху: 4..52 шаг 4
    for n in range(4, 53, 4):
        c = n - 1  # позиция по колонке (1..52) => (0..51)
        x = grid_x + c * (CELL + GAP)
        label = str(n)
        lx = x - (d.textbbox((0, 0), label, font=small_f)[2] // 2)
        d.text((lx, TOP_TITLE_H + 10), label, fill=GRAY, font=small_f)

    # Цифры лет слева: 5..90 шаг 5
    for y in range(5, TOTAL_YEARS + 1, 5):
        r = y - 1  # год 1..90 -> row 0..89
        yy = grid_y + r * (CELL + GAP)
        label = str(y)
        bbox = d.textbbox((0, 0), label, font=small_f)
        lw = bbox[2] - bbox[0]
        d.text((grid_x - 18 - lw, yy - 6), label, fill=GRAY, font=small_f)

    # Сетка
    for i in range(TOTAL_WEEKS):
        r = i // WEEKS_PER_YEAR
        c = i % WEEKS_PER_YEAR
        x = grid_x + c * (CELL + GAP)
        y = grid_y + r * (CELL + GAP)

        fill = BLACK if i < lived else BG
        d.rectangle([x, y, x + CELL, y + CELL], fill=fill, outline=GRAY, width=1)

    # Правая ось/стрелка “ВОЗРАСТ”
    axis_x = grid_x + grid_w + 55
    y1 = grid_y
    y2 = grid_y + grid_h
    draw_arrow(d, axis_x, y1, axis_x, y2, color=BLACK, width=2, head=10)

    # Текст "ВОЗРАСТ" вертикально (рисуем повернутым)
    axis_text = "ВОЗРАСТ"
    tmp = Image.new("RGBA", (300, 60), (255, 255, 255, 0))
    td = ImageDraw.Draw(tmp)
    td.text((0, 0), axis_text, fill=BLACK, font=axis_f)
    tmp = tmp.rotate(90, expand=1)
    img.paste(tmp, (axis_x + 18, (y1 + y2) // 2 - tmp.size[1] // 2), tmp)

    # Нижняя ось “НЕДЕЛИ” со стрелкой
    ax_y = grid_y + grid_h + 70
    draw_arrow(d, grid_x, ax_y, grid_x + grid_w, ax_y, color=BLACK, width=2, head=10)
    # подпись "НЕДЕЛИ" по центру
    weeks_label = "НЕДЕЛИ"
    wx = text_center_x(d, weeks_label, axis_f, grid_x + grid_w // 2)
    d.text((wx, ax_y + 15), weeks_label, fill=BLACK, font=axis_f)

    # Нижний заголовок
    bottom = "90 ЛЕТ ЖИЗНИ В НЕДЕЛЯХ"
    bx = text_center_x(d, bottom, bottom_f, center_x)
    d.text((bx, H - 120), bottom, fill=BLACK, font=bottom_f)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

# ====== TELEGRAM ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет. Напиши мне свою дату рождения в формате 01.01.1990 и я пришлю тебе твой календарь жизни"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    born = parse_birthdate(update.message.text if update.message else "")
    if not born:
        await update.message.reply_text("Формат даты: 01.01.1990")
        return

    today = datetime.now(UTC).date()
    png = make_story_image(born, today)
    await update.message.reply_photo(photo=png)

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
