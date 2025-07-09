import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)
from huggingface_hub import InferenceClient
from io import BytesIO

app = Flask(__name__)
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
HF_TOKEN = os.environ["HF_TOKEN"]

client = InferenceClient(
    provider="fal-ai",
    api_key=HF_TOKEN,
)

# In-memory user state
user_prompts = {}

# Flask root (for Render)
@app.route('/')
def home():
    return "Telegram HuggingFace Bot Running!"

# Telegram webhook endpoint
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.process_update(update)
    return "ok"

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a prompt to generate an image.")

# Handle prompt message
async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_prompts[user_id] = update.message.text

    # Ask for image ratio
    buttons = [
        [InlineKeyboardButton("1:1", callback_data="1:1")],
        [InlineKeyboardButton("9:16", callback_data="9:16")],
        [InlineKeyboardButton("16:9", callback_data="16:9")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Choose an image ratio:", reply_markup=reply_markup)

# Handle image ratio selection
async def handle_ratio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    prompt = user_prompts.get(user_id)
    ratio = query.data

    size_map = {
        "1:1": (768, 768),
        "9:16": (576, 1024),
        "16:9": (1024, 576),
    }
    width, height = size_map.get(ratio, (768, 768))

    await query.edit_message_text(f"Generating image for: \"{prompt}\" with ratio {ratio}...")

    # Generate image
    image = client.text_to_image(
        prompt,
        model="black-forest-labs/FLUX.1-dev",
        size=(width, height)
    )

    # Send image
    bio = BytesIO()
    image.save(bio, format="PNG")
    bio.seek(0)
    await context.bot.send_photo(chat_id=query.message.chat_id, photo=bio)

# Setup Telegram application
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt))
application.add_handler(CallbackQueryHandler(handle_ratio))
