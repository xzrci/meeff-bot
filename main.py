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
user_chat_id = None
status_message_id = None  # To track the message being updated

# Inline keyboards
start_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Start Requests", callback_data="start")]
])

stop_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Stop Requests", callback_data="stop")]
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

            # Check for "LikeExceeded" error
            if "errorCode" in json_res and json_res["errorCode"] == "LikeExceeded":
                if user_chat_id:
                    await bot.edit_message_text(
                        chat_id=user_chat_id,
                        message_id=status_message_id,
                        text="Meeff:\nYou've reached the daily limit of likes. Processing will stop. Please try again tomorrow.",
                        reply_markup=None
                    )
                running = False
                return True  # Stop processing
    return False  # Continue processing

# Run requests periodically
async def run_requests():
    global running, user_chat_id, status_message_id
    count = 0
    async with aiohttp.ClientSession() as session:
        while running:
            try:
                users = await fetch_users(session)
                if not users:
                    await bot.edit_message_text(
                        chat_id=user_chat_id,
                        message_id=status_message_id,
                        text=f"Meeff:\nProcessed batch: {count}, Users fetched: 0",
                        reply_markup=stop_markup
                    )
                else:
                    limit_exceeded = await process_users(session, users)
                    if limit_exceeded:
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
