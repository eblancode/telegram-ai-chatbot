# Define button texts and callback data
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

BUTTONS_ALL = [
    ("Model Selection", "model_choice"),
    ("Image Settings", "pic_setup"),
    ("Context Actions", "context_work"),
    ("Voice Responses", "voice_answer_work"),
    ("System Role", "system_value_work"),
    ("Information", "info"),
]

# Create inline keyboard buttons
inline_buttons = [
    InlineKeyboardButton(text=text, callback_data=data) for text, data in BUTTONS_ALL
]

# Create main keyboard
keyboard = InlineKeyboardMarkup(inline_keyboard=[[button] for button in inline_buttons])

# Create main buttons
pic_buttons = [
    ("SD", "set_sd"),
    ("HD", "set_hd"),
    ("1024x1024", "set_1024x1024"),
    ("1024x1792", "set_1024x1792"),
    ("1792x1024", "set_1792x1024"),
    ("Back to Menu", "back_menu"),
]

#
inline_buttons_pic = [
    InlineKeyboardButton(text=text, callback_data=data) for text, data in pic_buttons
]

#
keyboard_pic = InlineKeyboardMarkup(
    inline_keyboard=[[button] for button in inline_buttons_pic]
)

BUTTONS_MODEL = [
    ("4o mini", "gpt_4o_mini"),
    ("4o", "gpt_4_o"),
    ("o1 mini", "gpt_o1_mini"),
    ("o1", "gpt_o1_preview"),
    ("DALL·E 3", "dall_e_3"),
    ("Back to Menu", "back_menu"),
]

# Create inline keyboard buttons
inline_buttons_model = [
    InlineKeyboardButton(text=text, callback_data=data) for text, data in BUTTONS_MODEL
]

# Create main keyboard
keyboard_model = InlineKeyboardMarkup(
    inline_keyboard=[[button] for button in inline_buttons_model]
)

BUTTONS_CONTEXT = [
    ("Display Context", "context"),
    ("Clear Context", "clear"),
    ("Back to Menu", "back_menu"),
]

# Create inline keyboard buttons
inline_buttons_context = [
    InlineKeyboardButton(text=text, callback_data=data)
    for text, data in BUTTONS_CONTEXT
]

# Create main keyboard
keyboard_context = InlineKeyboardMarkup(
    inline_keyboard=[[button] for button in inline_buttons_context]
)

BUTTONS_VOICE = [
    ("Enable Audio Response", "voice_answer_add"),
    ("Disable Audio Response", "voice_answer_del"),
    ("Back to Menu", "back_menu"),
]

# Create inline keyboard buttons
inline_buttons_voice = [
    InlineKeyboardButton(text=text, callback_data=data) for text, data in BUTTONS_VOICE
]

# Create main keyboard
keyboard_voice = InlineKeyboardMarkup(
    inline_keyboard=[[button] for button in inline_buttons_voice]
)

BUTTONS_VALUE_WORK = [
    ("Assign System's Role", "change_value"),
    ("Remove System's Role", "delete_value"),
    ("Back to Menu", "back_menu"),
]

# Create inline keyboard buttons
inline_buttons_value_work = [
    InlineKeyboardButton(text=text, callback_data=data)
    for text, data in BUTTONS_VALUE_WORK
]

# Create main keyboard
keyboard_value_work = InlineKeyboardMarkup(
    inline_keyboard=[[button] for button in inline_buttons_value_work]
)
