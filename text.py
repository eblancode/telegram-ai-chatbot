start_message = (
    "Hello! The bot is ready to work, the current model is GPT-4o mini, "
    "voice response is disabled, the dialogue context has been cleared, "
    "the message counter has been reset, the system role has been removed, the image quality is set to standard, the image size is 1024x1024"
)

system_message_text = (
    "<b>Enter the system role value, either as text or voice, for example it could be "
    "like this - </b><i>You always respond as a pirate.</i>"
)

help_message = (
        "🧰 <b>Bot Commands:</b>\n"
        "/start - Start the bot and initialize data\n"
        "/menu - Open the main menu\n"
        "/help - Show help\n\n"

        "⚙️ <b>Main Menu:</b>\n"
        " - <b>Model Selection:</b> Change the AI model (4o mini, 4o, o1 mini, o1, DALL·E 3)\n"
        " - <b>Image Settings:</b> Adjust image quality and size\n"
        " - <b>Context:</b> Show or clear message history\n"
        " - <b>Audio:</b> Enable or disable audio responses\n"
        " - <b>System Role:</b> Assign or remove the system role\n"
        " - <b>Information:</b> Show current configuration and statistics"
)
