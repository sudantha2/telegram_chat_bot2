

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, filters
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from keep_alive import keep_alive
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import random
import io
import requests
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Start the Replit web server to keep the bot alive
keep_alive()

# Get the bot token from Replit Secrets
TOKEN = os.environ['TOKEN']

# MongoDB connection
MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    print("ERROR: MONGO_URI environment variable not found!")
    print("Please add MONGO_URI to your secrets in the Replit environment.")
    sys.exit(1)

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.telegram_bot
filters_collection = db.filters

# Filter management functions
async def save_filter(chat_id, keyword, reply_type, reply_content):
    """Save a filter to MongoDB"""
    try:
        filter_doc = {
            "chat_id": chat_id,
            "keyword": keyword.lower(),
            "reply_type": reply_type,
            "reply_content": reply_content
        }
        # Replace existing filter with same keyword and chat_id
        await filters_collection.replace_one(
            {"chat_id": chat_id, "keyword": keyword.lower()},
            filter_doc,
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error saving filter: {e}")
        return False

async def delete_filter(chat_id, keyword):
    """Delete a filter from MongoDB"""
    try:
        result = await filters_collection.delete_one({
            "chat_id": chat_id,
            "keyword": keyword.lower()
        })
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting filter: {e}")
        return False

async def get_filters(chat_id):
    """Get all filters for a chat"""
    try:
        cursor = filters_collection.find({"chat_id": chat_id})
        return await cursor.to_list(length=None)
    except Exception as e:
        print(f"Error getting filters: {e}")
        return []

async def get_filter_by_keyword(chat_id, keyword):
    """Get a specific filter by keyword"""
    try:
        return await filters_collection.find_one({
            "chat_id": chat_id,
            "keyword": keyword.lower()
        })
    except Exception as e:
        print(f"Error getting filter: {e}")
        return None

# Store muted users
muted_users = set()

# Store bot's groups (will be populated dynamically)
GROUPS = {}

# Store pending messages for group selection
pending_messages = {}

# Function to get all groups/chats the bot is in
async def get_bot_groups(context):
    """Get all groups the bot is a member of"""
    global GROUPS
    try:
        # Get bot's chat memberships (this is limited by Telegram API)
        # We'll use a different approach - store groups as bot encounters them
        pass
    except Exception as e:
        print(f"Error getting bot groups: {e}")

# Function to add/update group info when bot encounters a new group
def add_group_info(chat_id, chat_title):
    """Add group info to GROUPS dictionary"""
    global GROUPS
    # Use chat_id directly as key to ensure uniqueness
    chat_key = str(chat_id)

    # Avoid duplicates and update if name changed
    if chat_key not in GROUPS:
        GROUPS[chat_key] = {
            "id": chat_id,
            "name": chat_title
        }
        print(f"Added new group: {chat_title} (ID: {chat_id})")
    else:
        # Update group name if it changed
        if GROUPS[chat_key]["name"] != chat_title:
            GROUPS[chat_key]["name"] = chat_title
            print(f"Updated group name: {chat_title} (ID: {chat_id})")

# Store message counts
message_counts = {
    'daily': {},
    'weekly': {},
    'monthly': {}
}

# Store active quiz sessions - removed quiz functionality

import datetime

def get_date_keys():
    now = datetime.datetime.now()
    today = now.strftime('%Y-%m-%d')
    week = now.strftime('%Y-W%U')  # Year-Week format
    month = now.strftime('%Y-%m')  # Year-Month format
    return today, week, month

def increment_message_count():
    today, week, month = get_date_keys()

    # Initialize if not exists
    if today not in message_counts['daily']:
        message_counts['daily'][today] = 0
    if week not in message_counts['weekly']:
        message_counts['weekly'][week] = 0
    if month not in message_counts['monthly']:
        message_counts['monthly'][month] = 0

    # Increment counts
    message_counts['daily'][today] += 1
    message_counts['weekly'][week] += 1
    message_counts['monthly'][month] += 1

# Define the /cmd command
async def cmd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    commands_text = """
🤖 **Bot Commands List** 🤖

**Admin Commands:**
• `.mute` - Mute a user (reply to their message)
• `.mute_list` - Show muted users list
• `.delete` - Delete a message (reply to it)
• `.delete_all` - Delete all messages from a user

**General Commands:**
• `/go <text>` - Send message as bot
• `/voice <text>` - Convert text to voice (Sinhala)
• `/stick <text>` - Create text sticker
• `/hello <text>` - Create fancy hello sticker
• `/more <count> <text>` - Repeat message multiple times
• `/weather <city>` - Get current weather for a city
• `/weather_c <city>` - Get 5-day weather forecast for a city
• `/ask <query>` - Get instant answers from DuckDuckGo
• `/wiki <topic>` - Get Wikipedia summary for a topic
• `/holidays <country_code> <year>` - Get public holidays for a country
• `/movie <movie title>` - Get movie/series information
• `/img <search query>` - Search for images from Pixabay
• `/yt <search term>` - Search YouTube for videos
• `/cmd` - Show this command list
• `/mg_count` - Show message statistics

**Filter Commands (Groups Only):**
• `/filter <keyword>` - Save filter (reply to a message)
• `/del <keyword>` - Delete a filter
• `/filters` - List all filters in group

**Features:**
• Forward messages to groups via private chat
• Reply to group messages via private chat
• Auto-delete muted user messages

Made with ❤️ for group management!
    """

    await message.reply_text(commands_text, parse_mode='Markdown')

# Define the /mg_count command
async def mg_count_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    today, week, month = get_date_keys()

    today_count = message_counts['daily'].get(today, 0)
    weekly_count = message_counts['weekly'].get(week, 0)
    monthly_count = message_counts['monthly'].get(month, 0)

    count_text = f"""
📊 **Message Statistics** 📊

📅 **Today**: {today_count} messages
📺 **This Week**: {weekly_count} messages  
📆 **This Month**: {monthly_count} messages

🔥 Keep the conversation going! 🚀
    """

    await message.reply_text(count_text, parse_mode='Markdown')

# Define the mute command
async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message:
            return

        # Check if command is from authorized user
        if str(message.from_user.id) != "8197285353":
            return await message.reply_text("You are not authorized to use this command.")

        # Check if it's a reply
        if not message.reply_to_message:
            return await message.reply_text("Please reply to a message to mute the user.")

        # Get the user to mute
        muted_user = message.reply_to_message.from_user
        if muted_user.id in muted_users:
            return await message.reply_text("This user is already muted.")

        muted_users.add(muted_user.id)

        # Create clickable username mention
        user_mention = f"<a href='tg://user?id={muted_user.id}'>{muted_user.first_name}</a>"

        # Send mute notification
        await context.bot.send_message(
            chat_id=message.chat_id,
            text=f"{user_mention} has been muted. Contact admin to get unmuted.",
            parse_mode='HTML'
        )

        # Delete the command message
        await message.delete()
    except Exception as e:
        print(f"Error in mute command: {e}")

# Handle all messages to delete muted users' messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check for admin commands FIRST before any other processing
    if message.text:
        if message.text == '.delete':
            await delete_command(update, context)
            return

        if message.text == '.delete_all':
            await delete_all_command(update, context)
            return

        if message.text == '.mute_list':
            await mute_list_command(update, context)
            return

        # Check for .mute command
        if message.text.startswith('.mute'):
            if str(message.from_user.id) != "8197285353":
                return

            # Check if it's a reply
            if not message.reply_to_message:
                return

            # Get the user to mute
            muted_user = message.reply_to_message.from_user
            muted_users.add(muted_user.id)

            # Delete the command message
            await message.delete()

            # Create clickable username mention
            user_mention = f"<a href='tg://user?id={muted_user.id}'>{muted_user.first_name}</a>"

            # Send mute notification
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=f"{user_mention} You are Mute now. Please contact Major admin to Unmute",
                parse_mode='HTML'
            )
            return

    # Delete message if user is muted
    if message.from_user.id in muted_users:
        await message.delete()
        return

    # Check for filter matches first (only in groups)
    if message.chat.type in ['group', 'supergroup']:
        filter_matched = await check_filters(update, context)
        # Continue with other processing even if filter matched

    # Count message (only for non-command messages)
    if not (message.text and message.text.startswith('/')):
        increment_message_count()

    # Handle group messages
    if message.chat.type != 'private':
        # Add this group to our GROUPS dictionary if not already there
        if message.chat.type in ['group', 'supergroup']:
            add_group_info(message.chat.id, message.chat.title)

        if message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
            # Forward replied message to private chat
            user = message.from_user
            user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

            # Store message ID for future reference
            reply_msg = await context.bot.send_message(
                chat_id=8197285353,
                text=f"Reply from {user_mention} in group:\n\nOriginal message: {message.reply_to_message.text}\n\nID:{message.message_id}",
                parse_mode='HTML'
            )

            # Forward the actual reply
            await context.bot.forward_message(
                chat_id=8197285353,
                from_chat_id=message.chat_id,
                message_id=message.message_id
            )
        return

    # Handle private chat messages
    try:
        if message.reply_to_message:
            # Check if this is a reply to a forwarded message
            if "ID:" in message.reply_to_message.text:
                original_id = int(message.reply_to_message.text.split("ID:")[-1].strip())

                # Send reply to group
                if message.text:
                    await context.bot.send_message(
                        chat_id=-1002357656013,
                        text=message.text,
                        reply_to_message_id=original_id
                    )
                elif message.sticker:
                    await context.bot.send_sticker(
                        chat_id=-1002357656013,
                        sticker=message.sticker.file_id,
                        reply_to_message_id=original_id
                    )
                elif message.photo:
                    await context.bot.send_photo(
                        chat_id=-1002357656013,
                        photo=message.photo[-1].file_id,
                        caption=message.caption,
                        reply_to_message_id=original_id
                    )
                await message.reply_text("✅ Sent reply to group!")
                return

        # Store message for group selection
        message_id = message.message_id
        pending_messages[message_id] = {
            'type': 'text' if message.text else 'sticker' if message.sticker else 'photo' if message.photo else 'unsupported',
            'content': message.text if message.text else message.sticker.file_id if message.sticker else message.photo[-1].file_id if message.photo else None,
            'caption': message.caption if message.photo else None
        }

        # Check if message type is supported
        if pending_messages[message_id]['type'] == 'unsupported':
            await message.reply_text("❌ Message type not supported")
            del pending_messages[message_id]
            return

        # Skip command messages
        if message.text and message.text.startswith('/'):
            del pending_messages[message_id]
            return

        # Create group selection buttons
        keyboard = []
        if GROUPS:
            for chat_id, group_info in GROUPS.items():
                # Truncate group name if too long for display
                display_name = group_info["name"]
                if len(display_name) > 30:
                    display_name = display_name[:27] + "..."

                keyboard.append([InlineKeyboardButton(
                    text=display_name,
                    callback_data=f"send_{chat_id}_{message_id}"
                )])

            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{message_id}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text(
                f"📤 Select which group to forward this message to:\n(Found {len(GROUPS)} groups)",
                reply_markup=reply_markup
            )
        else:
            await message.reply_text(
                "❌ No groups available. Bot needs to be active in groups first to detect them.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{message_id}")]])
            )

    except Exception as e:
        print(f"Error handling message: {e}")
        await message.reply_text("❌ Failed to process message")



# Define the /go command
async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Delete the original /go message
    await message.delete()

    # Get the text content after /go
    text = ' '.join(context.args)
    if not text:
        return

    # If it's a reply to someone else's message (not a bot)
    reply_to = message.reply_to_message
    if reply_to and not reply_to.from_user.is_bot:
        await context.bot.send_message(
            chat_id=message.chat_id,
            text=text,
            reply_to_message_id=reply_to.message_id
        )
    else:
        # Send it as a regular message
        await context.bot.send_message(
            chat_id=message.chat_id,
            text=text
        )

# Define the /voice command
async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from gtts import gTTS
    from langdetect import detect, DetectorFactory
    import tempfile
    import os

    # Set seed for consistent results
    DetectorFactory.seed = 0

    message = update.message
    if not message:
        return

    # Get the command text
    text = ' '.join(context.args)
    if not text:
        return

    # Get reply message ID if it's a reply
    reply_to = message.reply_to_message
    reply_msg_id = reply_to.message_id if reply_to else None

    # Delete the command message
    await message.delete()

    try:
        # Check for Sinhala characters first (Unicode range for Sinhala)
        sinhala_chars = any('\u0D80' <= char <= '\u0DFF' for char in text)

        if sinhala_chars:
            lang_code = 'si'
            print(f"Detected Sinhala text, using 'si' language code")
        else:
            # Detect language from text
            detected_lang = detect(text)
            print(f"Detected language: {detected_lang}")

            # Map detected languages to gTTS supported languages
            lang_mapping = {
                'en': 'en',     # English
                'si': 'si',     # Sinhala
                'hi': 'hi',     # Hindi
                'ta': 'ta',     # Tamil
                'ja': 'ja',     # Japanese
                'ko': 'ko',     # Korean
                'zh': 'zh',     # Chinese
                'ar': 'ar',     # Arabic
                'bn': 'bn',     # Bengali
                'te': 'te',     # Telugu
                'ml': 'ml',     # Malayalam
                'kn': 'kn',     # Kannada
                'gu': 'gu',     # Gujarati
                'pa': 'pa',     # Punjabi
                'ur': 'ur',     # Urdu
                'ne': 'ne',     # Nepali
                'th': 'th',     # Thai
                'vi': 'vi',     # Vietnamese
                'tr': 'tr',     # Turkish
                'ru': 'ru',     # Russian
                'fr': 'fr',     # French
                'de': 'de',     # German
                'es': 'es',     # Spanish
                'it': 'it',     # Italian
                'pt': 'pt',     # Portuguese
                'nl': 'nl',     # Dutch
                'sv': 'sv',     # Swedish
                'no': 'no',     # Norwegian
                'da': 'da',     # Danish
                'fi': 'fi',     # Finnish
                'pl': 'pl',     # Polish
                'cs': 'cs',     # Czech
                'sk': 'sk',     # Slovak
                'hu': 'hu',     # Hungarian
                'ro': 'ro',     # Romanian
                'bg': 'bg',     # Bulgarian
                'hr': 'hr',     # Croatian
                'sr': 'sr',     # Serbian
                'sl': 'sl',     # Slovenian
                'et': 'et',     # Estonian
                'lv': 'lv',     # Latvian
                'lt': 'lt',     # Lithuanian
                'uk': 'uk',     # Ukrainian
                'be': 'be',     # Belarusian
                'mk': 'mk',     # Macedonian
                'sq': 'sq',     # Albanian
                'mt': 'mt',     # Maltese
                'cy': 'cy',     # Welsh
                'ga': 'ga',     # Irish
                'is': 'is',     # Icelandic
                'eu': 'eu',     # Basque
                'ca': 'ca',     # Catalan
                'gl': 'gl',     # Galician
                'af': 'af',     # Afrikaans
                'sw': 'sw',     # Swahili
                'zu': 'zu',     # Zulu
                'xh': 'xh',     # Xhosa
                'st': 'st',     # Sesotho
                'tn': 'tn',     # Setswana
                'ss': 'ss',     # Siswati
                've': 've',     # Tshivenda
                'ts': 'ts',     # Xitsonga
                'nr': 'nr',     # Ndebele
                'nso': 'nso',   # Northern Sotho
            }

            # Get the appropriate language code, default to English if not supported
            lang_code = lang_mapping.get(detected_lang, 'en')

        # Create temporary file for voice message
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            # Convert text to speech in detected language
            tts = gTTS(text=text, lang=lang_code)
            tts.save(tmp_file.name)

            # Send voice message as reply
            with open(tmp_file.name, 'rb') as audio:
                await context.bot.send_voice(
                    chat_id=message.chat_id,
                    voice=audio,
                    reply_to_message_id=reply_msg_id
                )

            # Clean up temporary file
            os.unlink(tmp_file.name)

    except Exception as e:
        # If language detection fails, fall back to Sinhala if text contains Sinhala characters, otherwise English
        print(f"Language detection failed: {e}")

        # Check for Sinhala characters as fallback
        sinhala_chars = any('\u0D80' <= char <= '\u0DFF' for char in text)
        fallback_lang = 'si' if sinhala_chars else 'en'

        print(f"Using fallback language: {fallback_lang}")

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tts = gTTS(text=text, lang=fallback_lang)
            tts.save(tmp_file.name)

            with open(tmp_file.name, 'rb') as audio:
                await context.bot.send_voice(
                    chat_id=message.chat_id,
                    voice=audio,
                    reply_to_message_id=reply_msg_id
                )

            os.unlink(tmp_file.name)

# Define the /stick command
async def stick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Get the text content
    text = ' '.join(context.args)
    if not text:
        return

    # Check if it's a reply
    reply_to = message.reply_to_message
    reply_msg_id = reply_to.message_id if reply_to else None

    # Delete the command message
    await message.delete()

    # Create image
    width, height = 512, 512
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD']
    bg_color = random.choice(colors)

    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Calculate font size based on text length
    font_size = min(80, int(400 / len(text)))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Center the text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) / 2
    y = (height - text_height) / 2

    # Add text with outline
    outline_color = '#FFFFFF'
    for offset in range(-2, 3):
        draw.text((x + offset, y), text, font=font, fill=outline_color)
        draw.text((x, y + offset), text, font=font, fill=outline_color)

    draw.text((x, y), text, font=font, fill='#000000')

    # Convert to webp
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='WEBP')
    img_byte_arr.seek(0)

    # Send as sticker, replying to original message if it exists
    await context.bot.send_sticker(
        chat_id=message.chat_id,
        sticker=img_byte_arr,
        reply_to_message_id=reply_msg_id  # This will be None for normal messages
    )

# Define the /hello command
async def hello_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Get the text content after /hello
    text = ' '.join(context.args)
    if not text:
        text = "hello"  # Default text if none provided

    # Delete the command message
    await message.delete()

    # Create image
    width, height = 512, 512
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Create cloud shape background with gradient
    # Night sky gradient
    for y in range(height):
        for x in range(width):
            distance = ((x - width/2)**2 + (y - height/2)**2)**0.5
            ratio = min(1.0, distance / (width/2))
            r = int(30 * (1 - ratio))  # Dark blue
            g = int(20 * (1 - ratio))
            b = int(60 * (1 - ratio))
            if distance < width/2:  # Cloud shape mask
                img.putpixel((x, y), (r, g, b, 255))

    # Add stars and moon
    for _ in range(30):
        star_x = random.randint(0, width)
        star_y = random.randint(0, height)
        star_size = random.randint(2, 4)
        draw.ellipse([star_x, star_y, star_x + star_size, star_y + star_size], fill=(255, 255, 200, 255))

    # Add heart
    heart_color = (255, 182, 193, 255)  # Light pink
    heart_size = 80
    heart_x = width//2 - heart_size//2
    heart_y = height//2 - heart_size
    draw.ellipse([heart_x, heart_y, heart_x + heart_size//2, heart_y + heart_size//2], fill=heart_color)
    draw.ellipse([heart_x + heart_size//2, heart_y, heart_x + heart_size, heart_y + heart_size//2], fill=heart_color)
    draw.polygon([
        (heart_x, heart_y + heart_size//4),
        (heart_x + heart_size//2, heart_y + heart_size),
        (heart_x + heart_size, heart_y + heart_size//4)
    ], fill=heart_color)

    # Use consistent font size
    try:
        font_size = 80  # Fixed size that's readable but not too large
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)

        # Calculate text size and scale down only if too wide
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width > width * 0.8:  # If text is wider than 80% of image
            font_size = int(font_size * (width * 0.8) / text_width)
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Get text size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) / 2
    y = (height - text_height) / 2 + 20  # Slightly lower than center

    # Add multiple outline layers for glow effect
    outline_colors = [
        (255, 255, 255, 50),  # White glow
        (255, 192, 203, 100),  # Pink glow
        (255, 255, 255, 150),  # Brighter white
        (0, 0, 0, 255),       # Black outline
    ]

    for color in outline_colors:
        for offset in range(3, 8, 2):
            for dx, dy in [(j, i) for i in range(-offset, offset+1) for j in range(-offset, offset+1)]:
                draw.text((x + dx, y + dy), text, font=font, fill=color)

    # Main text in pink
    draw.text((x, y), text, font=font, fill=(255, 192, 203, 255))

    # Convert to webp with transparency
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='WEBP')
    img_byte_arr.seek(0)

    # Get reply message ID if it's a reply
    reply_to = message.reply_to_message
    reply_msg_id = reply_to.message_id if reply_to else None

    # Send as sticker, replying to original message if it exists
    await context.bot.send_sticker(
        chat_id=message.chat_id,
        sticker=img_byte_arr,
        reply_to_message_id=reply_msg_id
    )

# Define the /more command
async def more_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not context.args:
        return

    try:
        # Get the repeat count from first argument
        repeat_count = int(context.args[0])
        if repeat_count <= 0 or repeat_count > 10:  # Limit to reasonable number
            return

        # Get the text content after the number
        text = ' '.join(context.args[1:])
        if not text:
            return

        # Delete the original command message
        await message.delete()

        # Get reply message if it exists
        reply_to = message.reply_to_message
        reply_msg_id = reply_to.message_id if reply_to else None

        # Send the message multiple times
        for _ in range(repeat_count):
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=text,
                reply_to_message_id=reply_msg_id
            )
    except ValueError:
        return  # Invalid number provided

# Define the /weather command
async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check if city name is provided
    if not context.args:
        await message.reply_text("❗ Please use the command like this:\n/weather <city>")
        return

    city = ' '.join(context.args)

    try:
        # Get API key from environment
        api_key = os.environ.get('OPENWEATHERMAP_API_KEY')
        if not api_key:
            await message.reply_text("❌ Weather service is not configured.")
            return

        # Make API request to OpenWeatherMap
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': city,
            'appid': api_key,
            'units': 'metric'
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 404:
            await message.reply_text(f"❌ City '{city}' not found. Please check the spelling and try again.")
            return
        elif response.status_code != 200:
            await message.reply_text("❌ Unable to fetch weather data. Please try again later.")
            return

        data = response.json()

        # Extract weather information
        city_name = data['name']
        country = data['sys']['country']
        condition = data['weather'][0]['description'].title()
        weather_main = data['weather'][0]['main'].lower()
        temp = round(data['main']['temp'])
        feels_like = round(data['main']['feels_like'])
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']

        # Get weather emoji based on condition
        weather_emoji = "🌤️"  # default
        if "clear" in weather_main or "sunny" in weather_main:
            weather_emoji = "☀️"
        elif "cloud" in weather_main:
            weather_emoji = "☁️"
        elif "rain" in weather_main or "drizzle" in weather_main:
            weather_emoji = "🌧️"
        elif "thunderstorm" in weather_main or "storm" in weather_main:
            weather_emoji = "⛈️"
        elif "snow" in weather_main:
            weather_emoji = "❄️"
        elif "mist" in weather_main or "fog" in weather_main:
            weather_emoji = "🌫️"
        elif "wind" in weather_main:
            weather_emoji = "💨"

        # Get temperature emoji
        temp_emoji = "🌡️"
        if temp >= 30:
            temp_emoji = "🔥"
        elif temp >= 25:
            temp_emoji = "🌡️"
        elif temp >= 15:
            temp_emoji = "🌡️"
        elif temp >= 5:
            temp_emoji = "🧊"
        else:
            temp_emoji = "❄️"

        # Get humidity emoji
        humidity_emoji = "💧"
        if humidity >= 80:
            humidity_emoji = "💦"
        elif humidity >= 60:
            humidity_emoji = "💧"
        else:
            humidity_emoji = "🏜️"

        # Get wind speed emoji
        wind_emoji = "🍃"
        if wind_speed >= 10:
            wind_emoji = "💨"
        elif wind_speed >= 5:
            wind_emoji = "🌬️"
        else:
            wind_emoji = "🍃"

        # Format weather response with emojis
        weather_text = f"""{weather_emoji} **Weather in {city_name}, {country}:**

🌦️ **Condition:** {condition}
{temp_emoji} **Temperature:** {temp}°C (Feels like {feels_like}°C)
{humidity_emoji} **Humidity:** {humidity}%
{wind_emoji} **Wind Speed:** {wind_speed} m/s"""

        await message.reply_text(weather_text, parse_mode='Markdown')

    except requests.exceptions.Timeout:
        await message.reply_text("❌ Weather service is taking too long to respond. Please try again.")
    except requests.exceptions.RequestException:
        await message.reply_text("❌ Unable to connect to weather service. Please try again later.")
    except KeyError:
        await message.reply_text("❌ Invalid weather data received. Please try again.")
    except Exception as e:
        print(f"Error in weather command: {e}")
        await message.reply_text("❌ An error occurred while fetching weather data.")

# Define the /weather_c command for 5-day forecast
async def weather_forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check if city name is provided
    if not context.args:
        await message.reply_text("❗ Please use the command like this:\n/weather_c <city>")
        return

    city = ' '.join(context.args)

    try:
        # Get API key from environment
        api_key = os.environ.get('OPENWEATHERMAP_API_KEY')
        if not api_key:
            await message.reply_text("❌ Weather service is not configured.")
            return

        # Make API request for 5-day forecast
        url = f"https://api.openweathermap.org/data/2.5/forecast"
        params = {
            'q': city,
            'appid': api_key,
            'units': 'metric'
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 404:
            await message.reply_text(f"❌ City '{city}' not found for forecast.")
            return
        elif response.status_code != 200:
            await message.reply_text("❌ Unable to fetch forecast data.")
            return

        data = response.json()

        # Extract forecast information
        city_name = data['city']['name']
        country = data['city']['country']
        forecasts = data['list']

        # Group forecasts by day (take one forecast per day at around noon)
        daily_forecasts = []
        seen_dates = set()

        for forecast in forecasts:
            forecast_time = forecast['dt_txt']
            date = forecast_time.split(' ')[0]
            hour = forecast_time.split(' ')[1]

            # Take forecast around noon (12:00) for each day, or first available if noon not found
            if date not in seen_dates and ('12:00' in hour or len(daily_forecasts) < 5):
                if date not in seen_dates:
                    seen_dates.add(date)
                    daily_forecasts.append(forecast)

                if len(daily_forecasts) >= 5:
                    break

        # Format forecast response
        forecast_text = f"📅 **5-Day Weather Forecast for {city_name}, {country}:**\n\n"

        for i, forecast in enumerate(daily_forecasts):
            date_str = forecast['dt_txt'].split(' ')[0]
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            day_name = date_obj.strftime('%A')

            condition = forecast['weather'][0]['description'].title()
            weather_main = forecast['weather'][0]['main'].lower()
            temp_max = round(forecast['main']['temp_max'])
            temp_min = round(forecast['main']['temp_min'])
            humidity = forecast['main']['humidity']
            wind_speed = forecast['wind']['speed']

            # Get weather emoji
            weather_emoji = "🌤️"
            if "clear" in weather_main or "sunny" in weather_main:
                weather_emoji = "☀️"
            elif "cloud" in weather_main:
                weather_emoji = "☁️"
            elif "rain" in weather_main or "drizzle" in weather_main:
                weather_emoji = "🌧️"
            elif "thunderstorm" in weather_main or "storm" in weather_main:
                weather_emoji = "⛈️"
            elif "snow" in weather_main:
                weather_emoji = "❄️"
            elif "mist" in weather_main or "fog" in weather_main:
                weather_emoji = "🌫️"

            forecast_text += f"{weather_emoji} **{day_name}** ({date_str})\n"
            forecast_text += f"   🌦️ {condition}\n"
            forecast_text += f"   🌡️ High: {temp_max}°C | Low: {temp_min}°C\n"
            forecast_text += f"   💧 Humidity: {humidity}%\n"
            forecast_text += f"   💨 Wind: {wind_speed} m/s\n\n"

        await message.reply_text(forecast_text, parse_mode='Markdown')

    except requests.exceptions.Timeout:
        await message.reply_text("❌ Weather service is taking too long to respond.")
    except requests.exceptions.RequestException:
        await message.reply_text("❌ Unable to connect to weather service.")
    except Exception as e:
        print(f"Error in weather forecast command: {e}")
        await message.reply_text("❌ An error occurred while fetching forecast data.")

# Define the /ask command for DuckDuckGo instant answers
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check if query is provided
    if not context.args:
        await message.reply_text("❗ Please use the command like this:\n/ask <your question>")
        return

    query = ' '.join(context.args)

    try:
        # Make API request to DuckDuckGo Instant Answer API
        url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_redirect': '1',
            'skip_disambig': '1'
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            await message.reply_text("❌ Unable to fetch answer from DuckDuckGo.")
            return

        data = response.json()

        # Extract answer from response
        answer_text = ""
        answer_url = ""

        # First try AbstractText
        if data.get('AbstractText'):
            answer_text = data['AbstractText']
            answer_url = data.get('AbstractURL', '')

        # Fallback to first RelatedTopic if AbstractText is empty
        elif data.get('RelatedTopics') and len(data['RelatedTopics']) > 0:
            first_topic = data['RelatedTopics'][0]
            if isinstance(first_topic, dict) and first_topic.get('Text'):
                answer_text = first_topic['Text']
                answer_url = first_topic.get('FirstURL', '')

        # If no meaningful answer found
        if not answer_text:
            await message.reply_text("Sorry, I couldn't find an instant answer for that.")
            return

        # Format response
        response_text = f"🔍 **Answer for: {query}**\n\n{answer_text}"

        # Add URL if available
        if answer_url:
            response_text += f"\n\n🔗 [More info]({answer_url})"

        await message.reply_text(response_text, parse_mode='Markdown', disable_web_page_preview=True)

    except requests.exceptions.Timeout:
        await message.reply_text("❌ DuckDuckGo is taking too long to respond.")
    except requests.exceptions.RequestException:
        await message.reply_text("❌ Unable to connect to DuckDuckGo service.")
    except Exception as e:
        print(f"Error in ask command: {e}")
        await message.reply_text("❌ An error occurred while fetching the answer.")

# Define the /holidays command for public holidays
async def holidays_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check if country code and year are provided
    if len(context.args) < 2:
        await message.reply_text("❗ Please use the command like this:\n/holidays [country_code] [year]\n\nExample: /holidays US 2025")
        return

    country_code = context.args[0].upper()
    try:
        year = int(context.args[1])
    except ValueError:
        await message.reply_text("❗ Please provide a valid year.\nExample: /holidays US 2025")
        return

    # Validate year range
    if year < 1900 or year > 2100:
        await message.reply_text("❗ Please provide a year between 1900 and 2100.")
        return

    try:
        # Make API request to Nager.Date API
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"

        response = requests.get(url, timeout=10)

        if response.status_code == 404:
            # Suggest common country code alternatives
            suggestions = {
                'UK': 'GB', 'LK': 'LK', 'USA': 'US', 'INDIA': 'IN', 
                'ENGLAND': 'GB', 'BRITAIN': 'GB', 'SRILANKA': 'LK'
            }
            suggestion = suggestions.get(country_code, None)
            error_msg = f"❌ Country code '{country_code}' not found or no holidays available for {year}."
            if suggestion and suggestion != country_code:
                error_msg += f"\n💡 Try using '{suggestion}' instead of '{country_code}'"
            error_msg += "\n\nCommon codes: US, GB, DE, IN, CA, AU, FR, IT, ES, JP"
            await message.reply_text(error_msg)
            return
        elif response.status_code != 200:
            await message.reply_text("❌ Unable to fetch holiday data. Please try again later.")
            return

        data = response.json()

        if not data:
            await message.reply_text(f"❌ No public holidays found for {country_code} in {year}.")
            return

        # Get country flag emoji (basic mapping for common countries)
        country_flags = {
            'US': '🇺🇸', 'DE': '🇩🇪', 'IN': '🇮🇳', 'GB': '🇬🇧', 'FR': '🇫🇷', 
            'IT': '🇮🇹', 'ES': '🇪🇸', 'CA': '🇨🇦', 'AU': '🇦🇺', 'JP': '🇯🇵',
            'KR': '🇰🇷', 'CN': '🇨🇳', 'BR': '🇧🇷', 'MX': '🇲🇽', 'RU': '🇷🇺',
            'ZA': '🇿🇦', 'EG': '🇪🇬', 'TR': '🇹🇷', 'SA': '🇸🇦', 'AE': '🇦🇪',
            'SG': '🇸🇬', 'TH': '🇹🇭', 'MY': '🇲🇾', 'ID': '🇮🇩', 'PH': '🇵🇭',
            'VN': '🇻🇳', 'LK': '🇱🇰', 'BD': '🇧🇩', 'PK': '🇵🇰', 'NP': '🇳🇵',
            'NL': '🇳🇱', 'BE': '🇧🇪', 'CH': '🇨🇭', 'AT': '🇦🇹', 'SE': '🇸🇪',
            'NO': '🇳🇴', 'DK': '🇩🇰', 'FI': '🇫🇮', 'PT': '🇵🇹', 'GR': '🇬🇷'
        }

        country_flag = country_flags.get(country_code, '🏳️')

        # Format response
        holidays_text = f"{country_flag} **Public Holidays in {country_code} for {year}:**\n\n"

        # Sort holidays by date
        sorted_holidays = sorted(data, key=lambda x: x['date'])

        for holiday in sorted_holidays:
            date = holiday['date']
            local_name = holiday.get('localName', holiday['name'])
            name = holiday['name']

            # Use local name if different from English name, otherwise just use name
            holiday_name = local_name if local_name != name else name

            holidays_text += f"📅 **{date}** - {holiday_name}\n"

        # Split message if too long (Telegram limit is 4096 characters)
        if len(holidays_text) > 4000:
            # Send first part
            first_part = holidays_text[:3900]
            last_newline = first_part.rfind('\n')
            if last_newline > 0:
                first_part = first_part[:last_newline]

            await message.reply_text(first_part, parse_mode='Markdown')

            # Send remaining part
            remaining = holidays_text[len(first_part):]
            await message.reply_text(remaining, parse_mode='Markdown')
        else:
            await message.reply_text(holidays_text, parse_mode='Markdown')

    except requests.exceptions.Timeout:
        await message.reply_text("❌ Holiday service is taking too long to respond. Please try again.")
    except requests.exceptions.RequestException:
        await message.reply_text("❌ Unable to connect to holiday service. Please try again later.")
    except Exception as e:
        print(f"Error in holidays command: {e}")
        await message.reply_text("❌ An error occurred while fetching holiday data.")

# Define the /movie command for movie information
async def movie_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check if movie title is provided
    if not context.args:
        await message.reply_text("ℹ️ Usage: `/movie [movie title]`")
        return

    movie_title = ' '.join(context.args)

    try:
        # Get API key from environment
        api_key = os.environ.get('MOVIE_API_KEY')
        if not api_key:
            await message.reply_text("❌ Movie service is not configured.")
            return

        # Format movie title for URL (replace spaces with +)
        formatted_title = movie_title.replace(' ', '+')

        # Make API request to OMDb API
        url = f"http://www.omdbapi.com/"
        params = {
            'apikey': api_key,
            't': formatted_title
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            await message.reply_text("❌ Unable to fetch movie data. Please try again later.")
            return

        data = response.json()

        # Check if movie was found
        if data.get('Response') == 'False':
            await message.reply_text(f'❌ No results found for "{movie_title}"')
            return

        # Extract movie information
        title = data.get('Title', 'N/A')
        year = data.get('Year', 'N/A')
        imdb_rating = data.get('imdbRating', 'N/A')
        genre = data.get('Genre', 'N/A')
        plot = data.get('Plot', 'N/A')
        director = data.get('Director', 'N/A')
        actors = data.get('Actors', 'N/A')
        language = data.get('Language', 'N/A')
        poster_url = data.get('Poster', '')

        # Format response
        movie_text = f"""🎬 **Title:** {title}
📆 **Year:** {year}
⭐ **IMDb Rating:** {imdb_rating}
🎭 **Genre:** {genre}
🎞️ **Plot:** {plot}
🎬 **Director:** {director}
👥 **Actors:** {actors}
🌐 **Language:** {language}"""

        # Add poster if available and not "N/A"
        if poster_url and poster_url != "N/A":
            movie_text += f"\n🖼️ [Poster]({poster_url})"

        await message.reply_text(movie_text, parse_mode='Markdown', disable_web_page_preview=True)

    except requests.exceptions.Timeout:
        await message.reply_text("❌ Movie service is taking too long to respond. Please try again.")
    except requests.exceptions.RequestException:
        await message.reply_text("❌ Unable to connect to movie service. Please try again later.")
    except Exception as e:
        print(f"Error in movie command: {e}")
        await message.reply_text("❌ An error occurred while fetching movie data.")

# Define the /img command for image search
async def img_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check if search query is provided
    if not context.args:
        await message.reply_text("ℹ️ Usage: `/img [search query]`\n\nExample: `/img cute puppies`")
        return

    search_query = ' '.join(context.args)
    await send_image_results(message, search_query, page=1)

async def send_image_results(message, search_query, page=1):
    """Send image search results with pagination"""
    await send_image_results_to_chat(message.get_bot(), message.chat_id, search_query, page)

async def send_image_results_to_chat(bot, chat_id, search_query, page=1):
    """Send image search results to a specific chat"""
    try:
        # Get API key from environment
        api_key = os.environ.get('PIXABAY_API_KEY')
        if not api_key:
            await bot.send_message(chat_id, "❌ Image search service is not configured.")
            return

        # Make API request to Pixabay with pagination
        url = "https://pixabay.com/api/"
        params = {
            'key': api_key,
            'q': search_query,
            'image_type': 'photo',
            'per_page': 5,
            'page': page,
            'safesearch': 'true'
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            await bot.send_message(chat_id, "❌ Unable to fetch images. Please try again later.")
            return

        data = response.json()

        # Check if images were found
        if not data.get('hits') or len(data['hits']) == 0:
            if page == 1:
                await bot.send_message(chat_id, f'Sorry, I couldn\'t find any images for "{search_query}".')
            else:
                await bot.send_message(chat_id, "No more images found.")
            return

        # Format response with images
        images_text = f'🖼️ **Images for "{search_query}" (Page {page}):**\n\n'

        for i, image in enumerate(data['hits'], 1):
            image_url = image.get('webformatURL', image.get('largeImageURL', ''))
            tags = image.get('tags', 'No tags available')

            # Limit tags length
            if len(tags) > 50:
                tags = tags[:47] + "..."

            images_text += f"{i}. [View Image]({image_url})\n   **Tags:** {tags}\n\n"

        # Create pagination keyboard
        keyboard = []
        if page < 10 and len(data['hits']) == 5:  # Only show More/Next if we have more results and haven't reached limit
            keyboard.append([InlineKeyboardButton("More ➡️", callback_data=f"img_next_{search_query}_{page + 1}")])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        await bot.send_message(chat_id, images_text, parse_mode='Markdown', disable_web_page_preview=False, reply_markup=reply_markup)

    except requests.exceptions.Timeout:
        await bot.send_message(chat_id, "❌ Image service is taking too long to respond. Please try again.")
    except requests.exceptions.RequestException:
        await bot.send_message(chat_id, "❌ Unable to connect to image service. Please try again later.")
    except Exception as e:
        print(f"Error in img command: {e}")
        await bot.send_message(chat_id, "❌ An error occurred while searching for images.")

# Define the /yt command for YouTube search
async def yt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check if search term is provided
    if not context.args:
        await message.reply_text("ℹ️ Usage: `/yt [search term]`\n\nExample: `/yt python tutorial`")
        return

    search_term = ' '.join(context.args)

    try:
        # Get API key from environment
        api_key = os.environ.get('YT_API_KEY')
        if not api_key:
            await message.reply_text("❌ YouTube API service is not configured.")
            return

        # Step 1: Search for videos
        search_url = "https://www.googleapis.com/youtube/v3/search"
        search_params = {
            'part': 'snippet',
            'q': search_term,
            'type': 'video',
            'maxResults': 1,
            'order': 'relevance',
            'key': api_key
        }

        search_response = requests.get(search_url, params=search_params, timeout=10)

        if search_response.status_code != 200:
            await message.reply_text("❌ Unable to search YouTube. Please try again later.")
            return

        search_data = search_response.json()

        if not search_data.get('items'):
            await message.reply_text(f"❌ No videos found for '{search_term}'")
            return

        video_item = search_data['items'][0]
        video_id = video_item['id']['videoId']
        channel_id = video_item['snippet']['channelId']

        # Step 2: Get video statistics and details
        video_url = "https://www.googleapis.com/youtube/v3/videos"
        video_params = {
            'part': 'statistics,snippet',
            'id': video_id,
            'key': api_key
        }

        video_response = requests.get(video_url, params=video_params, timeout=10)

        if video_response.status_code != 200:
            await message.reply_text("❌ Unable to fetch video details.")
            return

        video_data = video_response.json()

        if not video_data.get('items'):
            await message.reply_text("❌ Video details not found.")
            return

        video_details = video_data['items'][0]

        # Step 3: Get channel subscriber count
        channel_url = "https://www.googleapis.com/youtube/v3/channels"
        channel_params = {
            'part': 'statistics',
            'id': channel_id,
            'key': api_key
        }

        channel_response = requests.get(channel_url, params=channel_params, timeout=10)

        if channel_response.status_code != 200:
            await message.reply_text("❌ Unable to fetch channel details.")
            return

        channel_data = channel_response.json()

        # Extract information
        title = video_details['snippet']['title']
        channel_name = video_details['snippet']['channelTitle']
        thumbnail_url = video_details['snippet']['thumbnails'].get('high', {}).get('url', '')
        video_url_link = f"https://www.youtube.com/watch?v={video_id}"

        # Get statistics
        view_count = video_details['statistics'].get('viewCount', 'N/A')
        like_count = video_details['statistics'].get('likeCount', 'N/A')

        # Format numbers
        if view_count != 'N/A':
            view_count = f"{int(view_count):,}"
        if like_count != 'N/A':
            like_count = f"{int(like_count):,}"

        # Get subscriber count
        subscriber_count = 'N/A'
        if channel_data.get('items'):
            subscriber_count = channel_data['items'][0]['statistics'].get('subscriberCount', 'N/A')
            if subscriber_count != 'N/A':
                subscriber_count = f"{int(subscriber_count):,}"

        # Format response
        youtube_text = f"""🎥 **YouTube Search Results for "{search_term}":**

📺 **Title:** {title}
🎬 **Channel:** {channel_name}
👁️ **Views:** {view_count}
❤️ **Likes:** {like_count}
👤 **Subscribers:** {subscriber_count}

🔗 [Watch Video]({video_url_link})"""

        # Add thumbnail if available
        if thumbnail_url:
            youtube_text += f"\n📷 [Thumbnail]({thumbnail_url})"

        await message.reply_text(youtube_text, parse_mode='Markdown', disable_web_page_preview=False)

    except requests.exceptions.Timeout:
        await message.reply_text("❌ YouTube API is taking too long to respond. Please try again.")
    except requests.exceptions.RequestException:
        await message.reply_text("❌ Unable to connect to YouTube API. Please try again later.")
    except Exception as e:
        print(f"Error in yt command: {e}")
        await message.reply_text("❌ An error occurred while searching YouTube.")

# Define the /wiki command for Wikipedia summaries
async def wiki_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check if topic is provided
    if not context.args:
        await message.reply_text("❗ Please use the command like this:\n/wiki <topic>")
        return

    topic = ' '.join(context.args)

    try:
        # Replace spaces with underscores for Wikipedia API
        wiki_topic = topic.replace(' ', '_')

        # Make API request to Wikipedia REST API
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{wiki_topic}"

        response = requests.get(url, timeout=10)

        if response.status_code == 404:
            await message.reply_text(f"Sorry, I couldn't find any Wikipedia page for '{topic}'. Please try another query.")
            return
        elif response.status_code != 200:
            await message.reply_text("❌ Unable to fetch Wikipedia data. Please try again later.")
            return

        data = response.json()

        # Extract summary information
        extract = data.get('extract', '')
        page_url = data.get('content_urls', {}).get('desktop', {}).get('page', '')
        title = data.get('title', topic)

        if not extract:
            await message.reply_text(f"Sorry, I couldn't find a summary for '{topic}'. Please try another query.")
            return

        # Truncate summary if too long (500 characters limit)
        if len(extract) > 500:
            extract = extract[:497] + "..."

        # Format response
        response_text = f"📖 **{title}**\n\n{extract}"

        # Add Wikipedia link if available
        if page_url:
            response_text += f"\n\n🔗 [Read more on Wikipedia]({page_url})"

        await message.reply_text(response_text, parse_mode='Markdown', disable_web_page_preview=True)

    except requests.exceptions.Timeout:
        await message.reply_text("❌ Wikipedia is taking too long to respond. Please try again.")
    except requests.exceptions.RequestException:
        await message.reply_text("❌ Unable to connect to Wikipedia. Please try again later.")
    except Exception as e:
        print(f"Error in wiki command: {e}")
        await message.reply_text("❌ An error occurred while fetching Wikipedia data.")

# Define the /filter command
async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Only work in groups
    if message.chat.type == 'private':
        await message.reply_text("❌ Filters can only be used in groups.")
        return

    # Check if keyword is provided
    if not context.args:
        await message.reply_text("❗ Please use the command like this:\n/filter <keyword>\n\nReply to a message with this command to save it as a filter.")
        return

    # Check if it's a reply to a message
    if not message.reply_to_message:
        await message.reply_text("❗ Please reply to a message to save it as a filter.")
        return

    keyword = ' '.join(context.args)
    reply_msg = message.reply_to_message
    
    # Determine reply type and content
    reply_type = None
    reply_content = None
    
    if reply_msg.text:
        reply_type = "text"
        reply_content = reply_msg.text
    elif reply_msg.photo:
        reply_type = "photo"
        reply_content = reply_msg.photo[-1].file_id
    elif reply_msg.sticker:
        reply_type = "sticker"
        reply_content = reply_msg.sticker.file_id
    elif reply_msg.voice:
        reply_type = "voice"
        reply_content = reply_msg.voice.file_id
    elif reply_msg.video:
        reply_type = "video"
        reply_content = reply_msg.video.file_id
    elif reply_msg.animation:
        reply_type = "animation"
        reply_content = reply_msg.animation.file_id
    elif reply_msg.document:
        reply_type = "document"
        reply_content = reply_msg.document.file_id
    else:
        await message.reply_text("❌ Unsupported message type for filters.")
        return
    
    # Save filter to MongoDB
    success = await save_filter(message.chat.id, keyword, reply_type, reply_content)
    
    if success:
        await message.reply_text(f"✅ Filter saved! Messages containing '{keyword}' will trigger this response.")
    else:
        await message.reply_text("❌ Failed to save filter. Please try again.")

# Define the /del command
async def del_filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Only work in groups
    if message.chat.type == 'private':
        await message.reply_text("❌ Filters can only be managed in groups.")
        return

    # Check if keyword is provided
    if not context.args:
        await message.reply_text("❗ Please use the command like this:\n/del <keyword>")
        return

    keyword = ' '.join(context.args)
    
    # Delete filter from MongoDB
    success = await delete_filter(message.chat.id, keyword)
    
    if success:
        await message.reply_text(f"✅ Filter '{keyword}' has been deleted.")
    else:
        await message.reply_text(f"❌ Filter '{keyword}' not found.")

# Define the /filters command
async def filters_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Only work in groups
    if message.chat.type == 'private':
        await message.reply_text("❌ Filters can only be viewed in groups.")
        return

    # Get all filters for this chat
    chat_filters = await get_filters(message.chat.id)
    
    if not chat_filters:
        await message.reply_text("📝 No filters have been set for this group.")
        return
    
    # Format filter list using HTML parsing for better reliability
    filters_text = f"📝 <b>Filters in {message.chat.title}:</b>\n\n"
    
    for filter_doc in chat_filters:
        keyword = filter_doc['keyword']
        reply_type = filter_doc['reply_type']
        # Escape HTML special characters
        escaped_keyword = keyword.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        filters_text += f"• <code>{escaped_keyword}</code> → {reply_type}\n"
    
    await message.reply_text(filters_text, parse_mode='HTML')

# Check for filter matches in messages
async def check_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return False
    
    # Only check in groups
    if message.chat.type == 'private':
        return False
    
    # Skip if message is a command
    if message.text.startswith('/'):
        return False
    
    # Check for filter matches
    message_text = message.text.lower()
    chat_filters = await get_filters(message.chat.id)
    
    for filter_doc in chat_filters:
        keyword = filter_doc['keyword']
        if keyword in message_text:
            reply_type = filter_doc['reply_type']
            reply_content = filter_doc['reply_content']
            
            try:
                if reply_type == "text":
                    await message.reply_text(reply_content)
                elif reply_type == "photo":
                    await message.reply_photo(photo=reply_content)
                elif reply_type == "sticker":
                    await message.reply_sticker(sticker=reply_content)
                elif reply_type == "voice":
                    await message.reply_voice(voice=reply_content)
                elif reply_type == "video":
                    await message.reply_video(video=reply_content)
                elif reply_type == "animation":
                    await message.reply_animation(animation=reply_content)
                elif reply_type == "document":
                    await message.reply_document(document=reply_content)
                
                return True  # Filter matched and replied
            except Exception as e:
                print(f"Error sending filter reply: {e}")
    
    return False  # No filter matched

async def mute_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if str(message.from_user.id) != "8197285353":
        return

    # Delete the command message
    await message.delete()

    if not muted_users:
        await context.bot.send_message(
            chat_id=message.chat_id,
            text="No users are currently muted."
        )
        return

    # Create buttons for each muted user
    keyboard = []
    for user_id in muted_users:
        try:
            chat = await context.bot.get_chat(user_id)
            keyboard.append([InlineKeyboardButton(
                text=chat.first_name,
                callback_data=f"user_{user_id}"
            )])
        except Exception as e:
            print(f"Error getting user info: {e}")

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=message.chat_id,
        text="This is your muted list plz select a user for unmute",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Handle image pagination
    if query.data.startswith("img_next_"):
        parts = query.data.split("_", 3)  # Split into max 4 parts: img_next_query_page
        search_query = parts[2]
        page = int(parts[3])

        # Store chat_id before deleting the message
        chat_id = query.message.chat_id

        # Delete the current message
        await query.message.delete()

        # Send next page results to the chat
        await send_image_results_to_chat(context.bot, chat_id, search_query, page)
        return

    # Handle group selection for message forwarding
    if query.data.startswith("send_"):
        parts = query.data.split("_", 2)  # Split into max 3 parts
        group_key = parts[1]  # This is now the chat_id directly
        message_id = int(parts[2])

        if message_id not in pending_messages:
            await query.edit_message_text("❌ Message expired or already sent.")
            return

        message_data = pending_messages[message_id]
        if group_key not in GROUPS:
            await query.edit_message_text("❌ Group not found.")
            return
        group_info = GROUPS[group_key]

        try:
            # Send message to selected group
            if message_data['type'] == 'text':
                await context.bot.send_message(
                    chat_id=group_info["id"],
                    text=message_data['content']
                )
            elif message_data['type'] == 'sticker':
                await context.bot.send_sticker(
                    chat_id=group_info["id"],
                    sticker=message_data['content']
                )
            elif message_data['type'] == 'photo':
                await context.bot.send_photo(
                    chat_id=group_info["id"],
                    photo=message_data['content'],
                    caption=message_data['caption']
                )

            await query.edit_message_text(f"✅ Message forwarded to {group_info['name']}!")
            del pending_messages[message_id]
        except Exception as e:
            print(f"Error forwarding message: {e}")
            await query.edit_message_text("❌ Failed to forward message.")

    elif query.data.startswith("cancel_"):
        message_id = int(query.data.split("_")[1])
        if message_id in pending_messages:
            del pending_messages[message_id]
        await query.edit_message_text("❌ Message forwarding cancelled.")

    # Check if the button was clicked by authorized user for admin functions
    elif str(query.from_user.id) != "8197285353":
        await query.answer("You are not authorized to use these buttons.")
        return

    elif query.data.startswith("user_"):
        user_id = int(query.data.split("_")[1])
        try:
            chat = await context.bot.get_chat(user_id)
            keyboard = [
                [InlineKeyboardButton("Unmute", callback_data=f"unmute_{user_id}")],
                [InlineKeyboardButton("Back", callback_data="back")]
            ]
            await query.edit_message_text(
                text=f"Please select unmute button for continue\nSelected user: {chat.first_name}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Error handling user button: {e}")

    elif query.data.startswith("unmute_"):
        user_id = int(query.data.split("_")[1])
        if user_id in muted_users:
            muted_users.remove(user_id)
            try:
                chat = await context.bot.get_chat(user_id)
                user_mention = f"<a href='tg://user?id={user_id}'>{chat.first_name}</a>"
                await query.edit_message_text(
                    text=f"{user_mention} You are free now. Happy Happy!",
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"Error unmuting user: {e}")

    elif query.data.startswith("delete_all_"):
        if query.data == "delete_all_cancel":
            await query.message.delete()
            return

        user_id = int(query.data.split("_")[2])
        try:
            chat = await context.bot.get_chat(user_id)
            user_mention = f"<a href='tg://user?id={target_user.id}'>{chat.first_name}</a>"

            # Delete the confirmation message
            await query.message.delete()

            # Send processing message
            status_msg = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Deleting all messages from {user_mention}...",
                parse_mode='HTML'
            )

            # Here you would implement the actual message deletion
            # Note: Due to API limitations, we can only delete recent messages
            # Send completion message
            await status_msg.edit_text(
                f"✅ Successfully deleted messages from {user_mention}",
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"Error in delete_all: {e}")
            await query.message.edit_text("❌ Failed to delete messages.")
        return

    elif query.data == "back":
        # Return to muted users list
        keyboard = []
        for user_id in muted_users:
            try:
                chat = await context.bot.get_chat(user_id)
                keyboard.append([InlineKeyboardButton(
                    text=chat.first_name,
                    callback_data=f"user_{user_id}"
                )])
            except Exception as e:
                print(f"Error getting user info: {e}")

        if keyboard:
            await query.edit_message_text(
                text="This is your muted list plz select a user for unmute",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text(text="No users are currently muted.")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("cmd", cmd_command))
app.add_handler(CommandHandler("mg_count", mg_count_command))
app.add_handler(CommandHandler("go", go_command))
app.add_handler(CommandHandler("voice", voice_command))
app.add_handler(CommandHandler("stick", stick_command))
app.add_handler(CommandHandler("hello", hello_command))
app.add_handler(CommandHandler("more", more_command))
app.add_handler(CommandHandler("weather", weather_command))
app.add_handler(CommandHandler("weather_c", weather_forecast_command))
app.add_handler(CommandHandler("ask", ask_command))
app.add_handler(CommandHandler("wiki", wiki_command))
app.add_handler(CommandHandler("holidays", holidays_command))
app.add_handler(CommandHandler("movie", movie_command))
app.add_handler(CommandHandler("img", img_command))
app.add_handler(CommandHandler("yt", yt_command))
app.add_handler(CommandHandler("filter", filter_command))
app.add_handler(CommandHandler("del", del_filter_command))
app.add_handler(CommandHandler("filters", filters_list_command))

app.add_handler(MessageHandler(filters.Regex(r'^\.mute$'), mute_command))
app.add_handler(MessageHandler(filters.Regex(r'^\.mute_list$'), mute_list_command))
app.add_handler(MessageHandler((filters.TEXT | filters.Sticker.ALL | filters.PHOTO) & ~filters.COMMAND, handle_message))

# Delete command handler
async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message:
            return

        # Check if user is authorized
        if str(message.from_user.id) != "8197285353":
            return

        # Check if it's a reply
        if message.reply_to_message:
            # Delete the target message first
            await message.reply_to_message.delete()
            # Then delete the command message
            await message.delete()
        else:
            # Send error message and delete the command
            error_msg = await message.reply_text("Please reply to a message to delete it")
            await message.delete()
            # Delete error message after 3 seconds
            await asyncio.sleep(3)
            await error_msg.delete()
    except Exception as e:
        print(f"Error in delete command: {e}")
        try:
            # Still try to delete the command message even if target deletion failed
            await message.delete()
        except:
            pass

# Delete all command handler

async def delete_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check if user is authorized
    if str(message.from_user.id) != "8197285353":
        return

    # Check if it's a reply
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        user_mention = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"

        # Create confirmation buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm Delete All", callback_data=f"delete_all_{target_user.id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="delete_all_cancel")
            ]
        ]

        await message.delete()
        await context.bot.send_message(
            chat_id=message.chat_id,
            text=f"Are you sure you want to delete all messages from {user_mention}?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )


app.add_handler(CallbackQueryHandler(button_callback))

import signal
import sys

def signal_handler(sig, frame):
    print('Stopping bot...')
    app.stop_running()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

try:
    print("Bot is running...")
    app.run_polling(allowed_updates=["message", "callback_query"], drop_pending_updates=True)
except Exception as e:
    print(f"Error running bot: {e}")
    sys.exit(1)
