import asyncio
import aiohttp
import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.types.callback_query import CallbackQuery
from db_helper import set_token, get_tokens, set_current_account, get_current_account, delete_token

# Tokens
API_TOKEN = "8088969339:AAGd7a06rPhBhWQ0Q0Yxo8iIEpBQ3_sFzwY"
DEFAULT_MEEFF_TOKEN = "0KOFZAF6QQVROOUK5ZPYIE5JGHV6UAEDXLS2MK1WL2CKEKMYOR8B4FXUQ1V3FUQPT4GL4AASYE4EO4R3YMQ7TW3GQ7URLA2VKR3KICB6NBMHNOXGJIXYW6UTR2C8H6M0MGB5PG1SXOOBA7ICI239IDVNIZ7Y0EYGNVB97I5HXZAU10FSAJ2ME4LOK7KBXGCW0ENHITK5843CZP5D4DHBMLIRA63BLMBYOLI3PVZVB6B6Q8ZZO18W2BYHNUPVPOAW"

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
    [InlineKeyboardButton(text="Account", callback_data="account")]
])

stop_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Stop Requests", callback_data="stop")]
])

# Fetch users from MEEFF API
async def fetch_users(session, token):
    url = "https://api.meeff.com/user/explore/v2/?lat=-3.7895238&lng=-38.5327365"
    headers = {
        "meeff-access-token": token,
        "Connection": "keep-alive",
    }

    async with session.get(url, headers=headers) as response:
        if response.status != 200:
            logging.error(f"Failed to fetch users: {response.status}")
            return []
        data = await response.json()
        logging.info(f"Fetched Users: {data}")
        return data.get("users", [])

# Process each user
async def process_users(session, users, token):
    for user in users:
        user_id = user.get("_id")
        if not running:
            break
        url = f"https://api.meeff.com/user/undoableAnswer/v5/?userId={user_id}&isOkay=1"
        headers = {
            "meeff-access-token": token,
            "Connection": "keep-alive",
        }
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            logging.info(f"Response for user {user_id}: {data}")
            if data.get("errorCode") == "LikeExceeded":
                logging.info("Daily like limit reached.")
                return True
    return False

# Run requests periodically
async def run_requests():
    global running, user_chat_id, status_message_id
    count = 0
    async with aiohttp.ClientSession() as session:
        while running:
            try:
                # Use the default token for testing
                token = get_current_account(user_chat_id) or DEFAULT_MEEFF_TOKEN
                logging.info(f"Using token: {token}")

                users = await fetch_users(session, token)
                if not users:
                    await bot.edit_message_text(
                        chat_id=user_chat_id,
                        message_id=status_message_id,
                        text=f"Meeff:\nProcessed batch: {count}, Users fetched: 0",
                        reply_markup=stop_markup
                    )
                else:
                    limit_exceeded = await process_users(session, users, token)
                    if limit_exceeded:
                        await bot.edit_message_text(
                            chat_id=user_chat_id,
                            message_id=status_message_id,
                            text="Meeff:\nDaily like limit reached. Stopping requests.",
                            reply_markup=None
                        )
                        running = False
                        break

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
                    text=f"Meeff:\nAn error occurred: {e}",
                    reply_markup=None
                )
                break

# Command handler to start the bot
@router.message(Command("start"))
async def start_command(message: types.Message):
    global user_chat_id
    user_chat_id = message.chat.id
    await message.answer("Welcome! Use the button below to start requests.", reply_markup=start_markup)

# Callback query handler for start/stop buttons
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
            asyncio.create_task(run_requests())
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

# Main function to start the bot
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
