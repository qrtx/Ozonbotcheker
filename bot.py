from keep_alive import keep_alive

import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import aiohttp
import asyncio
import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
FIREBASE_URL = os.getenv("FIREBASE_URL")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

user_step = {}

async def get_firebase(path):
    async with aiohttp.ClientSession() as session:
        async with session.get(FIREBASE_URL + path + ".json") as resp:
            return await resp.json()

async def post_firebase(path, data):
    async with aiohttp.ClientSession() as session:
        async with session.post(FIREBASE_URL + path + ".json", json=data) as resp:
            return await resp.json()

async def delete_message(chat_id, message_id):
    try:
        await bot.delete_message(chat_id, message_id)
    except:
        pass

@dp.message_handler(commands=["check"])
async def check_start(message: types.Message):
    employees = await get_firebase("employees")
    if not employees:
        await message.reply("Список сотрудников пуст.")
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    for emp in employees.values():
        keyboard.insert(InlineKeyboardButton(text=emp, callback_data="emp_" + emp))

    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    msg = await message.reply("Выберите своё имя:", reply_markup=keyboard)
    user_step[message.from_user.id] = {"step": "await_name", "msg_id": msg.message_id}

@dp.callback_query_handler(lambda c: c.data.startswith("emp_"))
async def select_employee(callback: types.CallbackQuery):
    emp = callback.data[4:]
    points = await get_firebase("points")
    if not points:
        await callback.answer("Нет доступных пунктов")
        return

    await delete_message(callback.message.chat.id, callback.message.message_id)

    keyboard = InlineKeyboardMarkup(row_width=1)
    for p in points.keys():
        keyboard.add(InlineKeyboardButton(text=p, callback_data="pnt_" + p))

    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    msg = await bot.send_message(callback.message.chat.id, f"{emp}, выберите пункт:", reply_markup=keyboard)
    user_step[callback.from_user.id] = {
        "step": "await_point",
        "name": emp,
        "msg_id": msg.message_id
    }

@dp.callback_query_handler(lambda c: c.data.startswith("pnt_"))
async def select_point(callback: types.CallbackQuery):
    point = callback.data[4:]
    step = user_step.get(callback.from_user.id)

    if not step or step["step"] != "await_point":
        await callback.answer("Сначала выберите имя")
        return

    name = step["name"]
    await delete_message(callback.message.chat.id, step["msg_id"])

    now = datetime.datetime.now().strftime("%Y-%m-%d")
    data = {"employee": name, "point": point, "date": now}
    await post_firebase("shifts", data)

    await bot.send_message(callback.message.chat.id, f"{name} отметил(ся/ась) на пункте {point} — {now}!")

if __name__ == "__main__":
    keep_alive()
    executor.start_polling(dp, skip_updates=True)


@dp.callback_query_handler(lambda c: c.data == "cancel")
async def cancel_action(callback: types.CallbackQuery):
    await delete_message(callback.message.chat.id, callback.message.message_id)
    user_step.pop(callback.from_user.id, None)
    await callback.answer("Действие отменено", show_alert=False)
