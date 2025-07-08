import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load bot token from environment variable named TELEGRAM_BOT_TOKEN
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# Define /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I am alive on Render!")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("✅ Bot started...")
    app.run_polling()
