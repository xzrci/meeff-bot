import asyncio
import aiohttp
import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.types.callback_query import CallbackQuery
from db_helper import set_token, get_tokens

# Tokens
API_TOKEN = "7780275950:AAFZoZamRNCATEapl6rg2hmrUCbSCpXufyk"

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
router = Router()
dp = Dispatcher()

# Global state variables
running = False
user_chat_id = None
status_message_id = None  # To track the message being updated

# Inline keyboards
start_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Start Requests", callback_data="start")],
    [InlineKeyboardButton(text="Account", callback_data="account")]
])

stop_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Stop Requests", callback_data="stop")]
])

# Fetch users from MEEFF API
async def fetch_users(session, user_id):
    tokens = get_tokens(user_id)
    if not tokens:
        return None, "No MEEFF access token found. Please add one using the Account menu."

    meeff_access_token = tokens[0]["token"]  # Use the first token for now
    async with session.get(
        "https://api.meeff.com/user/explore/v2/?lat=-3.7895238&lng=-38.5327365",
        headers={
            "meeff-access-token": meeff_access_token,
            "Connection": "keep-alive",
        }
    ) as response:
        json_response = await response.json()
        if response.status == 200:
            return json_response.get("users", []), None
        return None, f"Error fetching users: {json_response.get('message', 'Unknown error')}"

# Process users
async def process_users(session, user_id, users):
    global running

    tokens = get_tokens(user_id)
    if not tokens:
        return "No MEEFF access token found. Please add one using the Account menu."

    meeff_access_token = tokens[0]["token"]

    for user in users:
        if not running:
            break
        user_id = user.get("_id")
        async with session.get(
            f"https://api.meeff.com/user/undoableAnswer/v5/?userId={user_id}&isOkay=1",
            headers={
                "meeff-access-token": meeff_access_token,
                "Connection": "keep-alive",
            }
        ) as response:
            json_res = await response.json()
            if "errorCode" in json_res and json_res["errorCode"] == "LikeExceeded":
                return "You've reached the daily limit of likes. Processing will stop."

    return None

# Run requests periodically
async def run_requests(user_id):
    global running, status_message_id
    count = 0

    async with aiohttp.ClientSession() as session:
        while running:
            try:
                users, error = await fetch_users(session, user_id)
                if error:
                    await bot.edit_message_text(
                        chat_id=user_chat_id,
                        message_id=status_message_id,
                        text=f"Meeff:\n{error}",
                        reply_markup=None
                    )
                    running = False
                    return

                if not users:
                    await bot.edit_message_text(
                        chat_id=user_chat_id,
                        message_id=status_message_id,
                        text=f"Meeff:\nProcessed batch: {count}, Users fetched: 0",
                        reply_markup=stop_markup
                    )
                else:
                    error = await process_users(session, user_id, users)
                    if error:
                        await bot.edit_message_text(
                            chat_id=user_chat_id,
                            message_id=status_message_id,
                            text=f"Meeff:\n{error}",
                            reply_markup=None
                        )
                        running = False
                        return

                    count += 1
                    await bot.edit_message_text(
                        chat_id=user_chat_id,
                        message_id=status_message_id,
                        text=f"Meeff:\nProcessed batch: {count}, Users fetched: {len(users)}",
                        reply_markup=stop_markup
                    )
                await asyncio.sleep(5)
            except Exception as e:
                logging.error(f"Error during processing: {e}")
                await bot.edit_message_text(
                    chat_id=user_chat_id,
                    message_id=status_message_id,
                    text=f"Meeff:\nAn error occurred: {str(e)}",
                    reply_markup=None
                )
                break

# Command handler to start the bot
@router.message(Command("start"))
async def start_command(message: types.Message):
    global user_chat_id
    user_chat_id = message.chat.id
    await message.answer("Welcome! Use the buttons below to navigate.", reply_markup=start_markup)

# Callback query handler for inline buttons
@router.callback_query()
async def callback_handler(callback_query: CallbackQuery):
    global running, status_message_id

    if callback_query.data == "start":
        if running:
            await callback_query.answer("Requests are already running!")
        else:
            running = True
            status_message = await callback_query.message.edit_text(
                "Meeff:\nInitializing requests...",
                reply_markup=stop_markup
            )
            status_message_id = status_message.message_id
            asyncio.create_task(run_requests(callback_query.from_user.id))
            await callback_query.answer("Requests started!")
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

# Polling for the bot
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
