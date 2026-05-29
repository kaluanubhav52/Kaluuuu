import os
import logging
import random
import asyncio
import re
import json
import base64
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from validators import domain
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import *

# Internal module imports
from Script import script
from plugins.dbusers import db
from plugins.users_api import get_user, update_user_info
from utils import verify_user, check_token, check_verification, get_token
from config import *
from TechVJ.utils.file_properties import get_name, get_hash, get_media_file_size

# Logging configurations
logger = logging.getLogger(__name__)


# global 
original_reply = Message.reply
async def patched_reply(self, *args, **kwargs):
    kwargs.setdefault('quote', False)
    return await original_reply(self, *args, **kwargs)
Message.reply = patched_reply

original_reply_text = Message.reply_text
async def patched_reply_text(self, *args, **kwargs):
    kwargs.setdefault('quote', False)
    return await original_reply_text(self, *args, **kwargs)
Message.reply_text = patched_reply_text

original_reply_photo = Message.reply_photo
async def patched_reply_photo(self, *args, **kwargs):
    kwargs.setdefault('quote', False)
    return await original_reply_photo(self, *args, **kwargs)
Message.reply_photo = patched_reply_photo

# end

BATCH_FILES = {}
CANCEL_PROCESSING = {}

# --- HELPER FUNCTIONS ---

async def auto_delete_msg(message, delay=300):
    """Asynchronously deletes temporary fallback/verification messages."""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Error deleting temporary verification message: {e}")

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def formate_file_name(file_name):
    if not file_name:
        return "Media File"
    chars = ["[", "]", "(", ")"]
    for c in chars:
        file_name = file_name.replace(c, "")
    file_name = '@HDFILM0900_BOT ' + ' '.join(filter(lambda x: not x.startswith('http') and not x.startswith('@') and not x.startswith('www.'), file_name.split()))
    return file_name


# ⭐⭐⭐ SECURED TEXT TRANSITION HELPER (Locks Buttons to Prevent Multiple Clicks) ⭐⭐⭐
async def show_text_transition(query):
    """Temporarily removes/locks buttons during text loading to prevent user double-clicks."""
    try:
        is_media = bool(query.message.photo or query.message.video or query.message.animation)
        
        # Loading ke waqt buttons ko "Please Wait" se lock kar dete hain taaki user click na kar paye
        lock_markup = InlineKeyboardMarkup([[InlineKeyboardButton("👑 𝙳𝙴𝚅𝙴𝙻𝙾𝙿𝙴𝚁", url="https://t.me/HDFILM0900_BOT")]])
        
        steps = ["● ◌ ◌", "● ● ◌", "● ● ●"]
        
        for step in steps:
            if is_media:
                await query.message.edit_caption(caption=step, reply_markup=lock_markup)
            else:
                await query.message.edit_text(text=step, reply_markup=lock_markup)
            await asyncio.sleep(0.3) # Delay space
            
    except Exception as e:
        logger.error(f"Text transition bypass: {e}")


# --- BOT ROUTING ENGINE ---

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except Exception:
        try: await message.react(emoji="⚡️", big=True)
        except Exception: pass
            
    username = client.me.username
    user_id = message.from_user.id
    
    # Live data extraction from dbusers system
    settings = await db.get_settings()
    is_verify_mode = settings.get("verify_mode", True)
    is_protect = settings.get("protect_content", False)
    is_autodelete = settings.get("auto_delete_mode", True)
    del_time_seconds = settings.get("auto_delete_time", 1800)
    del_time_minutes = del_time_seconds // 60
    
    is_premium = await db.check_premium_status(user_id)
    
    start_photo = settings.get("start_photo", None)
    is_spoiler = settings.get("start_spoiler", False) 
    db_start_text = settings.get("custom_start_text", None)
    start_caption = db_start_text if db_start_text else script.START_TXT

    # Auto Add New Users to Database
    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT.format(user_id, message.from_user.mention))
    
    # Render Main Menu Panel if no parameters passed
    if len(message.command) != 2:
        await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)
        await asyncio.sleep(1)
        
        buttons = [
            [
                InlineKeyboardButton('🔍 Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url='https://t.me/pratilipifm0900'),
                InlineKeyboardButton('🤖 Sᴛᴏʀʏ Cʜᴀɴɴᴇʟ', url='https://t.me/freestoryhubMR')
            ],
            [
                InlineKeyboardButton('💁‍♀️ Fᴇᴀᴛᴜʀᴇs', callback_data='help'),
                InlineKeyboardButton('😊 Aʙᴏᴜᴛ', callback_data='about')
            ],
            [InlineKeyboardButton('⭐ ᗷᑌY ᑭᖇᗴᗰIᑌᗰ ⭐', callback_data='buy_premium_panel', style=enums.ButtonStyle.DANGER)],
            [InlineKeyboardButton('⁉️ SᴇᴛᴛɪɴGS ⁉️', callback_data='open_admin_from_start', style=enums.ButtonStyle.PRIMARY)]
        ]
        if CLONE_MODE:
            buttons.append([InlineKeyboardButton('🤖 ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')])
            
        reply_markup = InlineKeyboardMarkup(buttons)
        me = client.me
        
        if start_photo:
            await message.reply_photo(
                photo=start_photo,
                caption=start_caption.format(message.from_user.mention, me.mention),
                reply_markup=reply_markup,
                has_spoiler=is_spoiler
            )
        else:
            await message.reply_text(
                text=start_caption.format(message.from_user.mention, me.mention),
                reply_markup=reply_markup,
                protect_content=is_protect
            )
        return

    data = message.command[1]
    
    # --- FIXED VERIFICATION ROUTER ENGINE ---
    if data.split("-", 1)[0] == "verify":
        try:
            userid = data.split("-", 2)[1]
            token = data.split("-", 3)[2]
        except IndexError:
            return await message.reply_text(text="<b>❌ Invalid Link Structure!</b>", protect_content=is_protect)

        if str(user_id) != str(userid):
            return await message.reply_text(text="<b>❌ Invalid link or Expired link !</b>", protect_content=is_protect)
        
        status_reply = await message.reply_text("<b>⏳ Processing your verification... Please wait!</b>", protect_content=is_protect)
        
        is_valid = await check_token(client, userid, token)
        if is_valid:
            await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)
            
            try:
                await verify_user(client, userid, token)
                from time import time
                try:
                    await update_user_info(int(userid), {"is_verified": True, "verified_at": int(time()), "verify_token": token})
                except Exception:
                    if hasattr(db, 'update_user'):
                        await db.update_user(int(userid), {"is_verified": True})
            except Exception as db_err:
                logger.error(f"Database sync bypass log: {db_err}")

            clean_token = token.split("-")[0] if "-" in token else token
            actual_file_param = data.split(f"verify-{userid}-{clean_token}-")[-1] if f"verify-{userid}-{clean_token}-" in data else ""
            
            redirect_target = actual_file_param if actual_file_param else clean_token

            redirect_btn = [[
                InlineKeyboardButton("📌 GET FILE NOW 📌", url=f"https://t.me/{username}?start={redirect_target}", style=enums.ButtonStyle.PRIMARY)
            ]]

            await status_reply.edit_text(
                text=script.VERIFIED_SUCCESS_TXT.format(message.from_user.mention) + "\n\n<b>✅ Verification Successful! Click below to claim your files.</b>",
                reply_markup=InlineKeyboardMarkup(redirect_btn)
            )
            asyncio.create_task(auto_delete_msg(status_reply, 300))
        else:
            await status_reply.edit_text(text="<b>❌ Invalid token link or expired tracking key!</b>")
        return

    # --- FILE DELIVERY ENGINE ---
    try:
        if not is_premium and settings.get("premium_mode", False):
            buy_btn = InlineKeyboardMarkup([[InlineKeyboardButton("👑 ᗷᑌY ᑭᖇᗴᗰIᑌᗰ", callback_data='buy_premium_panel', style=enums.ButtonStyle.PRIMARY)]])
            await message.reply_text(
                "👑 **यह फाइल प्रीमियम है!**\n\nइसे एक्सेस करने के लिए कृपया प्रीमियम लें।\n\n"
                "🔎 ᴄʟɪᴄᴋ ᴏɴ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ", 
                reply_markup=buy_btn
            )
            return 
        
        if not is_premium and is_verify_mode and not await check_verification(client, user_id):
            await db.increment_token_count()
            
            btn = [[
                InlineKeyboardButton("🌀 VERIFY 🌀", url=await get_token(client, user_id, f"https://telegram.me/{username}?start=", data)),
                InlineKeyboardButton("⁉️ TUTORIAL ⁉️", url=VERIFY_TUTORIAL)
            ]]
            not_verified_msg = await message.reply_text(
                text=script.NOT_VERIFIED_TXT.format(message.from_user.mention),
                protect_content=is_protect,
                reply_markup=InlineKeyboardMarkup(btn)
            )
            asyncio.create_task(auto_delete_msg(not_verified_msg, 300))
            return
    except Exception as e:
        return await message.reply_text(f"**Error - {e}**")

    processing_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 DEVELOPER", url="https://t.me/HDFILM0900_BOT", style=enums.ButtonStyle.PRIMARY)],
        [InlineKeyboardButton("❌ CANCEL", callback_data=f"cancel_batch_{user_id}", style=enums.ButtonStyle.DANGER)]
    ])
    CANCEL_PROCESSING[user_id] = False
    sts = await message.reply(text="<b>🔺 𝙿𝙻𝙴𝙰𝚂𝙴 𝚆𝙰𝙸𝚃</b>", reply_markup=processing_keyboard)

    try:
        decoded_bytes = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
        decoded_str = decoded_bytes.decode("ascii")
        
        if "file_" in decoded_str:
            decode_file_id = decoded_str.replace("file_", "")
        else:
            decode_file_id = decoded_str.split("_", 1)[1] if "_" in decoded_str else decoded_str
            
        msg = await client.get_messages(DB_CHANNEL, int(decode_file_id))
        
        if msg.document and msg.document.file_name == "Batch.json":
            file_id = data
            msgs = BATCH_FILES.get(file_id)
            
            if not msgs:
                try:
                    file = await client.download_media(msg)
                    with open(file, "r") as file_data:
                        msgs = json.loads(file_data.read())
                    os.remove(file)
                    BATCH_FILES[file_id] = msgs
                except Exception as e:
                    await sts.edit("<b>FAILED TO FETCH BATCH DATA ❌</b>")
                    return await client.send_message(DB_CHANNEL, f"UNABLE TO OPEN BATCH FILE: {str(e)}")
                
            filesarr = []
            for msg_item in msgs:
                if CANCEL_PROCESSING.get(user_id, False):
                    await sts.edit("<b>❌ Batch Processing Cancelled!</b>")
                    await asyncio.sleep(3)
                    await sts.delete()
                    if user_id in CANCEL_PROCESSING: del CANCEL_PROCESSING[user_id]
                    return

                try:
                    channel_id = int(msg_item.get("channel_id"))
                    msgid = int(msg_item.get("msg_id"))
                    info = await client.get_messages(channel_id, msgid)
                    
                    if info.empty or info.service: continue
                        
                    if info.media:
                        file_type = info.media
                        file = getattr(info, file_type.value)
                        f_caption = getattr(info, 'caption', '')
                        if f_caption: f_caption = f"@HDFILM0900_BOT {f_caption.html}"
                        old_title = getattr(file, "file_name", "Media File")
                        title = formate_file_name(old_title)
                        size = get_size(int(file.file_size)) if hasattr(file, "file_size") else "Unknown"
                        
                        if BATCH_FILE_CAPTION:
                            try:
                                f_caption = BATCH_FILE_CAPTION.format(file_name=title, file_size=size, file_caption=f_caption)
                            except Exception: pass
                        if f_caption is None: f_caption = f"@HDFILM0900_BOT {title}"
                            
                        if STREAM_MODE and (info.video or info.document):
                            stream = f"{URL}watch/{str(info.id)}/{quote_plus(get_name(info))}?hash={get_hash(info)}"
                            download = f"{URL}{str(info.id)}/{quote_plus(get_name(info))}?hash={get_hash(info)}"
                            button = [
                                [InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download), InlineKeyboardButton('• ᴡᴀᴛᴄʜ •', url=stream)],
                                [InlineKeyboardButton("• ᴡᴀᴛᴄʜ ɪɴ ᴡᴇʙ ᴀᴘᴘ •", web_app=WebAppInfo(url=stream))]
                            ]
                            reply_markup = InlineKeyboardMarkup(button)
                        else:
                            reply_markup = None
                        
                        await client.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_DOCUMENT)
                        msg_out = await info.copy(chat_id=user_id, caption=f_caption, protect_content=is_protect, reply_markup=reply_markup)
                    else:
                        await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)
                        msg_out = await info.copy(chat_id=user_id, protect_content=is_protect)
                    
                    filesarr.append(msg_out)
                    await asyncio.sleep(1)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    msg_out = await info.copy(chat_id=user_id, protect_content=is_protect)
                    filesarr.append(msg_out)
                except Exception:
                    continue
                    
            await sts.delete()
            if user_id in CANCEL_PROCESSING: del CANCEL_PROCESSING[user_id]
            
            if is_autodelete:
                k = await client.send_message(chat_id=user_id, text=f"<b><u>...IMPORTANT...</u></b>\n\nThis Movie File/Video will be deleted in <b><u>{del_time_minutes} minutes</u></b>.")
                await asyncio.sleep(del_time_seconds)
                for x in filesarr:
                    try: await x.delete()
                    except Exception: pass
                try: await k.edit_text("<b>Your All Files/Videos is successfully deleted!!!</b>")
                except Exception: pass
            return

        else:
            if msg.media:
                media = getattr(msg, msg.media.value)
                old_title = media.file_name if hasattr(media, "file_name") else "Photo File"
                title = formate_file_name(old_title)
                size = get_size(media.file_size) if hasattr(media, "file_size") else "Unknown"
                
                f_caption = f"@HDFILM0900_BOT <code>{title}</code>"
                if CUSTOM_FILE_CAPTION:
                    try:
                        f_caption = CUSTOM_FILE_CAPTION.format(file_name=title, file_size=size, file_caption='')
                    except Exception: pass
                
                if STREAM_MODE and (msg.video or msg.document):
                    log_msg = msg
                    stream = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    download = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    button = [
                        [InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download), InlineKeyboardButton('• ᴡᴀᴛᴄʜ •', url=stream)],
                        [InlineKeyboardButton("• ᴡᴀᴛᴄ_ʜ ɪɴ ᴡᴇʙ ᴀᴘᴘ •", web_app=WebAppInfo(url=stream))]
                    ]
                    reply_markup = InlineKeyboardMarkup(button)
                else: reply_markup = None
                    
                await client.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_DOCUMENT)
                await asyncio.sleep(1) 
                del_msg = await msg.copy(chat_id=user_id, caption=f_caption, reply_markup=reply_markup, protect_content=is_protect)
            else:
                await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)
                del_msg = await msg.copy(chat_id=user_id, protect_content=is_protect)
                
            await sts.delete()

            if is_autodelete:
                k = await client.send_message(chat_id=user_id, text=f"<b><u>...IMPORTANT...</u></b>\n\nThis Movie File/Video will be deleted in <b><u>{del_time_minutes} minutes</u></b>.")
                await asyncio.sleep(del_time_seconds)
                try: await del_msg.delete()
                except Exception: pass
                try: await k.edit_text("<b>Your File/Video is successfully deleted!!!</b>")
                except Exception: pass
            return
            
    except Exception as e:
        logger.error(f"Error in execution: {str(e)}")
        try: await sts.delete()
        except Exception: pass

# --- ADMIN API ENGINE ---

@Client.on_message(filters.command('api') & filters.private)
async def shortener_api_handler(client, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command

    if len(cmd) == 1:
        s = script.SHORTENER_API_MESSAGE.format(base_site=user["base_site"], shortener_api=user["shortener_api"])
        return await m.reply(s)
    elif len(cmd) == 2:    
        api = cmd[1].strip()
        await update_user_info(user_id, {"shortener_api": api})
        await m.reply("<b>Shortener API updated successfully to</b> " + api)

@Client.on_message(filters.command("base_site") & filters.private)
async def base_site_handler(client, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command
    text = (
        "`/base_site (base_site)`\n\n<b>Current base site: None\n\n EX:</b> "
        "`/base_site shortnerdomain.com`\n\nIf You Want To Remove Base Site Then Copy This And Send To Bot - `/base_site None`"
    )
    if len(cmd) == 1:
        return await m.reply(text=text, disable_web_page_preview=True)
    elif len(cmd) == 2:
        base_site = cmd[1].strip()
        if base_site == "None" or base_site is None:
            await update_user_info(user_id, {"base_site": None})
            return await m.reply("<b>Base Site updated successfully</b>")
            
        if not domain(base_site):
            return await m.reply(text=text, disable_web_page_preview=True)
        await update_user_info(user_id, {"base_site": base_site})
        await m.reply("<b>Base Site updated successfully</b>")

# --- INTERACTIVE CALLBACKS (SECURED AGAINST SPAM/DOUBLE-CLICKS) ---

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    settings = await db.get_settings()
    start_photo = settings.get("start_photo", None)
    is_spoiler = settings.get("start_spoiler", False)
    db_start_text = settings.get("custom_start_text", None)
    start_caption = db_start_text if db_start_text else script.START_TXT

    # Dummy handler for locked button click
    if query.data == "dummy_lock":
        await query.answer("Please wait, loading current step... ⏳", show_alert=False)
        return

    if query.data.startswith("cancel_batch_"):
        target_uid = int(query.data.split("_")[2])
        if query.from_user.id == target_uid:
            CANCEL_PROCESSING[target_uid] = True
            await query.answer("Cancelling ongoing file process... 🛑", show_alert=True)
        else:
            await query.answer("❌ Yeh action aapke liye nahi hai!", show_alert=True)
        return

    if query.data == "close_data":
        await query.message.delete()
        
    elif query.data == "buy_premium_panel":
        premium_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 QR Code", callback_data="show_premium_qr"), InlineKeyboardButton("💳 UPI ID", callback_data="show_premium_upi")],
            [InlineKeyboardButton("⬅️ Back", callback_data="start")]
        ])
        
        # 🔒 Lock Buttons & Show Transition Text First
        await show_text_transition(query)

        try:
            if start_photo:
                await query.message.edit_caption(caption=PREMIUM_PLANS_TEXT, reply_markup=premium_keyboard)
            else:
                await query.message.edit_text(text=PREMIUM_PLANS_TEXT, reply_markup=premium_keyboard)
        except Exception:
            try: await query.message.delete()
            except Exception: pass
            await client.send_message(query.message.chat.id, text=PREMIUM_PLANS_TEXT, reply_markup=premium_keyboard)

    elif query.data == "show_premium_qr":
        screenshot_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Send Payment Screenshot", url=f"https://t.me/HDFILM0900_BOT", style=enums.ButtonStyle.PRIMARY)], 
            [InlineKeyboardButton("❌ Close ❌", callback_data='close_data', style=enums.ButtonStyle.DANGER)]
        ])
        await query.message.reply_photo(
            photo=QR_IMAGE_URL,
            caption=f"⚡ <b>PAY AMOUNT ACCORDING TO YOUR PLAN AND ENJOY PREMIUM MEMBERSHIP !</b>\n\n‼️ <b>MUST SEND SCREENSHOT AFTER PAYMENT</b>\nपेमेंट होने के बाद हमें स्क्रीनशॉट भेजें।",
            reply_markup=screenshot_keyboard
        )
        await query.answer() 

    elif query.data == "show_premium_upi":
        screenshot_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Send Payment Screenshot", url=f"https://t.me/HDFILM0900_BOT", style=enums.ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("⬅️ Back", callback_data="buy_premium_panel")]
        ])
        
        # 🔒 Lock Buttons & Show Transition Text First
        await show_text_transition(query)

        try:
            if start_photo:
                await query.message.edit_caption(caption=f"👉 <b>PAY AMOUNT ACCORDING TO YOUR PLAN</b>\n\n📌 <b>UPI ID:</b> <code>{UPI_ID}</code>\n\n‼️ <b>MUST SEND SCREENSHOT AFTER PAYMENT</b>", reply_markup=screenshot_keyboard)
            else:
                await query.message.edit_text(text=f"👉 <b>PAY AMOUNT ACCORDING TO YOUR PLAN</b>\n\n📌 <b>UPI ID:</b> <code>{UPI_ID}</code>\n\n‼️ <b>MUST SEND SCREENSHOT AFTER PAYMENT</b>", reply_markup=screenshot_keyboard)
        except Exception:
            try: await query.message.delete()
            except Exception: pass
            await client.send_message(query.message.chat.id, text=f"👉 <b>PAY AMOUNT ACCORDING TO YOUR PLAN</b>\n\n📌 <b>UPI ID:</b> <code>{UPI_ID}</code>\n\n‼️ <b>MUST SEND SCREENSHOT AFTER PAYMENT</b>", reply_markup=screenshot_keyboard)

    elif query.data == "about":
        buttons = [[InlineKeyboardButton('Home', callback_data='start'), InlineKeyboardButton('🔒 Close', callback_data='close_data')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        text_content = script.ABOUT_TXT.format(me2)
        
        # 🔒 Lock Buttons & Show Transition Text First
        await show_text_transition(query)

        try:
            if start_photo:
                await query.message.edit_caption(caption=text_content, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            else:
                await query.message.edit_text(text=text_content, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        except Exception:
            try: await query.message.delete()
            except Exception: pass
            if start_photo:
                await client.send_photo(query.message.chat.id, photo=start_photo, caption=text_content, reply_markup=reply_markup, has_spoiler=is_spoiler)
            else:
                await client.send_message(query.message.chat.id, text=text_content, reply_markup=reply_markup)
    
    elif query.data == "start":
        buttons = [
            [InlineKeyboardButton('🔍 Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜヌ', url='https://t.me/pratilipifm0900'), InlineKeyboardButton('🤖 Sᴛᴏʀʏ Cʜᴀɴɴᴇʟ', url='https://t.me/freestoryhubMR')],
            [InlineKeyboardButton('💁‍♀️ Fᴇᴀᴛᴜʀᴇs', callback_data='help'), InlineKeyboardButton('😊 Aʙᴏᴜᴛ', callback_data='about')],
            [InlineKeyboardButton('⭐ ᗷᑌY ᑭᖇᗴᗰIᑌᗰ ⭐', callback_data='buy_premium_panel', style=enums.ButtonStyle.DANGER)],
            [InlineKeyboardButton('⁉️ SᴇᴛᴛɪɴGS ⁉️', callback_data='open_admin_from_start', style=enums.ButtonStyle.PRIMARY)]
        ]
        if CLONE_MODE:
            buttons.append([InlineKeyboardButton('🤖 create your own clone bot', callback_data='clone')])      
        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        text_content = start_caption.format(query.from_user.mention, me2)
        
        # 🔒 Lock Buttons & Show Transition Text First
        await show_text_transition(query)

        try:
            if start_photo:
                await query.message.edit_caption(caption=text_content, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            else:
                await query.message.edit_text(text=text_content, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        except Exception:
            try: await query.message.delete()
            except Exception: pass
            if start_photo:
                await client.send_photo(query.message.chat.id, photo=start_photo, caption=text_content, reply_markup=reply_markup, has_spoiler=is_spoiler)
            else:
                await client.send_message(query.message.chat.id, text=text_content, reply_markup=reply_markup)
    
    elif query.data == "clone":
        buttons = [[InlineKeyboardButton('Home', callback_data='start'), InlineKeyboardButton('🔒 Close', callback_data='close_data')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        text_content = script.CLONE_TXT.format(query.from_user.mention)
        
        # 🔒 Lock Buttons & Show Transition Text First
        await show_text_transition(query)

        try:
            if start_photo:
                await query.message.edit_caption(caption=text_content, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            else:
                await query.message.edit_text(text=text_content, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        except Exception:
            try: await query.message.delete()
            except Exception: pass
            if start_photo:
                await client.send_photo(query.message.chat.id, photo=start_photo, caption=text_content, reply_markup=reply_markup, has_spoiler=is_spoiler)
            else:
                await client.send_message(query.message.chat.id, text=text_content, reply_markup=reply_markup)
    
    elif query.data == "help":
        buttons = [[InlineKeyboardButton('Home', callback_data='start'), InlineKeyboardButton('🔒 Close', callback_data='close_data')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        text_content = script.HELP_TXT
        
        # 🔒 Lock Buttons & Show Transition Text First
        await show_text_transition(query)

        try:
            if start_photo:
                await query.message.edit_caption(caption=text_content, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            else:
                await query.message.edit_text(text=text_content, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        except Exception:
            try: await query.message.delete()
            except Exception: pass
            if start_photo:
                await client.send_photo(query.message.chat.id, photo=start_photo, caption=text_content, reply_markup=reply_markup, has_spoiler=is_spoiler)
            else:
                await client.send_message(query.message.chat.id, text=text_content, reply_markup=reply_markup)
