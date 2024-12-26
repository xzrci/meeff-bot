import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.types.callback_query import CallbackQuery

API_TOKEN = "YOUR_TELEGRAM_BOT_API_TOKEN"
MEEFF_ACCESS_TOKEN = "YOUR_MEEFF_ACCESS_TOKEN"

bot = Bot(token=API_TOKEN)
router = Router()
dp = Dispatcher()

running = False
user_id = None  # Store the user ID to send logs to them

# Inline keyboard setup
start_button = InlineKeyboardButton(text="Start Requests", callback_data="start")
stop_button = InlineKeyboardButton(text="Stop Requests", callback_data="stop")
start_stop_markup = InlineKeyboardMarkup(inline_keyboard=[
    [start_button, stop_button]
])

async def fetch_users(session):
    async with session.get(
        "https://api.meeff.com/user/explore/v2/?lat=-3.7895238&lng=-38.5327365",
        headers={
            "meeff-access-token": MEEFF_ACCESS_TOKEN,
            "Connection": "keep-alive",
        }
    ) as response:
        if response.status == 200:
            json_response = await response.json()
            return json_response.get("users", [])
    return []

async def process_users(session, users):
    global running
    for user in users:
        if not running:
            break
        user_id = user.get("_id")
        async with session.get(
            f"https://api.meeff.com/user/undoableAnswer/v5/?userId={user_id}&isOkay=1",
            headers={
                "meeff-access-token": MEEFF_ACCESS_TOKEN,
                "Connection": "keep-alive",
            }
        ) as response:
            json_res = await response.json()
            log_message = f"{user_id}\n{json_res}"
            # Send log message to the user
            await bot.send_message(chat_id=user_id, text=log_message)

            # Handle daily limit exceeded case
            if json_res.get("errorCode") == "LikeExceeded":
                limit_message = (
                    "You've reached the daily limit of likes. "
                    "Please try again tomorrow.\n"
                    f"Details: {json_res.get('errorMessage')}"
                )
                await bot.send_message(chat_id=user_id, text=limit_message)
                running = False  # Stop processing if the limit is reached
                break

async def run_requests():
    global running
    count = 0
    async with aiohttp.ClientSession() as session:
        while running:
            users = await fetch_users(session)
            await process_users(session, users)
            count += 1
            await asyncio.sleep(5)
            await bot.send_message(chat_id=user_id, text=f"Processed batch: {count}")

@router.message(Command("start"))
async def start_command(message: types.Message):
    global user_id
    user_id = message.chat.id  # Save the user ID
    await message.answer("Welcome! Use the buttons below to start or stop requests.", reply_markup=start_stop_markup)

@router.callback_query()
async def callback_handler(callback_query: CallbackQuery):
    global running

    if callback_query.data == "start":
        if running:
            await callback_query.answer("Requests are already running!")
        else:
            running = True
            await callback_query.answer("Started processing requests!")
            asyncio.create_task(run_requests())
    elif callback_query.data == "stop":
        if not running:
            await callback_query.answer("Requests are not running!")
        else:
            running = False
            await callback_query.answer("Stopped processing requests!")

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
