import aiohttp
import asyncio
import logging

LOUNGE_URL = "https://api.meeff.com/lounge/dashboard/v1"
CHATROOM_URL = "https://api.meeff.com/chatroom/open/v2"
SEND_MESSAGE_URL = "https://api.meeff.com/chat/send/v2"
HEADERS = {
    'User-Agent': "okhttp/4.12.0",
    'Accept-Encoding': "gzip",
    'content-type': "application/json; charset=utf-8"
}

async def fetch_lounge_users(token):
    headers = HEADERS.copy()
    headers['meeff-access-token'] = token
    params = {'locale': "en"}

    async with aiohttp.ClientSession() as session:
        async with session.get(LOUNGE_URL, params=params, headers=headers) as response:
            if response.status != 200:
                logging.error(f"Failed to fetch lounge users: {response.status}")
                return []
            data = await response.json()
            return data.get("both", [])

async def open_chatroom(token, user_id):
    headers = HEADERS.copy()
    headers['meeff-access-token'] = token
    payload = {
        "waitingRoomId": user_id,
        "locale": "en"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(CHATROOM_URL, json=payload, headers=headers) as response:
            if response.status != 200:
                logging.error(f"Failed to open chatroom: {response.status}")
                return None
            data = await response.json()
            return data.get("chatRoom", {}).get("_id")

async def send_message(token, chatroom_id, message):
    headers = HEADERS.copy()
    headers['meeff-access-token'] = token
    payload = {
        "chatRoomId": chatroom_id,
        "message": message,
        "locale": "en"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(SEND_MESSAGE_URL, json=payload, headers=headers) as response:
            if response.status != 200:
                logging.error(f"Failed to send message: {response.status}")
                return None
            return await response.json()

async def send_lounge(token, message="hi", status_message=None, bot=None, chat_id=None):
    sent_count = 0
    total_users = 0

    while True:
        users = await fetch_lounge_users(token)
        if not users:
            logging.info("No users found in the lounge.")
            break

        total_users += len(users)
        for user in users:
            user_id = user["user"]["_id"]
            chatroom_id = await open_chatroom(token, user_id)
            if chatroom_id:
                await send_message(token, chatroom_id, message)
                sent_count += 1
                if bot and chat_id and status_message:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_message.message_id,
                        text=f"Lounge Users: {total_users} Message sent: {sent_count}",
                    )
                logging.info(f"Sent message to {user['user']['name']} in chatroom {chatroom_id}.")
            await asyncio.sleep(0.02)  # Avoid hitting API rate limits

    logging.info(f"Finished sending messages. Total Lounge Users: {total_users}, Messages sent: {sent_count}")
