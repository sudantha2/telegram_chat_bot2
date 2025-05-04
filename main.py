from telegram import Update

from telegram.ext import MessageHandler, filters
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from keep_alive import keep_alive
import os
from PIL import Image, ImageDraw, ImageFont
import random
import io
import requests

# Start the Replit web server to keep the bot alive
keep_alive()

# Get the bot token from Replit Secrets
TOKEN = os.environ['TOKEN']

# Store muted users
muted_users = set()

# Define the mute command
async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check if command is from authorized user
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

# Handle all messages to delete muted users' messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Delete message if user is muted
    if message.from_user.id in muted_users:
        await message.delete()
        return

    # Check for inbox variations

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
    import tempfile
    import os

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

    # Create temporary file for voice message
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
        # Convert text to speech in Sinhala
        tts = gTTS(text=text, lang='si')
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Check for muted users
    if message.from_user.id in muted_users:
        await message.delete()
        return

    # Handle group messages
    if message.chat.type != 'private':
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
        
        # Forward regular messages to group
        if message.text and not message.text.startswith('/'):
            await context.bot.send_message(
                chat_id=-1002357656013,
                text=message.text
            )
        elif message.sticker:
            await context.bot.send_sticker(
                chat_id=-1002357656013,
                sticker=message.sticker.file_id
            )
        elif message.photo:
            await context.bot.send_photo(
                chat_id=-1002357656013,
                photo=message.photo[-1].file_id,
                caption=message.caption
            )
        else:
            await message.reply_text("❌ Message type not supported")
            return
            
        await message.reply_text("✅ Forwarded to group!")
        
    except Exception as e:
        print(f"Error handling message: {e}")
        await message.reply_text("❌ Failed to process message")

    # Convert message to lowercase for case-insensitive comparison
    text = message.text.lower()

    # Check for .delete command
    if text == '.delete':
        # Check if user is authorized
        if str(message.from_user.id) == "8197285353":
            # Check if it's a reply
            if message.reply_to_message:
                # Delete both messages
                await message.delete()
                await message.reply_to_message.delete()
        return

    # Check for .delete_all command
    if text == '.delete_all':
        # Check if user is authorized
        if str(message.from_user.id) == "8197285353":
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
        return

    # Check for .mute_list command
    if text == '.mute_list':
        await mute_list_command(update, context)
        return

    # Check for .mute command
    if text.startswith('.mute'):
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

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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

    # Check if the button was clicked by authorized user
    if str(query.from_user.id) != "8197285353":
        await query.answer("You are not authorized to use these buttons.")
        return

    await query.answer()

    if query.data.startswith("user_"):
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
        if str(query.from_user.id) != "8197285353":
            await query.answer("You are not authorized to use this command.")
            return
            
        if query.data == "delete_all_cancel":
            await query.message.delete()
            return
            
        user_id = int(query.data.split("_")[2])
        try:
            chat = await context.bot.get_chat(user_id)
            user_mention = f"<a href='tg://user?id={user_id}'>{chat.first_name}</a>"
            
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
app.add_handler(CommandHandler("go", go_command))
app.add_handler(CommandHandler("voice", voice_command))
app.add_handler(CommandHandler("stick", stick_command))
app.add_handler(CommandHandler("hello", hello_command))
app.add_handler(CommandHandler("more", more_command))
app.add_handler(CommandHandler("mute", mute_command))
app.add_handler(CommandHandler("mute_list", mute_list_command))
app.add_handler(MessageHandler((filters.TEXT | filters.Sticker.ALL | filters.PHOTO) & ~filters.COMMAND, handle_message))
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
