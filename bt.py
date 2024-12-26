import asyncio
import aiohttp
import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.types.callback_query import CallbackQuery
from db_helper import set_token, get_tokens, set_current_account, get_current_account, delete_token
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
status_message_id = None

# Inline keyboards
start_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Start Requests", callback_data="start")],
    [InlineKeyboardButton(text="Account", callback_data="account")]
])

stop_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Stop Requests", callback_data="stop")]
])

back_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Back", callback_data="back_to_menu")]
])

# Fetch account details from MEEFF API
async def fetch_account_details(token):
    url = "https://api.meeff.com/user/info/v1"
    headers = {
        "User-Agent": "okhttp/4.12.0",
        "Accept-Encoding": "gzip",
        "meeff-access-token": token
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return None, f"Error: {response.status}"
            data = await response.json()
            return data, None

# Handle account button actions
@router.callback_query()
async def account_callback_handler(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if callback_query.data == "account":
        tokens = get_tokens(user_id)

        if not tokens:
            await callback_query.message.edit_text(
                "No accounts saved. Send a new token to add an account.",
                reply_markup=back_markup
            )
            return

        buttons = [
            [InlineKeyboardButton(text=f"Account {i + 1}", callback_data=f"view_account_{i}")]
            for i, t in enumerate(tokens)
        ]
        buttons.append([InlineKeyboardButton(text="Back", callback_data="back_to_menu")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback_query.message.edit_text(
            "Your Accounts. Click on any account to view details:",
            reply_markup=markup
        )
    elif callback_query.data.startswith("view_account_"):
        account_index = int(callback_query.data.split("_")[-1])
        tokens = get_tokens(user_id)

        if account_index >= len(tokens):
            await callback_query.answer("Invalid account selected.")
            return

        token = tokens[account_index]["token"]
        account_data, error = await fetch_account_details(token)

        if error:
            account_info = f"Unable to fetch account details. Error: {error}"
        else:
            account_info = account_data.get("user", {})
            account_info = (
                f"Name: {account_info.get('name', 'N/A')}\n"
                f"Email: {account_info.get('email', 'N/A')}\n"
                f"Gender: {'Male' if account_info.get('gender') else 'Female'}\n"
                f"Description: {account_info.get('description', 'N/A')}\n"
                f"Nationality: {account_info.get('nationalityCode', 'N/A')}\n"
                f"Ruby: {account_info.get('ruby', 0)}\n"
            )

        buttons = [
            [InlineKeyboardButton(text="Set as Current", callback_data=f"set_current_{account_index}")],
            [InlineKeyboardButton(text="Delete Account", callback_data=f"delete_account_{account_index}")],
            [InlineKeyboardButton(text="Back to Accounts", callback_data="account")]
        ]
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback_query.message.edit_text(account_info, reply_markup=markup)
    elif callback_query.data.startswith("set_current_"):
        account_index = int(callback_query.data.split("_")[-1])
        tokens = get_tokens(user_id)

        if account_index >= len(tokens):
            await callback_query.answer("Invalid account selected.")
            return

        token = tokens[account_index]["token"]
        set_current_account(user_id, token)

        await callback_query.message.edit_text(
            "This account has been set as the current account.",
            reply_markup=back_markup
        )
    elif callback_query.data.startswith("delete_account_"):
        account_index = int(callback_query.data.split("_")[-1])
        tokens = get_tokens(user_id)

        if account_index >= len(tokens):
            await callback_query.answer("Invalid account selected.")
            return

        token = tokens[account_index]["token"]
        delete_token(user_id, token)

        await callback_query.message.edit_text(
            "The account has been deleted.",
            reply_markup=back_markup
        )
    elif callback_query.data == "back_to_menu":
        await callback_query.message.edit_text(
            "Welcome! Use the buttons below to navigate.",
            reply_markup=start_markup
        )

@router.message(Command("start"))
async def start_command(message: types.Message):
    global user_chat_id
    user_chat_id = message.chat.id
    await message.answer("Welcome! Use the buttons below to navigate.", reply_markup=start_markup)

# Handle new token submission
@router.message()
async def handle_new_token(message: types.Message):
    # Ignore commands
    if message.text.startswith("/"):
        return

    user_id = message.from_user.id
    token = message.text.strip()

    if len(token) < 10:
        await message.reply("Invalid token. Please try again.")
        return

    # Fetch userId from MEEFF API
    account_data, error = await fetch_account_details(token, "")
    if error:
        await message.reply(f"Failed to validate token. Error: {error}")
        return

    meeff_user_id = account_data.get("user", {}).get("_id")
    if not meeff_user_id:
        await message.reply("Failed to retrieve account information. Please check your token.")
        return

    # Save token and userId to the database
    set_token(user_id, token, meeff_user_id)
    await message.reply("Your access token has been saved.")
    
# Start polling
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
