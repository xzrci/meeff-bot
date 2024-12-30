from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_filter_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Gender", callback_data="filter_gender")],
        [InlineKeyboardButton(text="Age", callback_data="filter_age")],
        [InlineKeyboardButton(text="Nationality", callback_data="filter_nationality")],
        [InlineKeyboardButton(text="Show Current Filters", callback_data="show_filters")],
        [InlineKeyboardButton(text="Back", callback_data="back_to_menu")]
    ])
    return keyboard

def get_gender_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="All Gender", callback_data="filter_gender_all")],
        [InlineKeyboardButton(text="Male", callback_data="filter_gender_male")],
        [InlineKeyboardButton(text="Female", callback_data="filter_gender_female")],
        [InlineKeyboardButton(text="Back", callback_data="filter_back")]
    ])
    return keyboard

def get_age_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(age), callback_data=f"filter_age_{age}") for age in range(18, 41)],
        [InlineKeyboardButton(text="Back", callback_data="filter_back")]
    ])
    return keyboard

def get_nationality_keyboard():
    countries = ["RU", "US", "PK", "IN", "DE", "FR", "BR", "CN", "JP", "KR", "CA", "AU", "IT", "ES", "ZA"]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="All Countries", callback_data="filter_nationality_all")],
        *[[InlineKeyboardButton(text=country, callback_data=f"filter_nationality_{country}")] for country in countries],
        [InlineKeyboardButton(text="Back", callback_data="filter_back")]
    ])
    return keyboard
