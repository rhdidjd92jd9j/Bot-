import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask, request

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Example: https://your-app.onrender.com/webhook

app = Flask(__name__)

# Telegram bot Application
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Define /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I am alive on Render!")

telegram_app.add_handler(CommandHandler("start", start))

# Flask route for health check
@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

# Flask route to receive updates
@app.route("/webhook", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK", 200

if __name__ == "__main__":
    # Start webhook
    print("✅ Setting webhook...")
    telegram_app.bot.set_webhook(url=WEBHOOK_URL)

    # Start Flask server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
