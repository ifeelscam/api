import os
import logging
import requests
import asyncio
import json
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import BadRequest
from urllib.parse import urlencode
from datetime import datetime, timedelta
from pymongo import MongoClient

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    level=logging.WARNING  # Set to WARNING to reduce verbosity
)
logger = logging.getLogger(__name__)

# Load sensitive data from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8044268114:AAH_eYmxwdPRnv49WPh6XAUB99Fg1_yP3hQ")
API_URL = os.getenv("API_URL", "https://ig-report.vercel.app/api/key?key=rehan_drsudo_report_api_admin&days=7")
# Single configuration for multiple channels for force subscription
FSUB_CHANNELS = os.getenv("FSUB_CHANNELS", "@illegalCollege").split(",")

# Dictionary to track user usage of the /key command
user_key_usage = defaultdict(int)

# List of admin user IDs
ADMINS = [7387793694,6241590270]  # Replace with actual admin Telegram user IDs

# MongoDB connection setup
MONGO_URI = "mongodb+srv://PythonBotz:Baddie@cluster0.xunylzo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["AP1xBot"]  # Database name
user_collection = db["users"]  # Collection name

# Load user data from MongoDB
def load_user_data():
    user_data = {}
    for user in user_collection.find():
        user_data[str(user["_id"])] = {
            "name": user["name"],
            "expires_at": user["expires_at"]
        }
    return user_data

# Save or update user data in MongoDB
def save_user_data(user_id, name, expires_at):
    user_collection.update_one(
        {"_id": user_id},
        {"$set": {"name": name, "expires_at": expires_at}},
        upsert=True
    )

# Remove user data from MongoDB
def remove_user_data(user_id):
    user_collection.delete_one({"_id": user_id})

# Dictionary to track user access and expiration
user_access = load_user_data()

# Command to fetch data from the API with subscription check
async def key_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    # Admins always have access
    if user_id not in ADMINS and not await has_valid_access(user_id, context.application):
        await update.message.reply_text(
            "🚫 You do not have access to use this bot.\n\n"
            "💳 Please contact my admin to buy access.\n\n 🧢 Admins : @TagRehan & @metaui"
        )
        return

    # Check subscription before allowing API access
    not_joined = []
    for channel in FSUB_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel.strip(), user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_joined.append(channel.strip())
        except BadRequest:
            not_joined.append(channel.strip())

    if not_joined:
        keyboard = [[InlineKeyboardButton(f"Join {ch}", url=f"https://t.me/{ch[1:]}")] for ch in not_joined]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 You must join all required channels to use this bot.\n\n" +
            "\n".join([f"👉 {ch}" for ch in not_joined]),
            reply_markup=reply_markup
        )
        return

    # Fetch API data if the user is subscribed
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            data = response.json()
            key = data.get("key", "No key found")  # Extract only the key from the API response

            keyboard = [[InlineKeyboardButton("Update", url='t.me/DrSudo'),
                 InlineKeyboardButton("Support", url='t.me/PythonBotz')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Cool message format
            await update.message.reply_text(
                "🎉 <b>Congratulations!</b>\n\n"
                "🔑 Here is your <b>API Key</b>:\n\n"
                f"<code>{key}</code>\n\n"
                "⏳ This key will expire after <b>1 day</b>.\n\n"
                "💡 Use it wisely!",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            logger.error(f"API request failed with status code {response.status_code}")
            await update.message.reply_text("Failed to fetch data from the API. Please try again later.")
    except requests.RequestException as e:
        logger.exception("An error occurred while making the API request.")
        await update.message.reply_text(f"An error occurred while fetching data: {e}")
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        await update.message.reply_text(f"An unexpected error occurred: {e}")

# Command to fetch subscription details
async def fsub_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Feature subscription details will be added here.")

# Function to check if a user is subscribed to the channel
def is_user_subscribed(user_id: int) -> bool:
    # Check subscription for all required channels
    for channel in FSUB_CHANNELS:
        try:
            member = updater.bot.get_chat_member(chat_id=channel.strip(), user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except BadRequest as e:
            logger.warning(f"Failed to check subscription status for user {user_id} in {channel}: {e}")
            return False
    return True

# Command to display user profile
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    if str(user_id) in user_access:
        user_data = user_access[str(user_id)]
        name = user_data.get("name", "Unknown")
        expires_at = user_data.get("expires_at", "N/A")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        remaining_time = expires_at - datetime.now()
        days, seconds = remaining_time.days, remaining_time.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        keyboard = [[InlineKeyboardButton("Admin", url='t.me/metaui'),
                 InlineKeyboardButton("Support", url='https://t.me/+kBmOgvOBXgUxYWU9')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📋 <b>Your Profile:</b>\n\n"
            f"👤 <b>Name:</b> {name}\n"
            f"🆔 <b>User ID:</b> {user_id}\n"
            f"⏳ <b>Access Expires In:</b> {days}d {hours}h {minutes}m\n\n"
            "💡 Contact an admin to extend your access.",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "<b>🚫 You do not have access to this bot.\n\n"
            "💡 Please contact an admin to gain access.</b>",
            parse_mode="HTML"
        )

# Welcome message with subscription check
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    # Check all channels for subscription
    not_joined = []
    for channel in FSUB_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel.strip(), user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_joined.append(channel.strip())
        except BadRequest:
            not_joined.append(channel.strip())

    if not_joined:
        keyboard = [[InlineKeyboardButton(f"Join {ch}", url=f"https://t.me/{ch[1:]}")] for ch in not_joined]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 You must join all required channels to use this bot.\n\n" +
            "\n".join([f"👉 {ch}" for ch in not_joined]),
            reply_markup=reply_markup
        )
        return

    # Cool welcome message
    bot_username = context.bot.username
    keyboard = [[InlineKeyboardButton("Update", url='t.me/DrSudo'),
                 InlineKeyboardButton("Support", url='t.me/PythonBotz')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to <b>DrSudo API Bot</b>!\n\n"
        "✨ Use <b>/key</b> to fetch your API data.\n\n"
        "💡 Click the button below or use /key anytime.",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# Command to display information about the bot
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Update", url='t.me/DrSudo'),
                 InlineKeyboardButton("Support", url='t.me/PythonBotz')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '''🤖 <b>About DrSudo API Bot</b>\n
        <blockquote expandable> <b><u>All Endpoints</u></b>\n\n
    generate_new: "<code>/api/rep1/ig?key={key}&user={username}</code>",

      get_saved: "<code>/api/rep/ig?key={key}&user={username}</code>",

      mass_report: "<code>/api/mass/ig?key={key}&user={username}</code>"
       </blockquote>
        💡 Created with ❤️ by <b>PythonBotz</b>.''',
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# Command to display help information
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Update", url='t.me/DrSudo'),
                 InlineKeyboardButton("Support", url='t.me/PythonBotz')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🆘 <b>Help Menu</b>\n\n"
        "Here are the commands you can use:\n"
        "• /start - Start the bot and check subscription\n"
        "• /key - Fetch your API key\n"
        "• /profile - See You details \n"
        "• /about - Learn more about this bot\n"
        "• /help - Display this help menu\n\n"
        "If you face any issues, please contact support.",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# Command to add user access (admin only)
async def add_access_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("🚫 You do not have permission to use this command.")
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text(
                "Usage: /add <user_id> <duration>\n"
                "Example: /add 123456789 1d (for 1 day)\n"
                "Example: /add 123456789 30m (for 30 minutes)"
            )
            return

        user_id = int(args[0])
        duration_str = args[1]

        # Determine if the duration is in minutes or days
        if duration_str.endswith("m"):  # Minutes
            duration = int(duration_str[:-1])
            expiration_date = datetime.now() + timedelta(minutes=duration)
            duration_text = f"{duration} minute(s)"
        elif duration_str.endswith("d"):  # Days
            duration = int(duration_str[:-1])
            expiration_date = datetime.now() + timedelta(days=duration)
            duration_text = f"{duration} day(s)"
        else:
            await update.message.reply_text(
                "❌ Invalid duration format. Use 'm' for minutes or 'd' for days.\n"
                "Example: 30m for 30 minutes, 1d for 1 day."
            )
            return

        # Save user data to MongoDB
        save_user_data(user_id, update.message.from_user.full_name, expiration_date.isoformat())
        user_access[str(user_id)] = {"name": update.message.from_user.full_name, "expires_at": expiration_date.isoformat()}

        # Notify the admin
        await update.message.reply_text(
            f"✅ Access granted to user <code>{user_id}</code> for {duration_text}.",
            parse_mode="HTML"
        )

        # Notify the user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 <b>Congratulations!</b>\n\n"
                    f"✅ You have been granted access to the bot for <b>{duration_text}</b>.\n\n"
                    "💡 Use /key to fetch your API data.\n\n"
                    "⏳ Your access will expire automatically after the given duration."
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Failed to notify user {user_id}: {e}")
    except Exception as e:
        logger.exception("An error occurred while adding access.")
        await update.message.reply_text(f"An error occurred: {e}")

# Command to remove user access (admin only)
async def remove_access_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("🚫 You do not have permission to use this command.")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("Usage: /remove <user_id>")
            return

        user_id = int(args[0])
        if str(user_id) in user_access:
            # Remove user data from MongoDB
            remove_user_data(user_id)
            del user_access[str(user_id)]

            # Notify the admin
            await update.message.reply_text(
                f"❌ Access removed for user <code>{user_id}</code>.",
                parse_mode="HTML"
            )

            # Notify the user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "🚫 <b>Your access to the bot has been removed.</b>\n\n"
                        "💡 Please contact an admin to renew your access."
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Failed to notify user {user_id}: {e}")
        else:
            await update.message.reply_text(f"User <code>{user_id}</code> does not have access.", parse_mode="HTML")
    except Exception as e:
        logger.exception("An error occurred while removing access.")
        await update.message.reply_text(f"An error occurred: {e}")

# Command to list all users with access (admin only)
async def list_access_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("🚫 You do not have permission to use this command.")
        return

    if not user_access:
        await update.message.reply_text("No users currently have access.")
        return

    message = "📋 <b>Access List:</b>\n\n"
    for user_id, expiration in user_access.items():
        remaining_time = expiration - datetime.now()
        days, seconds = remaining_time.days, remaining_time.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        message += f"• <code>{user_id}</code> - Expires in {days}d {hours}h {minutes}m\n"

    await update.message.reply_text(message, parse_mode="HTML")

# Background task to check for expired access
async def notify_expired_access(application: Application) -> None:
    while True:
        now = datetime.now()
        expired_users = [user_id for user_id, data in user_access.items() if now >= datetime.fromisoformat(data["expires_at"])]

        for user_id in expired_users:
            try:
                # Notify the user about expiration
                await application.bot.send_message(
                    chat_id=int(user_id),
                    text=(
                        "⏳ <b>Your access to the bot has expired.</b>\n\n"
                        "💡 Please contact an admin to renew your access."
                    ),
                    parse_mode="HTML"
                )
                logger.warning(f"Notified user {user_id} about access expiration.")
            except Exception as e:
                logger.warning(f"Failed to notify user {user_id} about expiration: {e}")

            # Remove expired access from MongoDB
            remove_user_data(int(user_id))
            del user_access[user_id]

        # Wait for 1 minute before checking again
        await asyncio.sleep(60)

# Check if a user has valid access
async def has_valid_access(user_id: int, application: Application) -> bool:
    if str(user_id) in user_access:
        expires_at = user_access[str(user_id)]["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if datetime.now() < expires_at:
            return True
    return False

def main():
    # Build the Application with JobQueue enabled
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("key", key_command))
    application.add_handler(CommandHandler("fsub", fsub_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_access_command))  # Added add command
    application.add_handler(CommandHandler("remove", remove_access_command))  # Added remove command
    application.add_handler(CommandHandler("list_access", list_access_command))  # Added list_access command
    application.add_handler(CommandHandler("profile", profile_command))  # Added profile command

    # Start the background task for expiration notifications
    application.job_queue.run_repeating(notify_expired_access, interval=60)

    # Start the bot
    logger.warning("Bot is running...")  # Single log message
    application.run_polling()

if __name__ == "__main__":
    main()

