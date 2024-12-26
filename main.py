import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.types.callback_query import CallbackQuery

# Tokens
API_TOKEN = "7653663622:AAESlxbzSCDdxlOt1zf0_yYOHyxD_xJLfvY"
MEEFF_ACCESS_TOKEN = "92K26S09E6QFT7WGH2H3P0UJ62O5E61WTIMAOO507BA2B3XN3X2SF1KYFFK1V8DVACGK9501ST1X0A130AEN4O32ACQ0QFS30MDTXTNN34DRG0WJI5KX0FTDJN690VWIEUUKXJJDUJYWZPF86UCYUAHJSU0RG8PITK6NNMLQB248Z99CYB0IQ7X6BFSI72MLN4NCF90UOXO66MDV9VJZOEAG2AG82PD4I7N9T1XDI4W7C5JTIZSE7VNRXYT7NXVY"

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
router = Router()
dp = Dispatcher()

# Global state variables
running = False
user_chat_id = None  # To store the user's chat ID for sending updates

# Inline keyboard setup
start_button = InlineKeyboardButton(text="Start Requests", callback_data="start")
stop_button = InlineKeyboardButton(text="Stop Requests", callback_data="stop")
start_stop_markup = InlineKeyboardMarkup(inline_keyboard=[
    [start_button, stop_button]
])

# Fetch users from MEEFF API
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

# Process each user
async def process_users(session, users):
    global running, user_chat_id
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

            # Check if the "LikeExceeded" error occurs
            if "errorCode" in json_res and json_res["errorCode"] == "LikeExceeded":
                if user_chat_id:
                    await bot.send_message(
                        user_chat_id,
                        "You've reached the daily limit of likes. Processing will stop. Please try again tomorrow."
                    )
                print(json_res)  # Log the error message
                running = False  # Stop the process
                break
            else:
                print(json_res)  # Log normal responses

# Run requests periodically
async def run_requests():
    global running, user_chat_id
    count = 0
    async with aiohttp.ClientSession() as session:
        while running:
            try:
                users = await fetch_users(session)
                if not users:
                    if user_chat_id:
                        await bot.send_message(user_chat_id, "No users found in the current batch.")
                else:
                    await process_users(session, users)

                count += 1
                if user_chat_id:
                    await bot.send_message(
                        user_chat_id,
                        f"Processed batch: {count}, Users fetched: {len(users)}"
                    )
                await asyncio.sleep(5)
            except Exception as e:
                if user_chat_id:
                    await bot.send_message(user_chat_id, f"An error occurred: {str(e)}")
                break

# Command handler to start the bot
@router.message(Command("start"))
async def start_command(message: types.Message):
    global user_chat_id
    user_chat_id = message.chat.id  # Save the user's chat ID
    await message.answer("Welcome! Use the buttons below to start or stop requests.", reply_markup=start_stop_markup)

# Callback query handler for start/stop buttons
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

# Main function to start the bot
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
