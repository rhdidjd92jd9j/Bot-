import os
import io
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler
from huggingface_hub import InferenceClient
from PIL import Image

# --- Basic Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# It's highly recommended to use environment variables for these tokens
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
# The URL your Render web service is running on. Example: "https://your-bot.onrender.com"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# --- Hugging Face Client ---
try:
    client = InferenceClient(
        provider="fal-ai",
        api_key=HF_TOKEN,
    )
except Exception as e:
    logger.error(f"Failed to initialize Hugging Face client: {e}")
    client = None

# --- Conversation States ---
PROMPT, RATIO = range(2)

# --- Bot Functions ---

async def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks for a prompt."""
    await update.message.reply_text(
        "Hi! I can create an image for you based on a text prompt. ✨\n\n"
        "Please send me the prompt you'd like to use."
    )
    return PROMPT

async def get_prompt(update: Update, context: CallbackContext) -> int:
    """Stores the prompt and asks for the image ratio."""
    context.user_data['prompt'] = update.message.text
    logger.info(f"Received prompt: {update.message.text}")

    keyboard = [
        [
            InlineKeyboardButton("■ 1:1", callback_data='1:1'),
            InlineKeyboardButton("▬ 16:9", callback_data='16:9'),
            InlineKeyboardButton("▮ 9:16", callback_data='9:16'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Great! Now, please select your desired image aspect ratio:', reply_markup=reply_markup)
    return RATIO

async def generate_image(update: Update, context: CallbackContext) -> int:
    """Generates the image using the prompt and selected ratio."""
    query = update.callback_query
    await query.answer()
    ratio = query.data
    prompt = context.user_data.get('prompt')

    if not prompt:
        await query.edit_message_text(text="Oops! I lost the prompt. Please start over with /start.")
        return ConversationHandler.END

    await query.edit_message_text(text=f"Got it! Generating a {ratio} image for:\n\n*\"{prompt}\"* \n\nPlease wait, this might take a moment... ⏳")

    try:
        # Define dimensions based on the selected ratio
        if ratio == '16:9':
            width, height = 1344, 768
        elif ratio == '9:16':
            width, height = 768, 1344
        else:  # Default to 1:1
            width, height = 1024, 1024

        logger.info(f"Generating image with prompt: '{prompt}', size: {width}x{height}")

        # Generate the image
        image: Image.Image = client.text_to_image(
            prompt,
            model="black-forest-labs/FLUX.1-dev",
            parameters={"width": width, "height": height},
        )

        # Convert the PIL.Image object to bytes to send via Telegram
        with io.BytesIO() as bio:
            image.save(bio, 'PNG')
            bio.seek(0)
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=bio,
                caption=f"Here is your generated image! 🎨\n\nPrompt: *\"{prompt}\"*"
            )
        
        # Clean up the message
        await query.delete_message()

    except Exception as e:
        logger.error(f"Error generating image: {e}")
        await query.edit_message_text(text="😔 Sorry, something went wrong while creating the image. Please try again later.")

    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text('Operation cancelled.')
    return ConversationHandler.END

# --- Flask App for Webhook ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Hello! The bot is running."

@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
async def webhook() -> str:
    """This webhook receives updates from Telegram."""
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, application.bot)
    await application.process_update(update)
    return 'ok'

async def main():
    """Initializes and runs the bot application."""
    if not all([TELEGRAM_BOT_TOKEN, HF_TOKEN, WEBHOOK_URL]):
        logger.error("Missing one or more critical environment variables.")
        return

    # Using a global variable for the application so the webhook can access it
    global application
    
    # We need a Bot instance to set the webhook
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.set_webhook(url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}")

    application = Application.builder().bot(bot).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_prompt)],
            RATIO: [CallbackQueryHandler(generate_image)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # Note: We don't run application.run_polling() or run_webhook() here.
    # The Flask app will handle incoming requests from the webhook.

if __name__ == "__main__":
    import asyncio
    # Run the setup for the bot
    asyncio.run(main())
