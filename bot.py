
import os
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from keep_alive import keep_alive
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
FIREBASE_URL = os.getenv("FIREBASE_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

user_state = {}

async def get_firebase(path):
    async with aiohttp.ClientSession() as session:
        async with session.get(FIREBASE_URL + path + ".json") as resp:
            return await resp.json()

async def post_firebase(path, data):
    async with aiohttp.ClientSession() as session:
        async with session.post(FIREBASE_URL + path + ".json", json=data) as resp:
            return await resp.json()

@dp.message_handler(commands=["start", "check"])
async def check_start(message: types.Message):
    employees = await get_firebase("employees")
    if not employees:
        await message.answer("Список сотрудников пуст.")
        return

    keyboard = InlineKeyboardMarkup()
    for key in employees:
        keyboard.add(InlineKeyboardButton(employees[key], callback_data=f"user:{employees[key]}"))
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    await message.answer("Кто вы?", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith("user:"))
async def select_user(callback_query: types.CallbackQuery):
    name = callback_query.data.split(":")[1]
    user_state[callback_query.from_user.id] = {"name": name}

    points = await get_firebase("points")
    keyboard = InlineKeyboardMarkup()
    for point in points:
        keyboard.add(InlineKeyboardButton(f"{point}", callback_data=f"point:{point}"))
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text=f"Привет, {name}! Где ты сегодня работаешь?",
                                reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith("point:"))
async def select_point(callback_query: types.CallbackQuery):
    point = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id
    name = user_state.get(user_id, {}).get("name")

    if not name:
        await bot.answer_callback_query(callback_query.id, "Ошибка: имя не выбрано.")
        return

    now = asyncio.get_event_loop().time()
    from datetime import datetime
    dt = datetime.now()
    date = f"{dt.year}-{dt.month:02}-{dt.day:02}"

    await post_firebase("shifts", {
        "employee": name,
        "point": point,
        "date": date
    })

    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text=f"✅ {name} отметил(ся/ась) на пункте {point} — {date}!")

@dp.callback_query_handler(lambda c: c.data == "cancel")
async def cancel_callback(callback_query: types.CallbackQuery):
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text="❌ Отменено")

keep_alive()
executor.start_polling(dp)
