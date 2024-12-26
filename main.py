import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.types.callback_query import CallbackQuery

API_TOKEN = "7653663622:AAESlxbzSCDdxlOt1zf0_yYOHyxD_xJLfvY"
MEEFF_ACCESS_TOKEN = "92K26S09E6QFT7WGH2P0UJ62O5E61WTIMAOO507BA2B3XN3X2SF1KYFFK1V8DVACGK9501ST1X0A130AEN4O32ACQ0QFS30MDTXTNN34DRG0WJI5KX0FTDJN690VWIEUUKXJJDUJYWZPF86UCYUAHJSU0RG8PITK6NNMLQB248Z99CYB0IQ7X6BFSI72MLN4NCF90UOXO66MDV9VJZOEAG2AG82PD4I7N9T1XDI4W7C5JTIZSE7VNRXYT7NXVY"

bot = Bot(token=API_TOKEN)
router = Router()
dp = Dispatcher()

running = False
user_id = None  # Store the user ID to send logs
status_message_id = None  # Message ID to edit processing state

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
    global running, status_message_id
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
            # Log message for processing
            log_message = f"Processing User ID: {user_id}\nResponse: {json_res}"

            # Update processing state message
            if status_message_id:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=status_message_id,
                    text=log_message
                )

            # Handle daily limit exceeded case
            if json_res.get("errorCode") == "LikeExceeded":
                limit_message = (
                    "Daily limit of likes reached. "
                    "Please try again tomorrow.\n"
                    f"Details: {json_res.get('errorMessage')}"
                )
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=status_message_id,
                    text=limit_message
                )
                running = False
                break

async def run_requests():
    global running, status_message_id
    count = 0
    async with aiohttp.ClientSession() as session:
        while running:
            users = await fetch_users(session)
            await process_users(session, users)
            count += 1
            # Update the status message with batch processing information
            if status_message_id:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=status_message_id,
                    text=f"Processed batch: {count}\nFetching more users..."
                )
            await asyncio.sleep(5)

@router.message(Command("start"))
async def start_command(message: types.Message):
    global user_id, status_message_id
    user_id = message.chat.id  # Save the user ID
    await message.answer("Welcome! Use the buttons below to start or stop requests.", reply_markup=start_stop_markup)

@router.callback_query()
async def callback_handler(callback_query: CallbackQuery):
    global running, status_message_id

    if callback_query.data == "start":
        if running:
            await callback_query.answer("Requests are already running!")
        else:
            running = True
            # Send a new status message and save its ID
            status_message = await bot.send_message(
                chat_id=callback_query.message.chat.id,
                text="Starting processing requests..."
            )
            status_message_id = status_message.message_id
            await callback_query.answer("Started processing requests!")
            asyncio.create_task(run_requests())

    elif callback_query.data == "stop":
        if not running:
            await callback_query.answer("Requests are not running!")
        else:
            running = False
            # Update the status message to indicate stopping
            if status_message_id:
                await bot.edit_message_text(
                    chat_id=callback_query.message.chat.id,
                    message_id=status_message_id,
                    text="Processing stopped."
                )
            await callback_query.answer("Stopped processing requests!")

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
