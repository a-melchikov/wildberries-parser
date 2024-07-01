from aiogram import F, types, Router
from aiogram.filters import Command, or_f

user_private_router = Router()


async def start_cmd(message: types.Message):
    await message.answer("Привет, я виртуальный помощник")


@user_private_router.message(or_f(Command("menu"), (F.text.lower() == "меню")))
async def menu_cmd(message: types.Message):
    await message.answer("Вот меню:")


@user_private_router.message(F.text.lower() == "о нас")
@user_private_router.message(Command("about"))
async def about_cmd(message: types.Message):
    await message.answer("О нас:")
