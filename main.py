import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.types.callback_query import CallbackQuery
from dotenv import load_dotenv  # Use for environment variables

# Load environment variables
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
MEEFF_ACCESS_TOKEN = os.getenv("MEEFF_ACCESS_TOKEN")

bot = Bot(token=API_TOKEN)
router = Router()
dp = Dispatcher()

running = False
admin_chat_id = None  # Set your Telegram chat ID here to receive logs (optional)

# Inline keyboard setup
start_button = InlineKeyboardButton(text="Start Requests", callback_data="start")
stop_button = InlineKeyboardButton(text="Stop Requests", callback_data="stop")
start_stop_markup = InlineKeyboardMarkup(inline_keyboard=[
    [start_button, stop_button]
])

async def fetch_users(session):
    try:
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
    except Exception as e:
        print(f"Error fetching users: {e}")
    return []

async def process_users(session, users):
    global running
    for user in users:
        if not running:
            break
        user_id = user.get("_id")
        try:
            async with session.get(
                f"https://api.meeff.com/user/undoableAnswer/v5/?userId={user_id}&isOkay=1",
                headers={
                    "meeff-access-token": MEEFF_ACCESS_TOKEN,
                    "Connection": "keep-alive",
                }
            ) as response:
                if response.status == 200:
                    json_res = await response.json()
                    if json_res.get("errorCode") == "LikeExceeded":
                        error_message = json_res.get("errorMessage", "Limit exceeded.")
                        prices = json_res.get("prices", {})
                        log_message = (
                            f"{json_res}\n"
                            f"Error: {error_message}\n"
                            f"Prices: {prices}\n"
                            "Stopping bot..."
                        )
                        print(log_message)  # Log on the server
                        if admin_chat_id:
                            await bot.send_message(
                                chat_id=admin_chat_id,
                                text=log_message
                            )  # Notify admin on Telegram
                        running = False
                        return
                    print(json_res)  # Log successful response
        except Exception as e:
            print(f"Error processing user {user_id}: {e}")

async def run_requests():
    global running
    count = 0
    async with aiohttp.ClientSession() as session:
        while running:
            try:
                users = await fetch_users(session)
                await process_users(session, users)
                count += 1
                await asyncio.sleep(5)
                print(f"Processed batch: {count}")
            except Exception as e:
                print(f"Error in run_requests: {e}")

@router.message(Command("start"))
async def start_command(message: types.Message):
    global admin_chat_id
    admin_chat_id = message.chat.id  # Save the admin's chat ID
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
