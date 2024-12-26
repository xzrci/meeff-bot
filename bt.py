import asyncio
import aiohttp
import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.types.callback_query import CallbackQuery

# Tokens
API_TOKEN = "7780275950:AAFZoZamRNCATEapl6rg2hmrUCbSCpXufyk"
MEEFF_ACCESS_TOKEN = "CJ99XRSADKYRKXOMYTG44TNL16U7KZ0AW5RSGJU4OX60R3I9CD7ER3TVARJAXYWMKTBVZ5U24V5VR0Z85NX6INU7301WTVIF3LCH7GP54J7T0XD41UEKSRONBPNKL6N8W0T42C4H9H8EJ2X2H58W6SWUQBL5KKET6P1R6DGLNQZUO1MO52IB6D08Y4YPK6BU0IBKNSBMCU2QYTU5YSDEWVP5FQNLPCA0JSD5J9SHIGUD30PXPVW9BH0GOJ5VRYKV"

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
        json_response = await response.json()
        logging.info(f"Fetch Users Response: {json_response}")
        if response.status == 200:
            return json_response.get("users", [])
        return []

# Process each user
async def process_users(session, users):
    global running, user_chat_id
    for user in users:
        if not running:
            break

        # Extract user details
        user_id = user.get("_id")
        name = user.get("name", "Unknown")
        age = user.get("age", "N/A")
        location = user.get("location", {}).get("city", "Unknown")
        bio = user.get("bio", "No bio available")
        interests = user.get("interests", [])
        interests_str = ", ".join(interests) if interests else "None"

        # Log user details
        logging.info(f"Processing User: ID={user_id}, Name={name}, Age={age}, Location={location}, Bio={bio}, Interests={interests_str}")

        # Send request to "Like" the user
        async with session.get(
            f"https://api.meeff.com/user/undoableAnswer/v5/?userId={user_id}&isOkay=1",
            headers={
                "meeff-access-token": MEEFF_ACCESS_TOKEN,
                "Connection": "keep-alive",
            }
        ) as response:
            json_res = await response.json()
            logging.info(f"Process User Response for {user_id}: {json_res}")

            # Check for "LikeExceeded" error
            if "errorCode" in json_res and json_res["errorCode"] == "LikeExceeded":
                if user_chat_id:
                    await bot.edit_message_text(
                        chat_id=user_chat_id,
                        message_id=status_message_id,
                        text=f"Meeff:\nYou've reached the daily limit of likes. Processing will stop. Please try again tomorrow.\nLast processed user: {name}, Age: {age}, Location: {location}",
                        reply_markup=None
                    )
                running = False
                return True  # Stop processing

        # Update the Telegram message with user details
        if user_chat_id:
            await bot.edit_message_text(
                chat_id=user_chat_id,
                message_id=status_message_id,
                text=f"Meeff:\nProcessing User: {name}, Age: {age}, Location: {location}\nBio: {bio}\nInterests: {interests_str}",
                reply_markup=stop_markup
            )

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
