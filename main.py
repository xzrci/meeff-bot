 
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

API_TOKEN = "7653663622:AAESlxbzSCDdxlOt1zf0_yYOHyxD_xJLfvY"
MEEFF_ACCESS_TOKEN = "92K26S09E6QFT7WGH2H3P0UJ62O5E61WTIMAOO507BA2B3XN3X2SF1KYFFK1V8DVACGK9501ST1X0A130AEN4O32ACQ0QFS30MDTXTNN34DRG0WJI5KX0FTDJN690VWIEUUKXJJDUJYWZPF86UCYUAHJSU0RG8PITK6NNMLQB248Z99CYB0IQ7X6BFSI72MLN4NCF90UOXO66MDV9VJZOEAG2AG82PD4I7N9T1XDI4W7C5JTIZSE7VNRXYT7NXVY"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

running = False

# Start button
start_stop_markup = InlineKeyboardMarkup(row_width=2)
start_button = InlineKeyboardButton("Start Requests", callback_data="start")
stop_button = InlineKeyboardButton("Stop Requests", callback_data="stop")
start_stop_markup.add(start_button, stop_button)

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
            print(json_res)

async def run_requests():
    global running
    count = 0
    async with aiohttp.ClientSession() as session:
        while running:
            users = await fetch_users(session)
            await process_users(session, users)
            count += 1
            await asyncio.sleep(5)
            print(f"Processed batch: {count}")

@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    await message.answer("Welcome! Use the buttons below to start or stop requests.", reply_markup=start_stop_markup)

@dp.callback_query_handler(lambda c: c.data in ["start", "stop"])
async def callback_handler(callback_query: types.CallbackQuery):
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

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
