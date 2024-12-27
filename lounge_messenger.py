import requests
import json
import logging

LOUNGE_URL = "https://api.meeff.com/lounge/dashboard/v1"
CHATROOM_OPEN_URL = "https://api.meeff.com/chatroom/open/v2"
SEND_MESSAGE_URL = "https://api.meeff.com/chat/send/v2"

HEADERS = {
  'User-Agent': "okhttp/4.12.0",
  'Accept-Encoding': "gzip",
  'meeff-access-token': "YOUR_ACCESS_TOKEN",
  'content-type': "application/json; charset=utf-8"
}

async def get_lounge_users():
    params = {'locale': "en"}
    response = requests.get(LOUNGE_URL, params=params, headers=HEADERS)
    if response.status_code != 200:
        logging.error(f"Failed to fetch lounge users: {response.status_code}")
        return []
    return response.json().get("both", [])

async def open_chatroom_and_send_message(user_id, message_text):
    payload = {
        "waitingRoomId": user_id,
        "locale": "en"
    }
    response = requests.post(CHATROOM_OPEN_URL, data=json.dumps(payload), headers=HEADERS)
    if response.status_code != 200:
        logging.error(f"Failed to open chatroom: {response.status_code}")
        return None
    chatroom_id = response.json().get("chatRoom", {}).get("_id")
    if not chatroom_id:
        logging.error("Failed to get chatroom ID")
        return None

    message_payload = {
        "chatRoomId": chatroom_id,
        "message": message_text,
        "locale": "en"
    }
    message_response = requests.post(SEND_MESSAGE_URL, data=json.dumps(message_payload), headers=HEADERS)
    if message_response.status_code != 200:
        logging.error(f"Failed to send message: {message_response.status_code}")
        return None
    logging.info(f"Message sent to user {user_id} in chatroom {chatroom_id}")
    return message_response.json()

async def send_messages_to_all_in_lounge(message_text):
    users = await get_lounge_users()
    for user in users:
        user_id = user.get("_id")
        if user_id:
            await open_chatroom_and_send_message(user_id, message_text)
