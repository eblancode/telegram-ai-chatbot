import asyncio
import configparser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from aiogram import Bot, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from openai import OpenAI
from pydub import AudioSegment

#from mistralai import Mistral

from base import get_or_create_user_data

# Reading parameters from config.in
config = configparser.ConfigParser()
config.read(Path(__file__).parent / "config.ini")

TOKEN = config.get("Telegram", "token")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Parameters for OpenAI
openai_api_key = config.get("OpenAI", "api_key")

# Using parameters for OpenAI initialization
client = OpenAI(api_key=openai_api_key)


async def info_menu_func(user_id):
    user_data = await get_or_create_user_data(user_id)

    info_voice_answer = "Enabled" if user_data.voice_answer else "Disabled"
    info_system_message = "Set" if user_data.system_message else "Absent"

    info_menu = (
        f"<i>Messages:</i> <b>{user_data.count_messages}</b>\n"
        f"<i>Model:</i> <b>{user_data.model_message_info}</b>\n"
        f"<i>Audio:</i> <b>{info_voice_answer}</b>\n"
        f"<i>Role:</i> <b>{info_system_message}</b>\n"
        f"<i>Picture</i>\n"
        f"<i>Quality:</i> <b>{user_data.pic_grade}</b>\n"
        f"<i>Size:</i> <b>{user_data.pic_size}</b>"
    )
    return info_menu


async def prune_messages(messages, max_chars):
    pruned_messages = []
    total_chars = 0

    for message in reversed(messages):
        content_length = len(message["content"])
        remaining_chars = max_chars - total_chars

        if remaining_chars <= 0:
            break

        if content_length > remaining_chars:
            pruned_content = message["content"][:remaining_chars]
            pruned_messages.append({"role": message["role"], "content": pruned_content})
            break

        pruned_messages.append(message)
        total_chars += content_length

    return list(reversed(pruned_messages))


async def process_voice_message(bot: Bot, message: types.Message, user_id: int):
    # Obtaining the ID of the voice message file
    file_id = message.voice.file_id
    file_info = await bot.get_file(file_id)
    ogg_path = Path(__file__).parent / f"voice/voice_{user_id}.ogg"
    mp3_path = Path(__file__).parent / f"voice/voice_{user_id}.mp3"

    # Downloading the file
    await bot.download_file(file_info.file_path, ogg_path)

    # Audio conversion in a separate thread
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        await loop.run_in_executor(
            pool,
            lambda: AudioSegment.from_ogg(ogg_path).export(mp3_path, format="mp3"),
        )

    # Using asyncio.to_thread for calling the OpenAI API
    with open(mp3_path, "rb") as audio_file:
        transcription = await asyncio.to_thread(
            lambda: client.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )
        )
        sys_message = transcription.text
        return sys_message
