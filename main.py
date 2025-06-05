from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, filters, PollAnswerHandler
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from keep_alive import keep_alive
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import random
import io
import requests
import asyncio
import psutil
import gc
import time
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

# MongoDB Quiz connection
MONGO_QUIZ_URI = os.environ.get('MONGO_QUIZ_URI')
if MONGO_QUIZ_URI:
    quiz_mongo_client = AsyncIOMotorClient(MONGO_QUIZ_URI)
    quiz_db = quiz_mongo_client.quiz_bot
    quiz_collection = quiz_db.questions
else:
    quiz_mongo_client = None
    quiz_db = None
    quiz_collection = None

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

# Store active quiz sessions
active_quizzes = {}
quiz_user_states = {}
quiz_settings = {}

import datetime
import time

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

# Define the /status command
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    try:
        # Get CPU information
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # Get memory information
        memory = psutil.virtual_memory()
        memory_total_mb = round(memory.total / (1024 * 1024))
        memory_used_mb = round(memory.used / (1024 * 1024))
        memory_available_mb = round(memory.available / (1024 * 1024))
        memory_percent = memory.percent

        # Get disk information
        disk = psutil.disk_usage('/')
        disk_total_gb = round(disk.total / (1024 * 1024 * 1024), 1)
        disk_used_gb = round(disk.used / (1024 * 1024 * 1024), 1)
        disk_free_gb = round(disk.free / (1024 * 1024 * 1024), 1)
        disk_percent = round((disk.used / disk.total) * 100, 1)

        # Get system uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_hours = round(uptime_seconds / 3600, 1)

        # Format the status message
        status_text = f"""
🖥️ **System Status**

**CPU:**
• Usage: {cpu_percent}%
• Cores: {cpu_count}

**Memory:**
• Used: {memory_used_mb} MB ({memory_percent}%)
• Available: {memory_available_mb} MB
• Total: {memory_total_mb} MB

**Storage:**
• Used: {disk_used_gb} GB ({disk_percent}%)
• Free: {disk_free_gb} GB
• Total: {disk_total_gb} GB

**System:**
• Uptime: {uptime_hours} hours

🟢 Bot is running smoothly!
        """

        await message.reply_text(status_text.strip(), parse_mode='Markdown')

    except Exception as e:
        error_text = f"❌ **Error getting system status:**\n\n`{str(e)}`"
        await message.reply_text(error_text, parse_mode='Markdown')
        print(f"Error in status command: {e}")

# Define the /cmd command
async def cmd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    commands_text = """
╔═══════════════════════════════╗
║         🌟 **WELCOME!** 🌟         ║
╚═══════════════════════════════╝

🌟 **Hello and Welcome!** 🌟
I'm so happy you're here! 💖 This little bot was lovingly created with my small knowledge, and a big thanks to the amazing **Celestial Family** ✨ for the inspiration.

🚀 **Built using Replit & Render** to make your experience smooth and fun!

🙏 Please use this bot kindly and responsibly — let's keep things friendly and bright! 🌈
Enjoy and have a wonderful day! 🌸😊

╔═══════════════════════════════╗
║       🤖 **BOT COMMANDS**       ║
╚═══════════════════════════════╝

🛡️ **Admin Commands:**
┣━ `.mute` - Mute a user (reply to their message)
┣━ `.mute_list` - Show muted users list  
┗━ `.delete` - Delete a message (reply to it)

💬 **General Commands:**
┣━ `/go <text>` - Send message as bot
┣━ `/voice <text>` - Convert text to voice (Sinhala)
┣━ `/stick <text>` - Create text sticker
┣━ `/more <count> <text>` - Repeat message multiple times
┣━ `/weather <city>` - Get current weather for a city
┣━ `/weather_c <city>` - Get 5-day weather forecast
┣━ `/wiki <topic>` - Get Wikipedia summary for a topic
┣━ `/img <search query>` - Search for images from Pixabay
┣━ `/ai <prompt>` - Get AI response from Together AI
┣━ `/status` - Show system status and resource usage
┣━ `/refresh` - Clean memory and optimize bot performance
┣━ `/info` - Show group information and admin list *(Groups Only)*
┣━ `/cmd` - Show this command list
┗━ `/mg_count` - Show message statistics

🔧 **Filter Commands** *(Groups Only)*:
┣━ `/filter <keyword>` - Save filter (reply to a message)
┣━ `/del <keyword>` - Delete a filter
┗━ `/filters` - List all filters in group

🎯 **Quiz Commands:**
┣━ `/quiz` - Start a quiz in group chat *(Groups Only)*
┣━ `/set_quiz` - Add quiz questions *(Private Chat Only)*
┗━ `/stop_quiz` - Stop current quiz and show results *(Groups Only)*

✨ **Special Features:**
┣━ 📤 Forward messages to groups via private chat
┣━ 💬 Reply to group messages via private chat
┗━ 🔇 Auto-delete muted user messages

╔═══════════════════════════════╗
║   Made with ❤️ by Celestial Family   ║
║       🌟 Enjoy & Have Fun! 🌟       ║
╚═══════════════════════════════╝
    """

    await message.reply_text(commands_text, parse_mode='Markdown')

# Define the /refresh command
async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    message = update.message
    if not message:
        return

    # Check if user is authorized (only admin can refresh)
    if str(message.from_user.id) != "8197285353":
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        # Get current memory usage before cleanup
        memory_before = psutil.virtual_memory()
        used_before_mb = round(memory_before.used / (1024 * 1024))

        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm Refresh", callback_data="refresh_confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="refresh_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        refresh_text = f"""
🔄 **System Refresh Requested**

📊 **Current Memory Usage:** {used_before_mb} MB
⚠️ **Warning:** This will clean up bot memory and temporary data.

**What will be cleaned:**
• 🗑️ Garbage collection
• 📝 Pending messages cache
• 🎯 Quiz user states
• 🔧 Temporary variables

**Are you sure you want to proceed?**
        """

        await message.reply_text(refresh_text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        print(f"Error in refresh command: {e}")
        await message.reply_text("❌ An error occurred while preparing refresh.")

async def perform_memory_cleanup():
    """Perform actual memory cleanup operations"""
    import gc
    global pending_messages, quiz_user_states, quiz_settings, message_counts
    
    try:
        # Clear pending messages
        pending_messages.clear()
        
        # Clear quiz states
        quiz_user_states.clear()
        quiz_settings.clear()
        
        # Keep only recent message counts (last 7 days for daily, current month for others)
        today, week, month = get_date_keys()
        current_date = datetime.datetime.now()
        
        # Clean old daily counts (keep last 7 days)
        keys_to_remove = []
        for date_key in list(message_counts['daily'].keys()):
            try:
                date_obj = datetime.datetime.strptime(date_key, '%Y-%m-%d')
                if (current_date - date_obj).days > 7:
                    keys_to_remove.append(date_key)
            except:
                keys_to_remove.append(date_key)
        
        for key in keys_to_remove:
            del message_counts['daily'][key]
        
        # Force garbage collection multiple times
        collected = 0
        for _ in range(3):
            collected += gc.collect()
        
        return collected
        
    except Exception as e:
        print(f"Error during memory cleanup: {e}")
        return 0

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

# Define the /info command
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Only work in groups
    if message.chat.type == 'private':
        await message.reply_text("❌ This command can only be used in groups.")
        return

    try:
        chat = message.chat
        chat_id = chat.id
        
        # Get chat information
        chat_info = await context.bot.get_chat(chat_id)
        
        # Basic group info
        group_name = chat_info.title or "Unknown Group"
        group_type = "Supergroup" if chat.type == 'supergroup' else "Group"
        member_count = await context.bot.get_chat_member_count(chat_id)
        
        # Get group description
        description = chat_info.description or "No description available"
        if len(description) > 200:
            description = description[:197] + "..."
        
        # Get administrators
        try:
            administrators = await context.bot.get_chat_administrators(chat_id)
            
            owner = None
            admins = []
            
            for admin in administrators:
                user = admin.user
                if admin.status == 'creator':
                    owner = user
                elif admin.status == 'administrator':
                    admins.append({
                        'user': user,
                        'can_delete_messages': admin.can_delete_messages,
                        'can_restrict_members': admin.can_restrict_members,
                        'can_promote_members': admin.can_promote_members,
                        'can_change_info': admin.can_change_info,
                        'can_invite_users': admin.can_invite_users,
                        'can_pin_messages': admin.can_pin_messages,
                        'can_manage_video_chats': getattr(admin, 'can_manage_video_chats', False)
                    })
        except Exception as e:
            print(f"Error getting administrators: {e}")
            administrators = []
            owner = None
            admins = []
        
        # Format admin list
        admin_text = ""
        
        if owner:
            owner_name = owner.first_name
            if owner.last_name:
                owner_name += f" {owner.last_name}"
            if owner.username:
                owner_name += f" (@{owner.username})"
            admin_text += f"👑 **Owner:** [{owner_name}](tg://user?id={owner.id})\n\n"
        
        if admins:
            admin_text += "🛡️ **Administrators:**\n"
            for i, admin_info in enumerate(admins, 1):
                admin_user = admin_info['user']
                admin_name = admin_user.first_name
                if admin_user.last_name:
                    admin_name += f" {admin_user.last_name}"
                if admin_user.username:
                    admin_name += f" (@{admin_user.username})"
                
                # Show key permissions
                permissions = []
                if admin_info['can_delete_messages']:
                    permissions.append("🗑️")
                if admin_info['can_restrict_members']:
                    permissions.append("🔇")
                if admin_info['can_promote_members']:
                    permissions.append("⬆️")
                if admin_info['can_change_info']:
                    permissions.append("✏️")
                if admin_info['can_invite_users']:
                    permissions.append("👥")
                if admin_info['can_pin_messages']:
                    permissions.append("📌")
                if admin_info['can_manage_video_chats']:
                    permissions.append("📹")
                
                permission_text = " ".join(permissions) if permissions else "Basic"
                admin_text += f"{i}. [{admin_name}](tg://user?id={admin_user.id}) - {permission_text}\n"
        
        if not admin_text:
            admin_text = "❌ Could not retrieve administrator information"
        
        # Create modernized info text with better styling
        info_text = f"""
╔═══════════════════════════════╗
║       📋 **GROUP INFO**        ║
╚═══════════════════════════════╝

🏷️ **Group Details:**
┣━ **Name:** {group_name}
┣━ **Type:** {group_type}
┗━ **Members:** {member_count}

📝 **Description:**
{description}

╔═══════════════════════════════╗
║      👑 **ADMINISTRATION**     ║
╚═══════════════════════════════╝

{admin_text}

╔═══════════════════════════════╗
║    🔑 **PERMISSION LEGEND**    ║
╚═══════════════════════════════╝

🗑️ Delete Messages  |  🔇 Restrict Members
⬆️ Promote Members  |  ✏️ Change Info  
👥 Invite Users     |  📌 Pin Messages
📹 Manage Video Chats

╔═══════════════════════════════╗
║   🌟 Powered by Celestial Bot   ║
╚═══════════════════════════════╝
        """
        
        # Create delete button
        keyboard = [[InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_info_{message.message_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send info message without photo
        info_msg = await message.reply_text(
            info_text,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
        # Delete the command message
        await message.delete()
        
    except Exception as e:
        print(f"Error in info command: {e}")
        await message.reply_text("❌ An error occurred while fetching group information.")

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

# Handle /start command for quiz setup redirection
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or message.chat.type != 'private':
        return

    # Check if started with set_quiz parameter
    if context.args and context.args[0] == 'set_quiz':
        await set_quiz_command(update, context)
    else:
        await message.reply_text("👋 Hello! Use /cmd to see available commands.")

# Handle all messages to delete muted users' messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Handle quiz setup messages in private chat
    if message.chat.type == 'private' and message.from_user.id in quiz_user_states:
        await handle_quiz_setup_message(update, context)
        return

    # Check for admin commands FIRST before any other processing
    if message.text:
        if message.text == '.delete':
            await delete_command(update, context)
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
            reply_msg = message.reply_to_message
            reply_msg_id = reply_msg.message_id

            # Send the reply based on message type
            if message.text:
                await context.bot.send_message(
                    chat_id=8197285353,
                    text=message.text,
                    reply_to_message_id=reply_msg.message_id
                )
            elif message.photo:
                await context.bot.send_photo(
                    chat_id=8197285353,
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_msg.message_id
                )
            elif message.video:
                await context.bot.send_video(
                    chat_id=8197285353,
                    video=message.video.file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_msg.message_id
                )
            elif message.animation:
                await context.bot.send_animation(
                    chat_id=8197285353,
                    animation=message.animation.file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_msg.message_id
                )
            elif message.sticker:
                await context.bot.send_sticker(
                    chat_id=8197285353,
                    sticker=message.sticker.file_id,
                    reply_to_message_id=reply_msg.message_id
                )
            elif message.voice:
                await context.bot.send_voice(
                    chat_id=8197285353,
                    voice=message.voice.file_id,
                    reply_to_message_id=reply_msg.message_id
                )
            elif message.audio:
                await context.bot.send_audio(
                    chat_id=8197285353,
                    audio=message.audio.file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_msg.message_id
                )
            elif message.document:
                await context.bot.send_document(
                    chat_id=8197285353,
                    document=message.document.file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_msg.message_id
                )
            elif message.video_note:
                await context.bot.send_video_note(
                    chat_id=8197285353,
                    video_note=message.video_note.file_id,
                    reply_to_message_id=reply_msg.message_id
                )
            elif message.poll:
                poll = message.poll
                await context.bot.send_poll(
                    chat_id=8197285353,
                    question=poll.question,
                    options=[option.text for option in poll.options],
                    is_anonymous=poll.is_anonymous,
                    type=poll.type,
                    allows_multiple_answers=poll.allows_multiple_answers,
                    reply_to_message_id=reply_msg.message_id
                )
            else:
                # Fallback to forwarding if type not handled
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
        message_type = 'unsupported'
        content = None
        caption = None

        if message.text:
            message_type = 'text'
            content = message.text
        elif message.photo:
            message_type = 'photo'
            content = message.photo[-1].file_id
            caption = message.caption
        elif message.sticker:
            message_type = 'sticker'
            content = message.sticker.file_id
        elif message.video:
            message_type = 'video'
            content = message.video.file_id
            caption = message.caption
        elif message.animation:
            message_type = 'animation'
            content = message.animation.file_id
            caption = message.caption
        elif message.voice:
            message_type = 'voice'
            content = message.voice.file_id
        elif message.audio:
            message_type = 'audio'
            content = message.audio.file_id
            caption = message.caption
        elif message.document:
            message_type = 'document'
            content = message.document.file_id
            caption = message.caption
        elif message.video_note:
            message_type = 'video_note'
            content = message.video_note.file_id
        elif message.poll:
            message_type = 'poll'
            content = {
                'question': message.poll.question,
                'options': [option.text for option in message.poll.options],
                'is_anonymous': message.poll.is_anonymous,
                'type': message.poll.type,
                'allows_multiple_answers': message.poll.allows_multiple_answers
            }

        pending_messages[message_id] = {
            'type': message_type,
            'content': content,
            'caption': caption
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



# Define the /ai command for Together AI
async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check if prompt is provided
    if not context.args:
        await message.reply_text("❗ Please use the command like this:\n/ai <your prompt>")
        return

    prompt = ' '.join(context.args)

    try:
        # Get API key from environment
        api_key = os.environ.get('TOGETHER_API_KEY')
        if not api_key:
            await message.reply_text("❌ AI service is not configured.")
            return

        # Send "typing" action to show bot is processing
        await context.bot.send_chat_action(chat_id=message.chat_id, action='typing')

        # Make API request to Together AI
        url = "https://api.together.xyz/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "Qwen/Qwen2.5-7B-Instruct-Turbo",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "top_p": 0.9
        }

        response = requests.post(url, json=data, headers=headers, timeout=30)

        if response.status_code == 401:
            await message.reply_text("❌ AI service authentication failed.")
            return
        elif response.status_code == 429:
            await message.reply_text("❌ AI service rate limit exceeded. Please try again later.")
            return
        elif response.status_code != 200:
            await message.reply_text(f"❌ AI service error (Status: {response.status_code}). Please try again later.")
            return

        response_data = response.json()

        # Extract AI response
        if 'choices' not in response_data or not response_data['choices']:
            await message.reply_text("❌ No response from AI service.")
            return

        ai_response = response_data['choices'][0]['message']['content'].strip()

        if not ai_response:
            await message.reply_text("❌ Empty response from AI service.")
            return

        # Format response with user's prompt
        response_text = f"🤖 **AI Response:**\n\n{ai_response}"

        # Add prompt reference if response is long
        if len(ai_response) > 100:
            response_text = f"🤖 **AI Response to:** \"{prompt[:50]}{'...' if len(prompt) > 50 else ''}\"\n\n{ai_response}"

        await message.reply_text(response_text, parse_mode='Markdown')

    except requests.exceptions.Timeout:
        await message.reply_text("❌ AI service is taking too long to respond. Please try again.")
    except requests.exceptions.RequestException as e:
        print(f"AI API request error: {e}")
        await message.reply_text("❌ Unable to connect to AI service. Please try again later.")
    except KeyError as e:
        print(f"AI API response parsing error: {e}")
        await message.reply_text("❌ Unexpected response format from AI service.")
    except Exception as e:
        print(f"Error in ai command: {e}")
        await message.reply_text("❌ An error occurred while processing your request.")

# Quiz command for group chats
async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Only work in groups
    if message.chat.type == 'private':
        await message.reply_text("❌ Quiz can only be started in groups.")
        return

    # Check if quiz database is configured
    if quiz_collection is None:
        await message.reply_text("❌ Quiz service is not configured.")
        return

    chat_id = message.chat.id

    # Check if quiz is already running
    if chat_id in active_quizzes:
        await message.reply_text("❌ A quiz is already running in this group!")
        return

    try:
        # Check for unused questions
        unused_questions = await quiz_collection.find({"used": False}).to_list(length=None)

        if not unused_questions:
            # No unused questions available
            bot_username = context.bot.username
            quiz_link = f"https://t.me/{bot_username}?start=set_quiz"

            keyboard = [[InlineKeyboardButton("📝 ADD QUESTIONS", url=quiz_link)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await message.reply_text(
                "❌ My database doesn't have unused questions. Please add questions before using this feature.",
                reply_markup=reply_markup
            )
            return

        # Ask for number of questions first
        keyboard = [
            [InlineKeyboardButton("5️⃣", callback_data=f"quiz_select_5_{chat_id}")],
            [InlineKeyboardButton("🔟", callback_data=f"quiz_select_10_{chat_id}")],
            [InlineKeyboardButton("1️⃣5️⃣", callback_data=f"quiz_select_15_{chat_id}")],
            [InlineKeyboardButton("2️⃣0️⃣", callback_data=f"quiz_select_20_{chat_id}")],
            [InlineKeyboardButton("2️⃣5️⃣", callback_data=f"quiz_select_25_{chat_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_text(
            f"🎯 **Quiz Setup**\n\n📊 Available unused questions: {len(unused_questions)}\n\n🔢 How many questions do you want for this quiz?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        # Store available questions temporarily
        quiz_settings[f"available_{chat_id}"] = unused_questions

    except Exception as e:
        print(f"Error in quiz command: {e}")
        await message.reply_text("❌ An error occurred while starting the quiz.")

# Stop quiz command for group chats
async def stop_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Only work in groups
    if message.chat.type == 'private':
        await message.reply_text("❌ Stop quiz can only be used in groups.")
        return

    chat_id = message.chat.id

    # Check if quiz is running
    if chat_id not in active_quizzes:
        await message.reply_text("❌ No quiz is currently running in this group.")
        return

    try:
        # Show confirmation dialog before stopping quiz
        keyboard = [
            [
                InlineKeyboardButton("✅ Stop Quiz", callback_data=f"quiz_stop_confirm_{chat_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"quiz_stop_cancel_{chat_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_text(
            "🛑 **Are you sure you want to stop the quiz?**\n\nThis will end the current quiz and show final results.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        print(f"Error in stop_quiz command: {e}")
        await message.reply_text("❌ An error occurred while stopping the quiz.")

async def start_quiz_countdown(bot, chat_id):
    """Start quiz with countdown"""
    try:
        quiz_session = active_quizzes[chat_id]
        total_questions = quiz_session['total_questions']

        countdown_text = f"🎯 **QUIZ STARTING!**\n\n📊 Total Questions: {total_questions}\n⏱️ Time per question: {quiz_session['question_time']} seconds\n\n🕐 Starting in:"

        countdown_msg = await bot.send_message(
            chat_id=chat_id,
            text=countdown_text + " 3️⃣",
            parse_mode='Markdown'
        )

        quiz_session['countdown_message'] = countdown_msg

        # Countdown 3, 2, 1
        for i in [2, 1]:
            await asyncio.sleep(1)
            await countdown_msg.edit_text(countdown_text + f" {i}️⃣", parse_mode='Markdown')

        await asyncio.sleep(1)
        await countdown_msg.edit_text("🚀 **QUIZ STARTED!**", parse_mode='Markdown')

        # Start first question
        await send_quiz_poll(bot, chat_id, quiz_session['questions'][0])

    except Exception as e:
        print(f"Error in quiz countdown: {e}")

async def send_quiz_poll(bot, chat_id, question):
    """Send a quiz question using Telegram poll"""
    try:
        question_text = None
        for key, value in question.items():
            if key.startswith('question'):
                question_text = value
                break

        if not question_text:
            await bot.send_message(chat_id, "❌ Invalid question format.")
            return

        options = question.get('options', [])
        if len(options) != 4:
            await bot.send_message(chat_id, "❌ Question must have exactly 4 options.")
            return

        # Find correct answer index
        correct_answer = question.get('correct')
        correct_index = 0
        for i, option in enumerate(options):
            if option == correct_answer:
                correct_index = i
                break

        quiz_session = active_quizzes[chat_id]
        current_q = quiz_session['current_index'] + 1
        total_q = quiz_session['total_questions']

        # Send poll
        poll = await bot.send_poll(
            chat_id=chat_id,
            question=f"❓ Question {current_q}/{total_q}: {question_text}",
            options=options,
            type='quiz',
            correct_option_id=correct_index,
            open_period=quiz_session['question_time'],
            is_anonymous=False,
            explanation=f"✅ Correct answer: {correct_answer}"
        )

        quiz_session['poll_id'] = poll.poll.id
        quiz_session['current_poll'] = poll

        # Mark question as used
        await quiz_collection.update_one(
            {"_id": question['_id']},
            {"$set": {"used": True}}
        )

        # Schedule next question or end quiz using asyncio instead of job_queue
        asyncio.create_task(schedule_next_question(bot, chat_id, quiz_session['question_time']))

    except Exception as e:
        print(f"Error sending quiz poll: {e}")

async def schedule_next_question(bot, chat_id, delay_seconds):
    """Schedule the next question after a delay"""
    try:
        await asyncio.sleep(delay_seconds + 3)  # Add 3 seconds buffer

        if chat_id not in active_quizzes:
            return

        quiz_session = active_quizzes[chat_id]
        quiz_session['current_index'] += 1

        if quiz_session['current_index'] < len(quiz_session['questions']):
            # Send next question
            next_question = quiz_session['questions'][quiz_session['current_index']]
            await send_quiz_poll(bot, chat_id, next_question)
        else:
            # Quiz finished
            await show_quiz_final_results(bot, chat_id)
            del active_quizzes[chat_id]

    except Exception as e:
        print(f"Error scheduling next question: {e}")



async def show_quiz_final_results(bot, chat_id):
    """Show final quiz results"""
    try:
        quiz_session = active_quizzes.get(chat_id)
        if not quiz_session:
            return

        total_questions = quiz_session['total_questions']

        # Simple completion message without any leaderboard or scores
        results_text = f"🏁 **Quiz Finished!**\n\n📊 Total Questions: {total_questions}\n🎉 Thanks for participating!"

        await bot.send_message(chat_id, results_text, parse_mode='Markdown')

    except Exception as e:
        print(f"Error showing quiz results: {e}")
        await bot.send_message(chat_id, "❌ Error displaying results.")

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle poll answers from users"""
    try:
        poll_answer = update.poll_answer
        user_id = poll_answer.user.id
        poll_id = poll_answer.poll_id
        selected_options = poll_answer.option_ids

        print(f"Poll answer received: user_id={user_id}, poll_id={poll_id}, options={selected_options}")

        # Find which quiz this poll belongs to
        quiz_chat_id = None
        for chat_id, quiz_session in active_quizzes.items():
            if quiz_session.get('poll_id') == poll_id:
                quiz_chat_id = chat_id
                break

        if quiz_chat_id is None:
            print(f"Poll not found in active quizzes: {poll_id}")
            return  # Poll not found in active quizzes

        quiz_session = active_quizzes[quiz_chat_id]

        # Initialize participants dict if not exists
        if 'participants' not in quiz_session:
            quiz_session['participants'] = {}

        # Initialize scores dict if not exists
        if 'scores' not in quiz_session:
            quiz_session['scores'] = {}

        # Get user info
        try:
            user = await context.bot.get_chat(user_id)
            username = user.first_name
        except:
            username = f"User {user_id}"

        # Store user info for leaderboard
        quiz_session['participants'][user_id] = username

        # Initialize user score if not exists
        if user_id not in quiz_session['scores']:
            quiz_session['scores'][user_id] = 0

        print(f"Updated quiz session - Participants: {len(quiz_session['participants'])}, User {username} tracked")

        # Check if answer is correct (for quiz polls, Telegram automatically marks correct answers)
        # Since this is a quiz poll, we can check if the user answered correctly
        if selected_options:  # User answered
            current_question = quiz_session['questions'][quiz_session['current_index']]
            correct_answer = current_question.get('correct')

            if len(selected_options) > 0 and len(current_question['options']) > selected_options[0]:
                user_answer = current_question['options'][selected_options[0]]

                if user_answer == correct_answer:
                    quiz_session['scores'][user_id] += 1
                    print(f"User {username} answered correctly! Score: {quiz_session['scores'][user_id]}")
                else:
                    print(f"User {username} answered incorrectly. Correct: {correct_answer}, User: {user_answer}")

        print(f"Current quiz state: participants={len(quiz_session['participants'])}, scores={quiz_session['scores']}")

    except Exception as e:
        print(f"Error handling poll answer: {e}")

# Save setup command to exit quiz setup mode
async def save_setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Only work in private chats
    if message.chat.type != 'private':
        await message.reply_text("❌ This command can only be used in private chat.")
        return

    user_id = message.from_user.id

    # Check if user is in quiz setup mode
    if user_id not in quiz_user_states:
        await message.reply_text("❌ You are not currently in question adding mode.")
        return

    # Get current progress
    state = quiz_user_states[user_id]
    current_num = state.get('current_question_num', 1)
    total_num = state.get('total_questions', 0)

    # Clean up user state
    del quiz_user_states[user_id]
    if user_id in quiz_settings:
        del quiz_settings[user_id]

    # Send confirmation message
    if current_num > 1:
        questions_added = current_num - 1
        await message.reply_text(
            f"✅ **Setup saved!**\n\n📝 Questions added: {questions_added}/{total_num}\n\n🔄 You are now back to normal private chat mode.\nYou can forward messages to groups again."
        )
    else:
        await message.reply_text(
            "✅ **Setup exited!**\n\n🔄 You are now back to normal private chat mode.\nYou can forward messages to groups again."
        )

# Set quiz command for private chats
async def set_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Only work in private chats
    if message.chat.type != 'private':
        await message.reply_text("❌ Quiz setup can only be done in private chat.")
        return

    # Check if quiz database is configured
    if quiz_collection is None:
        await message.reply_text("❌ Quiz service is not configured.")
        return

    user_id = message.from_user.id

    # Initialize user state
    quiz_user_states[user_id] = {'step': 'count_selection'}

    # Ask for question count directly (skip time selection for now)
    keyboard = [
        [InlineKeyboardButton("🔢 10", callback_data="quiz_count_10")],
        [InlineKeyboardButton("🔢 15", callback_data="quiz_count_15")],
        [InlineKeyboardButton("🔢 20", callback_data="quiz_count_20")],
        [InlineKeyboardButton("🔢 25", callback_data="quiz_count_25")],
        [InlineKeyboardButton("🔢 30", callback_data="quiz_count_30")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        "🔢 How many questions do you want to add?",
        reply_markup=reply_markup
    )

async def handle_quiz_setup_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages during quiz setup"""
    message = update.message
    if not message or message.chat.type != 'private':
        return

    user_id = message.from_user.id
    if user_id not in quiz_user_states:
        return

    state = quiz_user_states[user_id]
    step = state.get('step')

    try:
        if step == 'question_text':
            state['current_question'] = {'text': message.text}
            state['step'] = 'option_1'
            await message.reply_text("📝 Enter option 1:")

        elif step == 'option_1':
            state['current_question']['options'] = [message.text]
            state['step'] = 'option_2'
            await message.reply_text("📝 Enter option 2:")

        elif step == 'option_2':
            state['current_question']['options'].append(message.text)
            state['step'] = 'option_3'
            await message.reply_text("📝 Enter option 3:")

        elif step == 'option_3':
            state['current_question']['options'].append(message.text)
            state['step'] = 'option_4'
            await message.reply_text("📝 Enter option 4:")

        elif step == 'option_4':
            state['current_question']['options'].append(message.text)
            state['step'] = 'correct_answer'

            # Show options for correct answer selection
            options = state['current_question']['options']
            keyboard = []
            for i, option in enumerate(options):
                keyboard.append([InlineKeyboardButton(f"{i+1}. {option}", callback_data=f"quiz_correct_{i}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text(
                "✅ Which one is the correct answer?",
                reply_markup=reply_markup
            )

    except Exception as e:
        print(f"Error in quiz setup: {e}")
        await message.reply_text("❌ An error occurred. Please try again.")

async def save_quiz_question(user_id, question_data):
    """Save a quiz question to MongoDB"""
    try:
        # Get the next question number
        last_question = await quiz_collection.find().sort("_id", -1).limit(1).to_list(length=1)
        question_num = 1

        if last_question:
            for key in last_question[0].keys():
                if key.startswith('question') and key[8:].isdigit():
                    question_num = max(question_num, int(key[8:]) + 1)

        # Create the question document
        question_doc = {
            f"question{question_num}": question_data['text'],
            "options": question_data['options'],
            "correct": question_data['correct'],
            "used": False,
            "created_by": user_id,
            "created_at": datetime.datetime.utcnow()
        }

        await quiz_collection.insert_one(question_doc)
        return True

    except Exception as e:
        print(f"Error saving quiz question: {e}")
        return False

async def show_quiz_results(bot, chat_id, scores):
    """Show final quiz results"""
    try:
        if not scores:
            await bot.send_message(chat_id, "🏁 **Quiz Finished!**\n\nNo one participated in the quiz.")
            return

        # Sort scores in descending order
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results_text = "🏁 **Quiz Finished! Final Results:**\n\n"

        for i, (user_id, score) in enumerate(sorted_scores, 1):
            try:
                user = await bot.get_chat(user_id)
                user_name = user.first_name

                if i == 1:
                    emoji = "🥇"
                elif i == 2:
                    emoji = "🥈"
                elif i == 3:
                    emoji = "🥉"
                else:
                    emoji = f"{i}."

                results_text += f"{emoji} <a href='tg://user?id={user_id}'>{user_name}</a>: {score} points\n"
            except:
                results_text += f"{i}. User {user_id}: {score} points\n"

        results_text += "\n🎉 Congratulations to all participants!"

        await bot.send_message(chat_id, results_text, parse_mode='HTML')

    except Exception as e:
        print(f"Error showing quiz results: {e}")
        await bot.send_message(chat_id, "❌ Error displaying results.")

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



    # Handle question count selection for quiz
    if query.data.startswith("quiz_select_"):
        parts = query.data.split("_")
        requested_count = int(parts[2])
        chat_id = int(parts[3])

        available_key = f"available_{chat_id}"
        if available_key not in quiz_settings:
            await query.edit_message_text("❌ Quiz session expired. Please try starting again.")
            return

        unused_questions = quiz_settings[available_key]
        available_count = len(unused_questions)

        if available_count < requested_count:
            # Not enough questions available
            keyboard = [
                [
                    InlineKeyboardButton("✅ Use Available", callback_data=f"quiz_use_available_{chat_id}_{available_count}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"quiz_cancel_{chat_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"⚠️ **Not Enough Questions**\n\n❌ My database doesn't have {requested_count} unused questions.\n📊 My database has only {available_count} unused questions.\n\n🔄 I will provide only my unused questions ({available_count} questions).\n\nDo you want to continue with {available_count} questions?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            # Enough questions available
            selected_questions = unused_questions[:requested_count]

            keyboard = [
                [
                    InlineKeyboardButton("✅ Start Quiz", callback_data=f"quiz_start_confirm_{chat_id}_{requested_count}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"quiz_cancel_{chat_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"🎯 **Quiz Ready!**\n\n📊 Questions: {requested_count}\n⏱️ Time per question: 30 seconds\n\n⚠️ **Are you sure you want to start the quiz?**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            # Store quiz data temporarily
            quiz_settings[f"temp_{chat_id}"] = {
                'questions': selected_questions,
                'current_index': 0,
                'scores': {},
                'total_questions': requested_count,
                'question_time': 30,
                'poll_id': None,
                'countdown_message': None
            }

    # Handle using available questions when not enough
    elif query.data.startswith("quiz_use_available_"):
        parts = query.data.split("_")
        chat_id = int(parts[3])
        available_count = int(parts[4])

        available_key = f"available_{chat_id}"
        if available_key not in quiz_settings:
            await query.edit_message_text("❌ Quiz session expired. Please try starting again.")
            return

        unused_questions = quiz_settings[available_key]

        keyboard = [
            [
                InlineKeyboardButton("✅ Start Quiz", callback_data=f"quiz_start_confirm_{chat_id}_{available_count}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"quiz_cancel_{chat_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"🎯 **Quiz Ready!**\n\n📊 Questions: {available_count}\n⏱️ Time per question: 30 seconds\n\n⚠️ **Are you sure you want to start the quiz?**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        # Store quiz data temporarily
        quiz_settings[f"temp_{chat_id}"] = {
            'questions': unused_questions,
            'current_index': 0,
            'scores': {},
            'total_questions': available_count,
            'question_time': 30,
            'poll_id': None,
            'countdown_message': None
        }

    # Handle quiz start confirmation
    elif query.data.startswith("quiz_start_confirm_"):
        parts = query.data.split("_")
        chat_id = int(parts[3])
        question_count = int(parts[4]) if len(parts) > 4 else 0

        temp_key = f"temp_{chat_id}"
        available_key = f"available_{chat_id}"

        if temp_key not in quiz_settings:
            await query.edit_message_text("❌ Quiz session expired. Please try starting again.")
            return

        # Move temporary quiz data to active quizzes
        active_quizzes[chat_id] = quiz_settings[temp_key]
        del quiz_settings[temp_key]

        # Clean up available questions
        if available_key in quiz_settings:
            del quiz_settings[available_key]

        await query.edit_message_text("🎯 **Quiz Starting!**", parse_mode='Markdown')

        # Start quiz countdown
        await start_quiz_countdown(context.bot, chat_id)

    # Handle quiz cancellation
    elif query.data.startswith("quiz_cancel_"):
        chat_id = int(query.data.split("_")[2])
        temp_key = f"temp_{chat_id}"
        available_key = f"available_{chat_id}"

        # Clean up temporary data
        if temp_key in quiz_settings:
            del quiz_settings[temp_key]
        if available_key in quiz_settings:
            del quiz_settings[available_key]

        await query.edit_message_text("❌ Quiz cancelled.")

    # Handle quiz stop confirmation
    elif query.data.startswith("quiz_stop_confirm_"):
        chat_id = int(query.data.split("_")[3])

        if chat_id not in active_quizzes:
            await query.edit_message_text("❌ No quiz is currently running.")
            return

        try:
            # Get quiz session
            quiz_session = active_quizzes[chat_id]

            # Stop the current poll if it exists
            if 'current_poll' in quiz_session and quiz_session['current_poll']:
                try:
                    await context.bot.stop_poll(
                        chat_id=chat_id,
                        message_id=quiz_session['current_poll'].message_id
                    )
                except Exception as e:
                    print(f"Error stopping poll: {e}")

            # Edit the confirmation message
            await query.edit_message_text("🛑 **Quiz stopped by admin!**", parse_mode='Markdown')

            # Show final results
            await show_quiz_final_results(context.bot, chat_id)

            # Clean up quiz session
            del active_quizzes[chat_id]

        except Exception as e:
            print(f"Error stopping quiz: {e}")
            await query.edit_message_text("❌ An error occurred while stopping the quiz.")

    # Handle quiz stop cancellation
    elif query.data.startswith("quiz_stop_cancel_"):
        await query.edit_message_text("✅ Quiz continues running.")

    # Handle refresh confirmation
    elif query.data == "refresh_confirm":
        # Check authorization again
        if str(query.from_user.id) != "8197285353":
            await query.answer("❌ You are not authorized to use this command.")
            return

        try:
            # Start refresh animation
            animation_frames = [
                "🔄 **Initializing refresh...**",
                "🧹 **Cleaning memory cache...**",
                "🗑️ **Running garbage collection...**",
                "📊 **Optimizing performance...**",
                "⚡ **Finalizing cleanup...**"
            ]

            # Show animation frames
            for i, frame in enumerate(animation_frames):
                await query.edit_message_text(frame, parse_mode='Markdown')
                if i < len(animation_frames) - 1:  # Don't sleep after last frame
                    await asyncio.sleep(1)

            # Perform actual cleanup
            collected_objects = await perform_memory_cleanup()

            # Get memory usage after cleanup
            memory_after = psutil.virtual_memory()
            used_after_mb = round(memory_after.used / (1024 * 1024))
            available_mb = round(memory_after.available / (1024 * 1024))

            # Final success message
            success_text = f"""
✅ **Refresh Completed Successfully!**

📊 **Memory Status:**
• Used: {used_after_mb} MB
• Available: {available_mb} MB
• Objects collected: {collected_objects}

🧹 **Cleaned up:**
• ✅ Pending messages cache
• ✅ Quiz user states  
• ✅ Temporary data
• ✅ Old message counts

🚀 **Bot performance optimized!**
            """

            await query.edit_message_text(success_text.strip(), parse_mode='Markdown')

        except Exception as e:
            print(f"Error during refresh: {e}")
            await query.edit_message_text("❌ **Refresh failed!** An error occurred during cleanup.")

    # Handle refresh cancellation
    elif query.data == "refresh_cancel":
        await query.edit_message_text("❌ **Refresh cancelled.** No changes were made.")

    # Handle info message deletion
    elif query.data.startswith("delete_info_"):
        try:
            # Delete the info message
            await query.message.delete()
        except Exception as e:
            print(f"Error deleting info message: {e}")
            await query.answer("❌ Failed to delete message.")

    # Handle quiz count selection
    elif query.data.startswith("quiz_count_"):
        user_id = query.from_user.id
        question_count = int(query.data.split("_")[2])

        if user_id not in quiz_user_states:
            await query.edit_message_text("❌ Session expired. Please start again with /set_quiz")
            return

        quiz_settings[user_id] = {'question_count': question_count}
        quiz_user_states[user_id].update({
            'step': 'question_text',
            'current_question_num': 1,
            'total_questions': question_count
        })

        await query.edit_message_text(
            f"✅ Will add {question_count} questions.\n\n📝 **Question 1/{question_count}**\nEnter the question text:\n\n💡 **Tip:** Send /save_setup anytime to exit question adding mode and return to normal chat."
        )

    # Handle correct answer selection
    elif query.data.startswith("quiz_correct_"):
        user_id = query.from_user.id
        correct_index = int(query.data.split("_")[2])

        if user_id not in quiz_user_states:
            await query.edit_message_text("❌ Session expired.")
            return

        state = quiz_user_states[user_id]
        if 'current_question' not in state:
            await query.edit_message_text("❌ No question data found.")
            return

        # Set correct answer
        state['current_question']['correct'] = state['current_question']['options'][correct_index]

        # Save question to database
        success = await save_quiz_question(user_id, state['current_question'])

        if success:
            current_num = state['current_question_num']
            total_num = state['total_questions']

            if current_num < total_num:
                # Move to next question
                state['current_question_num'] += 1
                state['step'] = 'question_text'
                await query.edit_message_text(
                    f"✅ Question {current_num} saved!\n\n📝 **Question {current_num + 1}/{total_num}**\nEnter the question text:\n\n💡 **Tip:** Send /save_setup anytime to exit question adding mode."
                )
            else:
                # All questions completed
                await query.edit_message_text(
                    f"🎉 **All {total_num} questions saved successfully!**\n\nYou can now use /quiz in group chats to start a quiz."
                )
                del quiz_user_states[user_id]
                if user_id in quiz_settings:
                    del quiz_settings[user_id]
        else:
            await query.edit_message_text("❌ Failed to save question. Please try again.")



    # Handle image pagination
    elif query.data.startswith("img_next_"):
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
            elif message_data['type'] == 'photo':
                await context.bot.send_photo(
                    chat_id=group_info["id"],
                    photo=message_data['content'],
                    caption=message_data['caption']
                )
            elif message_data['type'] == 'sticker':
                await context.bot.send_sticker(
                    chat_id=group_info["id"],
                    sticker=message_data['content']
                )
            elif message_data['type'] == 'video':
                await context.bot.send_video(
                    chat_id=group_info["id"],
                    video=message_data['content'],
                    caption=message_data['caption']
                )
            elif message_data['type'] == 'animation':
                await context.bot.send_animation(
                    chat_id=group_info["id"],
                    animation=message_data['content'],
                    caption=message_data['caption']
                )
            elif message_data['type'] == 'voice':
                await context.bot.send_voice(
                    chat_id=group_info["id"],
                    voice=message_data['content']
                )
            elif message_data['type'] == 'audio':
                await context.bot.send_audio(
                    chat_id=group_info["id"],
                    audio=message_data['content'],
                    caption=message_data['caption']
                )
            elif message_data['type'] == 'document':
                await context.bot.send_document(
                    chat_id=group_info["id"],
                    document=message_data['content'],
                    caption=message_data['caption']
                )
            elif message_data['type'] == 'video_note':
                await context.bot.send_video_note(
                    chat_id=group_info["id"],
                    video_note=message_data['content']
                )
            elif message_data['type'] == 'poll':
                poll_data = message_data['content']
                await context.bot.send_poll(
                    chat_id=group_info["id"],
                    question=poll_data['question'],
                    options=poll_data['options'],
                    is_anonymous=poll_data['is_anonymous'],
                    type=poll_data['type'],
                    allows_multiple_answers=poll_data['allows_multiple_answers']
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

app.add_handler(CommandHandler("status", status_command))
app.add_handler(CommandHandler("cmd", cmd_command))
app.add_handler(CommandHandler("mg_count", mg_count_command))
app.add_handler(CommandHandler("info", info_command))
app.add_handler(CommandHandler("refresh", refresh_command))
app.add_handler(CommandHandler("go", go_command))
app.add_handler(CommandHandler("voice", voice_command))
app.add_handler(CommandHandler("stick", stick_command))

app.add_handler(CommandHandler("more", more_command))
app.add_handler(CommandHandler("weather", weather_command))
app.add_handler(CommandHandler("weather_c", weather_forecast_command))
app.add_handler(CommandHandler("wiki", wiki_command))
app.add_handler(CommandHandler("img", img_command))

app.add_handler(CommandHandler("ai", ai_command))
app.add_handler(CommandHandler("filter", filter_command))
app.add_handler(CommandHandler("del", del_filter_command))
app.add_handler(CommandHandler("filters", filters_list_command))
app.add_handler(CommandHandler("quiz", quiz_command))
app.add_handler(CommandHandler("set_quiz", set_quiz_command))
app.add_handler(CommandHandler("stop_quiz", stop_quiz_command))
app.add_handler(CommandHandler("save_setup", save_setup_command))
app.add_handler(CommandHandler("start", start_command))

app.add_handler(MessageHandler(filters.Regex(r'^\.mute$'), mute_command))
app.add_handler(MessageHandler(filters.Regex(r'^\.mute_list$'), mute_list_command))
app.add_handler(MessageHandler((filters.TEXT | filters.Sticker.ALL | filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.VOICE | filters.AUDIO | filters.Document.ALL | filters.VIDEO_NOTE | filters.POLL) & ~filters.COMMAND, handle_message))

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




app.add_handler(CallbackQueryHandler(button_callback))
app.add_handler(PollAnswerHandler(handle_poll_answer))

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
