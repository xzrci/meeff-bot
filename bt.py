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
        return []

    meeff_access_token = tokens[0]["token"]  # Use the first token for now
    async with session.get(
        "https://api.meeff.com/user/explore/v2/?lat=-3.7895238&lng=-38.5327365",
        headers={
            "meeff-access-token": meeff_access_token,
            "Connection": "keep-alive",
        }
    ) as response:
        json_response = await response.json()
        logging.info(f"Fetch Users Response: {json_response}")
        if response.status == 200:
            return json_response.get("users", [])
        return []

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
    elif callback_query.data == "account":
        user_id = callback_query.from_user.id
        tokens = get_tokens(user_id)

        if tokens:
            accounts = "\n".join(f"- {t['token'][:10]}..." for t in tokens)
            await callback_query.message.edit_text(
                f"Your Accounts:\n{accounts}\n\nSend a new access token to add it.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Back", callback_data="back_to_menu")]
                ])
            )
        else:
            await callback_query.message.edit_text(
                "You have no saved accounts. Send a new access token to add it.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Back", callback_data="back_to_menu")]
                ])
            )
        await callback_query.answer()
    elif callback_query.data == "back_to_menu":
        await callback_query.message.edit_text(
            "Welcome! Use the buttons below to navigate.",
            reply_markup=start_markup
        )
        await callback_query.answer()

# Handle new tokens sent by the user
@router.message()
async def handle_new_token(message: types.Message):
    user_id = message.from_user.id
    token = message.text.strip()

    # Validate token format (optional)
    if len(token) < 10:  # Adjust the validation as per actual token format
        await message.reply("Invalid token. Please try again.")
        return

    # Save the token
    set_token(user_id, token)
    await message.reply("Your access token has been saved.")

# Main function to start the bot
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
