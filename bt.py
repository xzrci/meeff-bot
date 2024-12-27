import asyncio
import aiohttp
import logging
import html
import json
from collections import defaultdict
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.filters import Command
from aiogram.types.callback_query import CallbackQuery
from db_helper import set_token, get_tokens, set_current_account, get_current_account, delete_token

# Tokens
API_TOKEN = "8088969339:AAGd7a06rPhBhWQ0Q0Yxo8iIEpBQ3_sFzwY"

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
router = Router()
dp = Dispatcher()

# Global state variables
user_states = defaultdict(lambda: {
    "running": False,
    "status_message_id": None,
    "pinned_message_id": None,
    "total_added_friends": 0
})

# Inline keyboards
start_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Start Requests", callback_data="start")],
    [InlineKeyboardButton(text="Manage Accounts", callback_data="manage_accounts")],
    [InlineKeyboardButton(text="Show Account Info", callback_data="show_account_info")],
    [InlineKeyboardButton(text="Invoke", callback_data="invoke")]
])

stop_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Stop Requests", callback_data="stop")]
])

back_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Back", callback_data="back_to_menu")]
])

async def fetch_users(session, token):
    url = "https://api.meeff.com/user/explore/v2/?lat=-3.7895238&lng=-38.5327365"
    headers = {"meeff-access-token": token, "Connection": "keep-alive"}
    async with session.get(url, headers=headers) as response:
        if response.status != 200:
            logging.error(f"Failed to fetch users: {response.status}")
            return []
        return (await response.json()).get("users", [])

def format_user_details(user):
    details = (
        f"<b>Name:</b> {html.escape(user.get('name', 'N/A'))}\n"
        f"<b>Description:</b> {html.escape(user.get('description', 'N/A'))}\n"
        f"<b>Birth Year:</b> {html.escape(str(user.get('birthYear', 'N/A')))}\n"
        f"<b>Distance:</b> {html.escape(str(user.get('distance', 'N/A')))} km\n"
        f"<b>Language Codes:</b> {html.escape(', '.join(user.get('languageCodes', [])))}\n"
        "Photos: " + ' '.join([f"<a href='{html.escape(url)}'>Photo</a>" for url in user.get('photoUrls', [])])
    )
    return details

async def process_users(session, users, token, user_id):
    state = user_states[user_id]
    batch_added_friends = 0
    for user in users:
        if not state["running"]:
            break
        url = f"https://api.meeff.com/user/undoableAnswer/v5/?userId={user['_id']}&isOkay=1"
        headers = {"meeff-access-token": token, "Connection": "keep-alive"}
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            if data.get("errorCode") == "LikeExceeded":
                logging.info("Daily like limit reached.")
                return True
            await bot.send_message(chat_id=user_id, text=format_user_details(user), parse_mode="HTML")
            batch_added_friends += 1
            state["total_added_friends"] += 1
            await bot.edit_message_text(chat_id=user_id, message_id=state["status_message_id"],
                                        text=f"Batch: {state['batch_index']} Users Fetched: {len(users)}\n"
                                             f"Batch: {state['batch_index']} Added Friends: {batch_added_friends}\n"
                                             f"Total Added: {state['total_added_friends']}",
                                        reply_markup=stop_markup)
            await asyncio.sleep(1)
    return False

async def run_requests(user_id):
    state = user_states[user_id]
    state["total_added_friends"] = 0
    state["batch_index"] = 0
    async with aiohttp.ClientSession() as session:
        while state["running"]:
            try:
                token = get_current_account(user_id)
                if not token:
                    await bot.edit_message_text(chat_id=user_id, message_id=state["status_message_id"],
                                                text="No active account found. Please set an account before starting requests.",
                                                reply_markup=None)
                    state["running"] = False
                    if state["pinned_message_id"]:
                        await bot.unpin_chat_message(chat_id=user_id, message_id=state["pinned_message_id"])
                        state["pinned_message_id"] = None
                    return

                users = await fetch_users(session, token)
                state["batch_index"] += 1
                if not users:
                    await bot.edit_message_text(chat_id=user_id, message_id=state["status_message_id"],
                                                text=f"Batch: {state['batch_index']} Users Fetched: 0\n"
                                                     f"Total Added: {state['total_added_friends']}",
                                                reply_markup=stop_markup)
                else:
                    if await process_users(session, users, token, user_id):
                        await bot.edit_message_text(chat_id=user_id, message_id=state["status_message_id"],
                                                    text="You've reached daily limit, try again tomorrow.",
                                                    reply_markup=None)
                        state["running"] = False
                        if state["pinned_message_id"]:
                            await bot.unpin_chat_message(chat_id=user_id, message_id=state["pinned_message_id"])
                            state["pinned_message_id"] = None
                        break
                await asyncio.sleep(5)
            except Exception as e:
                logging.error(f"Error during processing: {e}")
                await bot.edit_message_text(chat_id=user_id, message_id=state["status_message_id"],
                                            text=f"An error occurred: {e}", reply_markup=None)
                state["running"] = False
                if state["pinned_message_id"]:
                    await bot.unpin_chat_message(chat_id=user_id, message_id=state["pinned_message_id"])
                    state["pinned_message_id"] = None
                break

async def fetch_account_info(token):
    url = "https://api.meeff.com/user/login/v4"
    payload = {
        "os": "iOS v16.4.1", "platform": "ios", "device": "BRAND: Apple, MODEL: iPhone 14 Pro",
        "deviceUniqueId": "6a92f1b4e7d54abc", "deviceLanguage": "en", "deviceRegion": "US",
        "simRegion": "US", "deviceGmtOffset": "-0800", "deviceRooted": 0, "deviceEmulator": 0,
        "appVersion": "6.3.9", "locale": "en"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0", 'Accept-Encoding': "gzip", 'meeff-access-token': token,
        'content-type': "application/json; charset=utf-8"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=json.dumps(payload), headers=headers) as response:
            if response.status != 200:
                logging.error(f"Failed to fetch account info: {response.status}")
                return None
            return (await response.json()).get('user')

@router.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.chat.id
    state = user_states[user_id]
    state["status_message_id"] = (await message.answer("Welcome! Use the button below to start requests.", reply_markup=start_markup)).message_id
    state["pinned_message_id"] = None

@router.message()
async def handle_new_token(message: types.Message):
    if message.text and message.text.startswith("/"):
        return
    user_id = message.from_user.id
    
    # Ignore bot's own messages
    if message.from_user.is_bot:
        return
    
    if message.text:
        token = message.text.strip()
        if len(token) < 10:
            await message.reply("Invalid token. Please try again.")
            return

        account_info = await fetch_account_info(token)
        if account_info is None:
            await message.reply("Failed to sign in. Token is expired or invalid.")
            return

        set_token(user_id, token, account_info['name'])
        await message.reply("Your access token has been verified and saved. Use the menu to manage accounts.")
    else:
        await message.reply("Message text is empty. Please provide a valid token.")

@router.callback_query()
async def callback_handler(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    state = user_states[user_id]

    if callback_query.data == "manage_accounts":
        tokens = get_tokens(user_id)
        current_token = get_current_account(user_id)
        if not tokens:
            await callback_query.message.edit_text("No accounts saved. Send a new token to add an account.", reply_markup=back_markup)
            return
        buttons = [
            [InlineKeyboardButton(text=f"{token['name']} {'(Current)' if token['token'] == current_token else ''}", callback_data=f"set_account_{i}"),
             InlineKeyboardButton(text="Delete", callback_data=f"delete_account_{i}")]
            for i, token in enumerate(tokens)
        ]
        buttons.append([InlineKeyboardButton(text="Back", callback_data="back_to_menu")])
        await callback_query.message.edit_text("Manage your accounts:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

    elif callback_query.data.startswith("set_account_"):
        index = int(callback_query.data.split("_")[-1])
        tokens = get_tokens(user_id)
        if index < len(tokens):
            set_current_account(user_id, tokens[index]["token"])
            await callback_query.message.edit_text("Account set as active. You can now start requests.")
        else:
            await callback_query.answer("Invalid account selected.")

    elif callback_query.data.startswith("delete_account_"):
        index = int(callback_query.data.split("_")[-1])
        tokens = get_tokens(user_id)
        if index < len(tokens):
            delete_token(user_id, tokens[index]["token"])
            await callback_query.message.edit_text("Account has been deleted.", reply_markup=back_markup)
        else:
            await callback_query.answer("Invalid account selected.")

    elif callback_query.data == "start":
        if state["running"]:
            await callback_query.answer("Requests are already running!")
        else:
            state["running"] = True
            try:
                status_message = await callback_query.message.edit_text("Initializing requests...", reply_markup=stop_markup)
                state["status_message_id"] = status_message.message_id
                state["pinned_message_id"] = status_message.message_id
                await bot.pin_chat_message(chat_id=user_id, message_id=state["status_message_id"])
                asyncio.create_task(run_requests(user_id))
                await callback_query.answer("Requests started!")
            except Exception as e:
                logging.error(f"Error while starting requests: {e}")
                await callback_query.message.edit_text("Failed to start requests. Please try again later.", reply_markup=start_markup)
                state["running"] = False

    elif callback_query.data == "stop":
        if not state["running"]:
            await callback_query.answer("Requests are not running!")
        else:
            state["running"] = False
            message_text = f"Requests stopped. Use the button below to start again.\nTotal Added Friends: {state['total_added_friends']}"
            await callback_query.message.edit_text(message_text, reply_markup=start_markup)
            await callback_query.answer("Requests stopped.")
            if state["pinned_message_id"]:
                await bot.unpin_chat_message(chat_id=user_id, message_id=state["pinned_message_id"])
                state["pinned_message_id"] = None

    elif callback_query.data == "show_account_info":
        token = get_current_account(user_id)
        if not token:
            await callback_query.message.edit_text("No active account token found. Please set an account before requesting account info.", reply_markup=back_markup)
            return
        account_info = await fetch_account_info(token)
        if account_info:
            await callback_query.message.edit_text(
                f"<b>Name:</b> {html.escape(account_info.get('name', 'N/A'))}\n"
                f"<b>Email:</b> {html.escape(account_info.get('email', 'N/A'))}\n"
                f"<b>Birth Year:</b> {html.escape(str(account_info.get('birthYear', 'N/A')))}\n"
                f"<b>Nationality:</b> {html.escape(account_info.get('nationalityCode', 'N/A'))}\n"
                f"<b>Languages:</b> {html.escape(', '.join(account_info.get('languageCodes', [])))}\n"
                f"<b>Description:</b> {html.escape(account_info.get('description', 'N/A'))}\n"
                "Photos: " + ' '.join([f"<a href='{html.escape(url)}'>Photo</a>" for url in account_info.get('photoUrls', [])]),
                parse_mode="HTML", reply_markup=back_markup)
        else:
            await callback_query.message.edit_text("Failed to retrieve account information.", reply_markup=back_markup)

    elif callback_query.data == "invoke":
        tokens = get_tokens(user_id)
        expired_tokens = []
        for token in tokens:
            account_info = await fetch_account_info(token["token"])
            if account_info is None:
                expired_tokens.append(token["token"])

        if expired_tokens:
            for token in expired_tokens:
                delete_token(user_id, token)
                await callback_query.message.edit_text(f"Deleted expired token: {token[:5]}...")
        else:
            await callback_query.message.edit_text("No expired tokens found.")

    elif callback_query.data == "back_to_menu":
        await callback_query.message.edit_text("Welcome! Use the buttons below to navigate.", reply_markup=start_markup)

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="invoke", description="Delete expired accounts")
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_bot_commands()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
