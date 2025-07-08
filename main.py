import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask, request

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # e.g. https://your-app.onrender.com/webhook

# Flask server
flask_app = Flask(__name__)

# Telegram bot Application
tg_app = ApplicationBuilder().token(BOT_TOKEN).build()

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I am alive on Render!")

tg_app.add_handler(CommandHandler("start", start))

# Flask route for health check
@flask_app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

# Flask route to receive webhook updates
@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, tg_app.bot)
    await tg_app.process_update(update)
    return "OK", 200

if __name__ == "__main__":
    # Set the webhook once before starting
    print("✅ Setting webhook...")
    tg_app.bot.set_webhook(url=WEBHOOK_URL)

    # Start Flask server
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
