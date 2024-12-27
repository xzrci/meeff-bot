import asyncio
import aiohttp
import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.filters import Command
from aiogram.types.callback_query import CallbackQuery
from db_helper import set_token, get_tokens, set_current_account, get_current_account, delete_token

# Tokens
API_TOKEN = "8088969339:AAGd7a06rPhBhWQ0Q0Yxo8iIEpBQ3_sFzwY"

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
router = Router()
dp = Dispatcher()

# Global state variables
running = False
user_chat_id = None
status_message_id = None

# Inline keyboards
start_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Start Requests", callback_data="start")],
    [InlineKeyboardButton(text="Manage Accounts", callback_data="manage_accounts")]
])

stop_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Stop Requests", callback_data="stop")]
])

back_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Back", callback_data="back_to_menu")]
])

# Fetch users from MEEFF API
async def fetch_users(session, token):
    url = "https://api.meeff.com/user/explore/v2/?lat=-3.7895238&lng=-38.5327365"
    headers = {"meeff-access-token": token, "Connection": "keep-alive"}
    async with session.get(url, headers=headers) as response:
        if response.status == 401:
            logging.error("Unauthorized access. Please check the token.")
            return []
        if response.status != 200:
            logging.error(f"Failed to fetch users: {response.status}")
            return []
        data = await response.json()
        logging.info(f"Fetched Users: {data}")
        return data.get("users", [])

# Format user details for Telegram message
def format_user_details(user):
    details = (
        f"<b>Name:</b> {user.get('name', 'N/A')}<br>"
        f"<b>Description:</b> {user.get('description', 'N/A')}<br>"
        f"<b>Birth Year:</b> {user.get('birthYear', 'N/A')}<br>"
        f"<b>Distance:</b> {user.get('distance', 'N/A')} km<br>"
        f"<b>Language Codes:</b> {', '.join(user.get('languageCodes', []))}<br>"
        "Photos:<br>"
    )
    for photo_url in user.get('photoUrls', []):
        details += f"<a href='{photo_url}'>Photo</a><br>"
    return details

# Process each user
async def process_users(session, users, token):
    for user in users:
        user_id = user.get("_id")
        if not running:
            break
        url = f"https://api.meeff.com/user/undoableAnswer/v5/?userId={user_id}&isOkay=1"
        headers = {"meeff-access-token": token, "Connection": "keep-alive"}
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            logging.info(f"Response for user {user_id}: {data}")
            if data.get("errorCode") == "LikeExceeded":
                logging.info("Daily like limit reached.")
                return True
            # Send user details to Telegram chat
            details = format_user_details(user)
            await bot.send_message(chat_id=user_chat_id, text=details, parse_mode="HTML")
            await asyncio.sleep(1)  # Short delay to ensure messages are sent one by one
    return False

# Run requests periodically
async def run_requests():
    global running, user_chat_id, status_message_id
    count = 0
    async with aiohttp.ClientSession() as session:
        while running:
            try:
                token = get_current_account(user_chat_id)
                if not token:
                    logging.error("No active account token found.")
                    await bot.edit_message_text(
                        chat_id=user_chat_id,
                        message_id=status_message_id,
                        text="No active account found. Please set an account before starting requests.",
                        reply_markup=None
                    )
                    running = False
                    return

                logging.info(f"Using token: {token}")
                users = await fetch_users(session, token)
                if not users:
                    new_text = f"Meeff:\nProcessed batch: {count}, Users fetched: 0"
                    await bot.edit_message_text(
                        chat_id=user_chat_id,
                        message_id=status_message_id,
                        text=new_text,
                        reply_markup=stop_markup
                    )
                else:
                    limit_exceeded = await process_users(session, users, token)
                    if limit_exceeded:
                        logging.info("Daily like limit reached.")
                        await bot.edit_message_text(
                            chat_id=user_chat_id,
                            message_id=status_message_id,
                            text="Meeff:\nDaily like limit reached. Stopping requests.",
                            reply_markup=None
                        )
                        running = False
                        break

                    count += 1
                    new_text = f"Meeff:\nProcessed batch: {count}, Users fetched: {len(users)}"
                    await bot.edit_message_text(
                        chat_id=user_chat_id,
                        message_id=status_message_id,
                        text=new_text,
                        reply_markup=stop_markup
                    )
                await asyncio.sleep(5)
            except Exception as e:
                logging.error(f"Error during processing: {e}")
                await bot.edit_message_text(
                    chat_id=user_chat_id,
                    message_id=status_message_id,
                    text=f"Meeff:\nAn error occurred: {e}",
                    reply_markup=None
                )
                running = False
                break

# Command handler to start the bot
@router.message(Command("start"))
async def start_command(message: types.Message):
    global user_chat_id
    user_chat_id = message.chat.id
    await message.answer("Welcome! Use the button below to start requests.", reply_markup=start_markup)

# Handle new token submission
@router.message()
async def handle_new_token(message: types.Message):
    if message.text.startswith("/"):
        return
    user_id = message.from_user.id
    token = message.text.strip()
    if len(token) < 10:
        await message.reply("Invalid token. Please try again.")
    else:
        set_token(user_id, token, "meeff_user_id_placeholder")
        await message.reply("Your access token has been saved. Use the menu to manage accounts.")

# Manage accounts and handle other callback queries
@router.callback_query()
async def callback_handler(callback_query: CallbackQuery):
    global running, user_chat_id, status_message_id

    user_id = callback_query.from_user.id
    user_chat_id = callback_query.message.chat.id  # Ensure this is updated

    if callback_query.data == "manage_accounts":
        tokens = get_tokens(user_id)
        current_token = get_current_account(user_id)
        if not tokens:
            await callback_query.message.edit_text(
                "No accounts saved. Send a new token to add an account.",
                reply_markup=back_markup
            )
            return
        buttons = [
            [InlineKeyboardButton(text=f"Account {i + 1} {'(Current)' if token['token'] == current_token else ''}", callback_data=f"set_account_{i}"),
             InlineKeyboardButton(text="Delete", callback_data=f"delete_account_{i}")]
            for i, token in enumerate(tokens)
        ]
        buttons.append([InlineKeyboardButton(text="Back", callback_data="back_to_menu")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback_query.message.edit_text("Manage your accounts:", reply_markup=markup)

    elif callback_query.data.startswith("set_account_"):
        index = int(callback_query.data.split("_")[-1])
        tokens = get_tokens(user_id)
        if index < len(tokens):
            set_current_account(user_id, tokens[index]["token"])
            await callback_query.message.edit_text("Account set as active. You can now start requests.")
        else:
            await callback_query.answer("Invalid account selected.")

    elif callback_query.data.startswith("delete_account_"):
        index = int(callback_query.data.split("_")[-1])
        tokens = get_tokens(user_id)
        if index < len(tokens):
            delete_token(user_id, tokens[index]["token"])
            await callback_query.message.edit_text("Account has been deleted.", reply_markup=back_markup)
        else:
            await callback_query.answer("Invalid account selected.")

    elif callback_query.data == "start":
        if running:
            await callback_query.answer("Requests are already running!")
        else:
            running = True
            try:
                status_message = await callback_query.message.edit_text(
                    "Meeff:\nInitializing requests...",
                    reply_markup=stop_markup
                )
                status_message_id = status_message.message_id
                asyncio.create_task(run_requests())
                await callback_query.answer("Requests started!")
            except Exception as e:
                logging.error(f"Error while starting requests: {e}")
                await callback_query.message.edit_text(
                    "Meeff:\nFailed to start requests. Please try again later.",
                    reply_markup=start_markup
                )
                running = False

    elif callback_query.data == "stop":
        if not running:
            await callback_query.answer("Requests are not running!")
        else:
            running = False
            await callback_query.message.edit_text(
                "Meeff:\nRequests stopped. Use the button below to start again.",
                reply_markup=start_markup
            )
            await callback_query.answer("Requests stopped.")

    elif callback_query.data == "back_to_menu":
        await callback_query.message.edit_text(
            "Welcome! Use the buttons below to navigate.",
            reply_markup=start_markup
        )

# Set bot commands
async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Start the bot"),
    ]
    await bot.set_my_commands(commands)

# Main function to start the bot
async def main():
    await set_bot_commands()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
