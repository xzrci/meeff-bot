from aiogram import types
import requests
import json
from db import get_current_account, get_user_filters, set_user_filters
from common import get_filter_keyboard, get_gender_keyboard, get_age_keyboard, get_nationality_keyboard

async def set_filter(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    token = get_current_account(user_id)
    
    if not token:
        await callback_query.message.edit_text("No active account found. Please set an account before updating filters.")
        return
    
    # Retrieve stored user filters
    user_filters = get_user_filters(user_id, token) or {}

    # Filter data to be updated
    filter_data = {
        "filterGenderType": user_filters.get("filterGenderType", 7),
        "filterBirthYearFrom": user_filters.get("filterBirthYearFrom", 1979),
        "filterBirthYearTo": 2006,      # Default value
        "filterDistance": 510,          # Default value
        "filterLanguageCodes": user_filters.get("filterLanguageCodes", ""),
        "filterNationalityBlock": user_filters.get("filterNationalityBlock", 0),
        "filterNationalityCode": user_filters.get("filterNationalityCode", ""),
        "locale": "en"  # Ensure locale is always included
    }

    if callback_query.data == "filter_gender":
        await callback_query.message.edit_text("Select Gender:", reply_markup=get_gender_keyboard())
        return

    if callback_query.data.startswith("filter_gender_"):
        gender = callback_query.data.split("_")[-1]
        if gender == "male":
            filter_data["filterGenderType"] = 6
        elif gender == "female":
            filter_data["filterGenderType"] = 5
        elif gender == "all":
            filter_data["filterGenderType"] = 7
        message = f"Filter updated: Gender set to {gender.capitalize()}"
    
    elif callback_query.data == "filter_age":
        await callback_query.message.edit_text("Select Age:", reply_markup=get_age_keyboard())
        return

    elif callback_query.data.startswith("filter_age_"):
        age = int(callback_query.data.split("_")[-1])
        current_year = 2024  # Current year
        filter_data["filterBirthYearFrom"] = current_year - age
        filter_data["filterBirthYearTo"] = 2006
        message = f"Filter updated: Age set to {age}"
    
    elif callback_query.data == "filter_nationality":
        await callback_query.message.edit_text("Select Nationality:", reply_markup=get_nationality_keyboard())
        return

    elif callback_query.data.startswith("filter_nationality_"):
        nationality = callback_query.data.split("_")[-1]
        if nationality == "all":
            filter_data["filterNationalityCode"] = ""
        else:
            filter_data["filterNationalityCode"] = nationality
        message = f"Filter updated: Nationality set to {nationality}"

    # Update user filters in storage
    set_user_filters(user_id, token, filter_data)

    url = "https://api.meeff.com/user/updateFilter/v1"
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Accept-Encoding': "gzip",
        'meeff-access-token': token,
        'content-type': "application/json; charset=utf-8"
    }

    print(f"Updating filters with data: {filter_data}")  # Debug statement
    response = requests.post(url, data=json.dumps(filter_data), headers=headers)
    if response.status_code == 200:
        await callback_query.message.edit_text(message)
    else:
        await callback_query.message.edit_text(f"Failed to update filter. Response: {response.text}")

async def filter_command(message: types.Message):
    await message.answer("Set your filter preferences:", reply_markup=get_filter_keyboard())
