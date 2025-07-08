import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# /start কমান্ডের হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """যখন ইউজার /start কমান্ড পাঠায় তখন এই ফাংশনটি চলে।"""
    user = update.effective_user
    await update.message.reply_html(
        f"হাই {user.mention_html()}! আমি একটি সহজ বট। আমাকে কিছু বলুন!",
    )

# সাধারণ মেসেজের হ্যান্ডলার (কমান্ড ছাড়া)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ইউজারের মেসেজকে প্রতিধ্বনিত করে (echo)।"""
    await update.message.reply_text(update.message.text)

def main() -> None:
    """বট শুরু করে।"""
    # আপনার বট টোকেন এনভায়রনমেন্ট ভেরিয়েবল থেকে নিন
    # এটি API সুরক্ষিত রাখার একটি গুরুত্বপূর্ণ অংশ
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set.")
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")

    # ApplicationBuilder ব্যবহার করে বট অ্যাপ্লিকেশন তৈরি করুন
    application = Application.builder().token(TOKEN).build()

    # কমান্ড হ্যান্ডলার যোগ করুন
    application.add_handler(CommandHandler("start", start))

    # মেসেজ হ্যান্ডলার যোগ করুন (সব টেক্সট মেসেজের জন্য যা কমান্ড নয়)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # বট শুরু করুন (Polling mode)
    # Render-এ সাধারণত Webhook ব্যবহার করা হয়, তবে সহজ উদাহরণের জন্য Polling দেখাচ্ছি
    # Render-এ Webhook সেটআপের জন্য একটু বেশি কোড প্রয়োজন
    # যদি আপনি Render Free Tier ব্যবহার করেন, তবে Polling কিছুক্ষণ চলার পর বন্ধ হয়ে যেতে পারে।
    # Persistent bot-এর জন্য Render-এর Background Worker (paid) ব্যবহার করা ভালো।
    # অথবা Webhook সেটআপ করতে পারেন যা Render Web Service-এ কাজ করবে।
    logger.info("Bot starting with polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
  
