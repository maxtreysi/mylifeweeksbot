from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 👋\n\n"
        "Скоро здесь будет бот, который покажет твою жизнь в неделях.\n"
        "Пока что он просто проверяет, что всё работает 🙂"
    )

def main():
    token = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
