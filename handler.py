"""
Core handler module for the Telegram AI chatbot.
This module contains all the message handlers, callback processors, and bot commands.
It manages user interactions, GPT model integration, voice responses, and menu navigation.
Main functionalities include:
- Command handlers (/start, /help, etc.)
- Menu callback processors
- GPT text and image processing
- Voice message handling
- User data management
"""

import asyncio
import base64
import configparser
import logging
from datetime import datetime
from pathlib import Path

import pytz
from aiogram import Router, F, Bot, types, flags
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session import aiohttp
from aiogram.enums import ParseMode
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from aiogram.types import Message, FSInputFile
from aiogram.utils.formatting import Text, Bold
from openai import OpenAI

from base import get_or_create_user_data, save_user_data
from buttons import (
    keyboard_model,
    keyboard_context,
    keyboard_voice,
    keyboard_value_work,
)
from buttons import keyboard_pic, keyboard
from function import info_menu_func
from function import prune_messages, process_voice_message, simple_bot_responses
from middlewares import ThrottlingMiddleware
from text import start_message, help_message, system_message_text

# Set the timezone
timezone = pytz.timezone("Europe/Madrid")

# Getting the current date and time
current_datetime = datetime.now(timezone)

# Formatting date and time
formatted_datetime = current_datetime.strftime("%d.%m.%Y %H:%M:%S")

# Reading parameters from config.ini
config = configparser.ConfigParser()

config.read(Path(__file__).parent / "config.ini")

TOKEN = config.get("Telegram", "token")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Parameters for OpenAI
openai_api_key = config.get("OpenAI", "api_key")

# Using parameters for initializing OpenAI
client = OpenAI(api_key=openai_api_key)

# Reading the user IDs
OWNER_ID = int(config.get("Telegram", "owner_id"))
ADMIN_ID = int(config.get("Telegram", "admin_id"))

# Global variable to control all users access
ALL_USERS_ACCESS = False

# Initializing the router
router = Router()

router.message.middleware(ThrottlingMiddleware(spin=1.5))

last_message_id = {}

# Function to check user access
async def checkAccess(message: Message) -> bool:
    """
    Check if the user has access to the bot.
    
    Args:
        message (Message): The incoming Telegram message
    
    Returns:
        bool: True if the user has access, False otherwise
    """
    user_id = message.from_user.id
    
    # Always allow
    if user_id == OWNER_ID or user_id == ADMIN_ID:
        return True
    
    # Check if all users are allowed
    if ALL_USERS_ACCESS:
        return True
    
    # Deny access with a message
    await message.answer(
        f"<i>Sorry, you do not have access to this bot.\n"
        f"User ID:</i> <b>{user_id}</b>"
    )
    return False

# Commands for access control
@router.message(F.text == "/enable_all")
async def enable_all_access(message: Message):
    """
    Command to enable bot access for all users.
    Only users in OWNER_ID can use this command.
    """
    user_id = message.from_user.id
    
    # Ensure who can use this command
    if user_id != OWNER_ID and user_id != ADMIN_ID:
        await message.answer("You do not have permission to use this command.")
        return
    
    global ALL_USERS_ACCESS
    ALL_USERS_ACCESS = True
    await message.answer("Bot access has been enabled for all users.")

@router.message(F.text == "/disable_all")
async def disable_all_access(message: Message):
    """
    Command to disable bot access for non-owner users.
    Only users in OWNER_ID can use this command.
    """
    user_id = message.from_user.id
    
    # Ensure who can use this command
    if user_id != OWNER_ID and user_id != ADMIN_ID:
        await message.answer("You do not have permission to use this command.")
        return
    
    global ALL_USERS_ACCESS
    ALL_USERS_ACCESS = False
    await message.answer("Bot access has been disabled for all non-owner users. Owner access remains unaffected.")

# Creating a class for the state machine
class ChangeValueState(StatesGroup):
    waiting_for_new_value = State()

# Handler for the /start command
@router.message(F.text == "/start")
@flags.throttling_key("spin")
async def command_start_handler(message: Message, state: FSMContext):
    if not await checkAccess(message):
        return

    if state is not None:
        await state.clear()

    # Retrieving or creating user data objects
    user_data = await get_or_create_user_data(message.from_user.id)

    user_data.model = "gpt-4o-mini"
    user_data.model_message_info = "4o mini"
    user_data.model_message_chat = "4o mini:\n\n"
    user_data.messages = []
    user_data.count_messages = 0
    user_data.max_out = 128000
    user_data.voice_answer = False
    user_data.system_message = ""
    user_data.pic_grade = "standard"
    user_data.pic_size = "1024x1024"

    # Saving updated data to the database
    await save_user_data(message.from_user.id)

    await message.answer(start_message)
    return


@router.message(F.text == "/menu")
@flags.throttling_key("spin")
async def process_key_button(message: Message, state: FSMContext):
    if not await checkAccess(message):
        return

    if state is not None:
        await state.clear()

    info_menu = await info_menu_func(message.from_user.id)
    
    await message.answer(text=f"{info_menu}", reply_markup=keyboard)
    return


@router.callback_query(F.data == "model_choice")
async def process_callback_model_choice(
        callback_query: CallbackQuery, state: FSMContext
):
    if not await checkAccess(callback_query.message):
        return

    if state is not None:
        await state.clear()

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"<i>Model:</i> {user_data.model_message_info} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "gpt_4o_mini")
async def process_callback_menu_1(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if user_data.model == "gpt-4o-mini":
        await callback_query.answer()
        return

    user_data.model = "gpt-4o-mini"
    user_data.max_out = 128000
    user_data.model_message_info = "4o mini"
    user_data.model_message_chat = "4o mini:\n\n"

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"<i>Model:</i> {user_data.model_message_info} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "gpt_4_o")
async def process_callback_menu_2(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if user_data.model == "gpt-4o":
        await callback_query.answer()
        return

    user_data.model = "gpt-4o"
    user_data.max_out = 128000
    user_data.model_message_info = "4o"
    user_data.model_message_chat = "4o:\n\n"

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"<i>Model:</i> {user_data.model_message_info} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "gpt_o1_mini")
async def process_callback_menu_1(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if user_data.model == "o1-mini":
        await callback_query.answer()
        return

    user_data.model = "o1-mini"
    user_data.max_out = 128000
    user_data.model_message_info = "o1 mini"
    user_data.model_message_chat = "o1 mini:\n\n"

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"<i>Model:</i> {user_data.model_message_info} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "gpt_o1_preview")
async def process_callback_menu_2(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if user_data.model == "o1-preview":
        await callback_query.answer()
        return

    user_data.model = "o1-preview"
    user_data.max_out = 128000
    user_data.model_message_info = "o1"
    user_data.model_message_chat = "o1:\n\n"

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"<i>Model:</i> {user_data.model_message_info} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "dall_e_3")
async def process_callback_menu_3(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if user_data.model == "dall-e-3":
        await callback_query.answer()
        return

    user_data.model = "dall-e-3"
    user_data.model_message_info = "DALL·E 3"
    user_data.model_message_chat = "DALL·E 3:\n\n"

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"<i>Model:</i> {user_data.model_message_info} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "pic_setup")
async def process_callback_menu_pic_setup(
        callback_query: CallbackQuery, state: FSMContext
):
    if not await checkAccess(callback_query.message):
        return

    if state is not None:
        await state.clear()

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"{user_data.pic_grade} : {user_data.pic_size} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "set_sd")
async def process_callback_set_sd(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if user_data.pic_grade == "standard":
        await callback_query.answer()
        return

    user_data.pic_grade = "standard"

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"{user_data.pic_grade} : {user_data.pic_size} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "set_hd")
async def process_callback_set_hd(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if user_data.pic_grade == "hd":
        await callback_query.answer()
        return

    user_data.pic_grade = "hd"

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"{user_data.pic_grade} : {user_data.pic_size} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "set_1024x1024")
async def process_callback_set_1024x1024(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if user_data.pic_size == "1024x1024":
        await callback_query.answer()
        return

    user_data.pic_size = "1024x1024"

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"{user_data.pic_grade} : {user_data.pic_size} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "set_1024x1792")
async def process_callback_set_1024x1792(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if user_data.pic_size == "1024x1792":
        await callback_query.answer()
        return

    user_data.pic_size = "1024x1792"

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"{user_data.pic_grade} : {user_data.pic_size} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "set_1792x1024")
async def process_callback_set_1792x1024(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if user_data.pic_size == "1792x1024":
        await callback_query.answer()
        return

    user_data.pic_size = "1792x1024"

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"{user_data.pic_grade} : {user_data.pic_size} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "context_work")
async def process_callback_context_work(
        callback_query: CallbackQuery, state: FSMContext
):
    if not await checkAccess(callback_query.message):
        return

    if state is not None:
        await state.clear()

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"<i>Messages:</i> {user_data.count_messages} ",
        reply_markup=keyboard_context,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "context")
async def process_callback_context(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    user_data = await get_or_create_user_data(callback_query.from_user.id)
    history = await generate_history(user_data.messages)

    if callback_query.message.text == "Context is empty":
        await callback_query.answer()
        return

    if not history:
        await callback_query.message.edit_text(
            text="Context is empty", reply_markup=keyboard_context
        )
        await callback_query.answer()
        return

    await send_history(callback_query.from_user.id, history)
    await callback_query.message.edit_text(text="Context:", reply_markup=None)
    await callback_query.answer()


async def generate_history(messages):
    return "\n\n".join(f"{msg['role']}:\n{msg['content']}" for msg in messages)


async def send_history(user_id, history):
    max_length = 4096
    # Split the story into lines
    lines = history.split("\n")
    chunks = []
    current_chunk = []

    current_length = 0
    for line in lines:
        line_length = len(line) + 1

        # Check if the current chunk length is exceeded
        if current_length + line_length > max_length:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_length = line_length
        else:
            current_chunk.append(line)
            current_length += line_length

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    for chunk in chunks:
        await send_message(user_id, chunk)

    await send_menu(user_id)


async def send_message(user_id, content):
    content_kwargs = Text(content)
    await bot.send_message(
        user_id,
        **content_kwargs.as_kwargs(),
        disable_web_page_preview=True,
    )


async def send_menu(user_id):
    await bot.send_message(
        user_id,
        text=f"Actions with context:",
        reply_markup=keyboard_context,
    )


@router.callback_query(F.data == "clear")
async def process_callback_clear(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    user_data.messages = []
    user_data.count_messages = 0

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    if callback_query.message.text == "Context cleared":
        await callback_query.answer()
        return

    await callback_query.message.edit_text(
        text="Context cleared", reply_markup=keyboard_context
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "voice_answer_work")
async def process_callback_voice_answer_work(
        callback_query: CallbackQuery, state: FSMContext
):
    if not await checkAccess(callback_query.message):
        return

    if state is not None:
        await state.clear()

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    info_voice_answer = "on" if user_data.voice_answer else "off"

    await callback_query.message.edit_text(
        text=f"<i>Audio:</i> {info_voice_answer}",
        reply_markup=keyboard_voice,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "voice_answer_add")
async def process_callback_voice_answer_add(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if user_data.voice_answer:
        await callback_query.answer()
        return

    user_data.voice_answer = True

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    info_voice_answer = "enabled" if user_data.voice_answer else "off"

    await callback_query.message.edit_text(
        text=f"<i>Audio:</i> {info_voice_answer}", reply_markup=keyboard_voice
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "voice_answer_del")
async def process_callback_voice_answer_del(callback_query: CallbackQuery):
    if not await checkAccess(callback_query.message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if not user_data.voice_answer:
        await callback_query.answer()
        return

    user_data.voice_answer = False

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    info_voice_answer = "on" if user_data.voice_answer else "off"

    await callback_query.message.edit_text(
        text=f"<i>Audio:</i> {info_voice_answer}",
        reply_markup=keyboard_voice,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "system_value_work")
async def process_callback_voice_answer_work(
        callback_query: CallbackQuery, state: FSMContext
):
    if not await checkAccess(callback_query.message):
        return

    if state is not None:
        await state.clear()

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    info_system_message = (
        "Undefined" if not user_data.system_message else user_data.system_message
    )

    await callback_query.message.edit_text(
        text=f"<i>Role:</i> {info_system_message}",
        reply_markup=keyboard_value_work,
    )

    await callback_query.answer()
    return


# Button click handler
@router.callback_query(F.data == "change_value")
async def process_callback_change_value(
        callback_query: types.CallbackQuery, state: FSMContext
):
    if not await checkAccess(callback_query.message):
        return

    await state.set_state(ChangeValueState.waiting_for_new_value)

    await callback_query.message.edit_text(
        text=system_message_text,
        reply_markup=None,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "delete_value")
async def process_callback_delete_value(callback_query: CallbackQuery, state: FSMContext):
    if not await checkAccess(callback_query.message):
        return

    if state is not None:
        await state.clear()

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    if not user_data.system_message:
        await callback_query.answer()
        return

    user_data.system_message = ""

    # Saving the updated data to the database
    await save_user_data(callback_query.from_user.id)

    info_system_message = (
        "Undefined" if not user_data.system_message else user_data.system_message
    )

    await callback_query.message.edit_text(
        text=f"<i>Role:</i> {info_system_message}",
        reply_markup=keyboard_value_work,
    )

    await callback_query.answer()
    return


# New value input handler
@router.message(StateFilter(ChangeValueState.waiting_for_new_value))
async def process_new_value(message: types.Message, state: FSMContext):
    if not await checkAccess(message):
        return

    global sys_massage

    if message.voice:
        sys_massage = await process_voice_message(bot, message, message.from_user.id)

    elif message.text:
        sys_massage = message.text

    # Your method of obtaining or creating user data
    user_data = await get_or_create_user_data(message.from_user.id)

    user_data.system_message = sys_massage

    # Saving the updated data to the database
    await save_user_data(message.from_user.id)

    await state.clear()

    info_system_message = (
        "Undefined" if not user_data.system_message else user_data.system_message
    )

    await message.answer(
        text=f"<i>Role:</i> {info_system_message}",
        reply_markup=keyboard_value_work,
    )
    return


@router.callback_query(F.data == "back_menu")
async def process_callback_menu_back(callback_query: CallbackQuery, state: FSMContext):
    if not await checkAccess(callback_query.message):
        return

    if state is not None:
        await state.clear()

    info_menu = await info_menu_func(callback_query.from_user.id)

    await callback_query.message.edit_text(
        text=f"{info_menu}", reply_markup=keyboard
    )
    return


@router.callback_query(F.data == "info")
async def process_callback_info(callback_query: CallbackQuery, state: FSMContext):
    if not await checkAccess(callback_query.message):
        return

    if state is not None:
        await state.clear()

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(callback_query.from_user.id)

    info_voice_answer = "on" if user_data.voice_answer else "off"

    info_system_message = (
        "Undefined" if not user_data.system_message else user_data.system_message
    )

    info_messages = (
        f"<i>Date:</i> <b>{formatted_datetime}</b>\n"
        f"<i>User ID:</i> <b>{callback_query.from_user.id}</b>\n"
        f"<i>Model:</i> <b>{user_data.model_message_info}</b>\n"
        f"<i>Image</i>\n"
        f"<i>Quality:</i> <b>{user_data.pic_grade}</b>\n"
        f"<i>Size:</i> <b>{user_data.pic_size}</b>\n"
        f"<i>Messages:</i> <b>{user_data.count_messages}</b>\n"
        f"<i>Audios:</i> <b>{info_voice_answer}</b>\n"
        f"<i>Role:</i> <b>{info_system_message}</b>"
    )

    await callback_query.message.edit_text(
        text=info_messages,
        reply_markup=None,
    )

    await callback_query.answer()
    return


@router.message(F.text == "/help")
@flags.throttling_key("spin")
async def help_handler(message: Message, state: FSMContext):
    if not await checkAccess(message):
        return

    if state is not None:
        await state.clear()

    # Retrieve or create user data objects
    await get_or_create_user_data(message.from_user.id)

    await message.answer(help_message)
    return


@router.message(F.content_type.in_({"text", "voice"}))
async def chatgpt_text_handler(message: Message):
    if not await checkAccess(message):
        return

    # Retrieve or create user data objects
    user_data = await get_or_create_user_data(message.from_user.id)

    user_prompt = ""

    # Temporary message
    response = await message.answer(f"⏳ Hold on, your request is being processed!")
    last_message_id = response.message_id

    if message.voice:
        user_prompt = await process_voice_message(bot, message, message.from_user.id)

    elif message.text:
        user_prompt = message.text

    # First, check for simple bot responses
    # from function import simple_bot_responses
    simple_response = await simple_bot_responses(user_prompt)
    if simple_response:
        await message.bot.delete_message(message.chat.id, last_message_id)
        await message.reply(simple_response)
        return

    # Rest of the existing code remains the same
    if (
            user_data.model == "gpt-4o-mini"
            or user_data.model == "gpt-4o"
            or user_data.model == "o1-mini"
            or user_data.model == "o1-preview"
    ):

        # Add the user's message to the chat history
        user_data.messages.append({"role": "user", "content": user_prompt})

        # Apply the trim function
        pruned_messages = await prune_messages(
            user_data.messages, max_chars=user_data.max_out
        )

        try:
            # Add Role system temporarily, without saving in context
            system_message = {
                "role": "system",
                "content": user_data.system_message,
            }

            if user_data.model == "gpt-4o-mini" or user_data.model == "gpt-4o":
                pruned_messages.insert(0, system_message)

            # Use asyncio.to_thread for OpenAI API call
            chat_completion = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model=user_data.model, messages=pruned_messages
                )
            )

            # The bot is typing...
            await message.bot.send_chat_action(message.chat.id, action="typing")

            # Getting the model's response
            response_message = chat_completion.choices[0].message.content

            # Adding the model's response to the chat history
            user_data.messages.append(
                {"role": "assistant", "content": response_message}
            )

            # User's message counter
            user_data.count_messages += 1

            # Saving the updated data to the database
            await save_user_data(message.from_user.id)

            # Deleting the temporary message
            await message.bot.delete_message(message.chat.id, last_message_id)

            # Function to send kwargs
            async def send_message_kwargs(
                    model_massage_kwargs, response_message_kwargs
            ):
                content_kwargs = Text(
                    Bold(model_massage_kwargs), response_message_kwargs
                )
                await message.reply(
                    **content_kwargs.as_kwargs(), disable_web_page_preview=True
                )

            async def send_message_kwargs_long(
                    model_message_kwargs, response_message_kwargs
            ):
                content = f"{model_message_kwargs}\n{response_message_kwargs}"  # Concatenate two parts of the message
                messages = content.split("\n")  # Split the message by \n
                chunk = ""
                chunks = []

                for line in messages:
                    if len(chunk) + len(line) + 1 > 4096:  # +1 for the newline character
                        chunks.append(chunk)
                        chunk = line
                    else:
                        if chunk:
                            chunk += line + "\n"
                        else:
                            chunk = line

                # Don't forget to add the last chunk
                if chunk:
                    chunks.append(chunk)

                for chunk in chunks:
                    content_kwargs = Text(chunk)
                    await message.answer(
                        **content_kwargs.as_kwargs(),
                        disable_web_page_preview=True,
                    )

            # Function to send Markdown (md)
            async def send_message_md(model_massage_md, response_md):
                final_message = f"*{model_massage_md}*{response_md}"
                await message.reply(
                    final_message,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )

            async def send_message_md_long(model_massage_md, response_md):
                final_message = f"*{model_massage_md}*\n{response_md}"

                lines = final_message.split("\n")
                chunks = []
                current_chunk = []

                for line in lines:
                    # If adding another line would exceed the limit, add the current chunk and start a new one
                    if len(current_chunk) + len(line) + 1 > 4096:  # +1 для \n
                        chunks.append("\n".join(current_chunk))
                        current_chunk = [line]
                    else:
                        current_chunk.append(line)

                ## Don't forget to add the last chunk
                if current_chunk:
                    chunks.append("\n".join(current_chunk))

                # Now send all chunks as separate messages
                for chunk in chunks:
                    await message.answer(
                        chunk,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True,
                    )

            async def text_to_speech(unic_id, text_message):
                """Generates a voice message from text using the OpenAI API."""
                speech_file_path = Path(__file__).parent / f"voice/speech_{unic_id}.mp3"

                response_voice = await asyncio.to_thread(
                    lambda: client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=text_message,
                    )
                )

                await asyncio.to_thread(
                    lambda: response_voice.stream_to_file(speech_file_path)
                )
                audio = FSInputFile(speech_file_path)

                return await bot.send_audio(
                    unic_id, audio, title="Audio answer option"
                )

            # Sending the model's response to the user
            try:
                if "```" in response_message:
                    if len(response_message) > 4096:
                        await send_message_md_long(
                            user_data.model_message_chat, response_message
                        )
                        if user_data.voice_answer:
                            await text_to_speech(message.chat.id, response_message)
                        return

                    await send_message_md(
                        user_data.model_message_chat, response_message
                    )
                    if user_data.voice_answer:
                        await text_to_speech(message.chat.id, response_message)
                    return

                else:
                    if len(response_message) > 4096:
                        await send_message_kwargs_long(
                            user_data.model_message_chat, response_message
                        )
                        if user_data.voice_answer:
                            await text_to_speech(message.chat.id, response_message)
                        return

                    await send_message_kwargs(
                        user_data.model_message_chat, response_message
                    )
                    if user_data.voice_answer:
                        await text_to_speech(message.chat.id, response_message)
                    return

            except Exception as e:
                logging.exception(e)
                if len(response_message) > 4096:
                    await send_message_kwargs_long(
                        user_data.model_message_chat, response_message
                    )
                    if user_data.voice_answer:
                        await text_to_speech(message.chat.id, response_message)
                    return

                await send_message_kwargs(
                    user_data.model_message_chat, response_message
                )
                if user_data.voice_answer:
                    await text_to_speech(message.chat.id, response_message)
                return

        except Exception as e:
            logging.exception(e)
            await message.reply(f"An error occurred: {e}")
            return

    elif user_data.model == "dall-e-3":

        try:
            # Use asyncio.to_thread for OpenAI API call
            response = await asyncio.to_thread(
                lambda: client.images.generate(
                    model="dall-e-3",
                    prompt=user_prompt,
                    n=1,
                    size=user_data.pic_size,
                    quality=user_data.pic_grade,
                )
            )

        except Exception as e:
            logging.exception(e)
            await message.reply(f"An error occurred: {e}")
            return

        # The bot is uploading a photo...
        await message.bot.send_chat_action(message.chat.id, action="upload_photo")

        # User's message counter
        user_data.count_messages += 1

        # Saving the updated data to the database
        await save_user_data(message.from_user.id)

        # Deleting the temporary message
        await message.bot.delete_message(message.chat.id, last_message_id)

        await message.bot.send_photo(
            message.chat.id,
            response.data[0].url,
            reply_to_message_id=message.message_id,
        )
        return


@router.message(F.photo)
async def chatgpt_photo_vision_handler(message: types.Message, state: FSMContext):
    if not await checkAccess(message):
        return

    if state is not None:
        await state.clear()

    try:
        user_data = await get_or_create_user_data(message.from_user.id)
        temp_message = await message.answer("⏳ Hold on, your request is being processed!")

        text = message.caption or "What's in the picture?"
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"

        base64_image = await download_and_encode_image(file_url)

        ai_response = await process_image_with_gpt(text, base64_image)

        await update_user_data(user_data, message.from_user.id)
        await message.bot.delete_message(message.chat.id, temp_message.message_id)
        await message.answer(ai_response)

    except Exception as e:
        logging.exception(e)
        await message.reply(f"An error occurred: {e}")


async def download_and_encode_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                image_content = await resp.read()
                base64_image = base64.b64encode(image_content).decode("utf-8")
                return f"data:image/jpeg;base64,{base64_image}"
    raise ValueError("Failed to download image")


async def process_image_with_gpt(text, base64_image):
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": base64_image}},
            ],
        }
    ]
    chat_completion = await asyncio.to_thread(
        lambda: client.chat.completions.create(
            model="gpt-4o", messages=messages, max_tokens=4000
        )
    )
    return chat_completion.choices[0].message.content


async def update_user_data(user_data, user_id):
    user_data.count_messages += 1
    await save_user_data(user_id)
