import os
import logging
import random
import asyncio
import re
import json
import base64
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

BATCH_FILES = {}
# Global tracking dictionary to terminate ongoing loops
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
    """Converts bytes to a human-readable format string."""
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def formate_file_name(file_name):
    """Cleans up formatting issues and appends the default channel handle."""
    if not file_name:
        return "Media File"
    chars = ["[", "]", "(", ")"]
    for c in chars:
        file_name = file_name.replace(c, "")
    file_name = '@HDFILM0900_BOT ' + ' '.join(filter(lambda x: not x.startswith('http') and not x.startswith('@') and not x.startswith('www.'), file_name.split()))
    return file_name


# --- BOT ROUTING ENGINE ---

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except Exception:
        try:
            await message.react(emoji="⚡️", big=True)
        except Exception:
            pass
            
    username = client.me.username
    user_id = message.from_user.id
    
    # Dynamic runtime setting collection
    settings = await db.get_settings()
    is_verify_mode = settings.get("verify_mode", True)
    is_protect = settings.get("protect_content", False)
    is_autodelete = settings.get("auto_delete_mode", True)
    del_time_seconds = settings.get("auto_delete_time", 1800)
    del_time_minutes = del_time_seconds // 60
    
    # Premium verification layer
    is_premium = await db.check_premium_status(user_id) if hasattr(db, 'check_premium_status') else False
    
    # Media & visual configuration elements
    start_photo = settings.get("start_photo", None)
    is_spoiler = settings.get("start_spoiler", False) 
    db_start_text = settings.get("custom_start_text", None)
    
    start_caption = db_start_text if db_start_text else script.START_TXT

    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT.format(user_id, message.from_user.mention))
    
    # Handling raw /start command without deep-link arguments
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
            [
                InlineKeyboardButton('⭐ Buy Premium ⭐', callback_data='buy_premium_panel')
            ],
            [
                InlineKeyboardButton('⁉️ Sᴇᴛᴛɪngs ⁉️', callback_data='open_admin_from_start')
            ]
        ]
        if CLONE_MODE:
            buttons.append([InlineKeyboardButton('🤖 ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴏᴡɴ ᴄʟᴏɴេ ʙᴏᴛ', callback_data='clone')])
            
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

    # Extract single deep-link parameter parsing routing logic
    data = message.command[1]
    
    # 1. Verification callback handling
    if data.split("-", 1)[0] == "verify":
        userid = data.split("-", 2)[1]
        token = data.split("-", 3)[2]
        if str(user_id) != str(userid):
            return await message.reply_text(text="<b>Invalid link or Expired link !</b>", protect_content=is_protect)
        
        is_valid = await check_token(client, userid, token)
        if is_valid:
            await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)
            await asyncio.sleep(1)
            
            success_msg = await message.reply_text(
                text=script.VERIFIED_SUCCESS_TXT.format(message.from_user.mention),
                protect_content=is_protect
            )
            asyncio.create_task(auto_delete_msg(success_msg, 300))
            await verify_user(client, userid, token)
        else:
            return await message.reply_text(text="<b>Invalid link or Expired link !</b>", protect_content=is_protect)
        return

    # 2. Gatekeeping check logic 
    try:
        is_user_premium = await db.check_premium_status(user_id) if hasattr(db, 'check_premium_status') else False
        if not is_user_premium and settings.get("premium_mode", False):
            buy_btn = InlineKeyboardMarkup([[InlineKeyboardButton("👑 Buy Premium", callback_data='buy_premium_panel')]])
            await message.reply_text(
                "👑 **यह फाइल प्रीमियम है!**\n\nइसे एक्सेस करने के लिए कृपया प्रीमियम लें।\n\n"
                "☂️ ᴛʜɪs ᴄᴏɴᴛᴇɴᴛ ɪs ᴘʀᴇᴍɪᴜᴍ ᴘʀᴏᴛᴇᴄᴛᴇᴅ,\n ᴏɴʟʏ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀ ᴄᴀɴ ᴀᴄᴄᴇss ᴛʜɪs ʟɪɴᴋ ᴄᴏɴᴛᴇɴᴛ.\n\n"
                "🔎 ᴄʟɪᴄᴋ ᴏɴ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ", 
                reply_markup=buy_btn
            )
            return 
        
        if not is_premium and is_verify_mode and not await check_verification(client, user_id):
            btn = [[
                InlineKeyboardButton("🌀 𝚅𝙴𝚁𝙸𝙵𝚈 🌀", url=await get_token(client, user_id, f"https://telegram.me/{username}?start=")),
                InlineKeyboardButton("⁉️ 𝚃𝚄𝚃𝙾𝚁𝙸𝙰𝙻 ⁉️", url=VERIFY_TUTORIAL)
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

    # 🌟 COMMON PLEASE WAIT MESSAGE FOR ALL FILE TYPES 🌟
    processing_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 DEVELOPER", url="https://t.me/HDFILM0900_BOT")],
        [InlineKeyboardButton("❌ CANCEL", callback_data=f"cancel_batch_{user_id}")]
    ])
    CANCEL_PROCESSING[user_id] = False
    sts = await message.reply(text="<b>🔺 𝙿𝙻𝙴𝙰𝚂𝙴 𝚆ait</b>", reply_markup=processing_keyboard)

    # 3. DB Base64 Hash Processing System
    try:
        decoded_bytes = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
        decoded_str = decoded_bytes.decode("ascii")
        
        if "file_" in decoded_str:
            decode_file_id = decoded_str.replace("file_", "")
        else:
            decode_file_id = decoded_str.split("_", 1)[1] if "_" in decoded_str else decoded_str
            
        msg = await client.get_messages(DB_CHANNEL, int(decode_file_id))
        
        # --- BATCH FILE ROUTE ---
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
                    await sts.edit("<b>❌ Batch Processing Cancelled By User!</b>")
                    await asyncio.sleep(3)
                    await sts.delete()
                    if user_id in CANCEL_PROCESSING:
                        del CANCEL_PROCESSING[user_id]
                    return

                try:
                    channel_id = int(msg_item.get("channel_id"))
                    msgid = int(msg_item.get("msg_id"))
                    info = await client.get_messages(channel_id, msgid)
                    
                    if info.empty or info.service:
                        continue
                        
                    if info.media:
                        file_type = info.media
                        file = getattr(info, file_type.value)
                        f_caption = getattr(info, 'caption', '')
                        if f_caption:
                            f_caption = f"@HDFILM0900_BOT {f_caption.html}"
                        old_title = getattr(file, "file_name", "Media File")
                        title = formate_file_name(old_title)
                        
                        size = get_size(int(file.file_size)) if hasattr(file, "file_size") else "Unknown"
                        if BATCH_FILE_CAPTION:
                            try:
                                f_caption = BATCH_FILE_CAPTION.format(
                                    file_name='' if title is None else title, 
                                    file_size='' if size is None else size, 
                                    file_caption='' if f_caption is None else f_caption
                                )
                            except Exception:
                                pass
                        if f_caption is None:
                            f_caption = f"@HDFILM0900_BOT {title}"
                            
                        if STREAM_MODE and (info.video or info.document):
                            stream = f"{URL}watch/{str(info.id)}/{quote_plus(get_name(info))}?hash={get_hash(info)}"
                            download = f"{URL}{str(info.id)}/{quote_plus(get_name(info))}?hash={get_hash(info)}"
                            button = [
                                [
                                    InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download),
                                    InlineKeyboardButton('• ᴡᴀᴛᴄʜ •', url=stream)
                                ],
                                [
                                    InlineKeyboardButton("• ᴡᴀᴛᴄʜ ɪn ᴡᴇʙ ᴀᴘᴘ •", web_app=WebAppInfo(url=stream))
                                ]
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
                except Exception as e:
                    logger.error(f"Error copying batch sub-file: {e}")
                    continue
                    
            await sts.delete()
            
            if user_id in CANCEL_PROCESSING:
                del CANCEL_PROCESSING[user_id]
            
            if is_autodelete:
                k = await client.send_message(
                    chat_id=user_id, 
                    text=f"<b><u>...IMPORTANT...</u></b>\n\nThis Movie File/Video will be deleted in <b><u>{del_time_minutes} minutes</u> ... <i></b>(Due to Copyright Issues)</i>.\n\n<b><i>Please forward this File/Video to your Saved Messages and Start Download there</b>"
                )
                await asyncio.sleep(del_time_seconds)
                for x in filesarr:
                    try:
                        await x.delete()
                    except Exception:
                        pass
                try:
                    await k.edit_text("<b>Your All Files/Videos is successfully deleted!!!</b>")
                except Exception:
                    pass
            return

        # --- SINGLE FILE ROUTE ---
        else:
            if CANCEL_PROCESSING.get(user_id, False):
                await sts.edit("<b>❌ Request Cancelled By User!</b>")
                await asyncio.sleep(3)
                await sts.delete()
                return

            if msg.media:
                media = getattr(msg, msg.media.value)
                old_title = media.file_name if hasattr(media, "file_name") else "Photo File"
                title = formate_file_name(old_title)
                size = get_size(media.file_size) if hasattr(media, "file_size") else "Unknown"
                
                f_caption = f"@HDFILM0900_BOT <code>{title}</code>"
                if CUSTOM_FILE_CAPTION:
                    try:
                        f_caption = CUSTOM_FILE_CAPTION.format(
                            file_name='' if title is None else title, 
                            file_size='' if size is None else size, 
                            file_caption=''
                        )
                    except Exception:
                        pass
                
                if STREAM_MODE and (msg.video or msg.document):
                    log_msg = msg
                    stream = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    download = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    button = [
                        [
                            InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download),
                            InlineKeyboardButton('• ᴡᴀᴛᴄʜ •', url=stream)
                        ],
                        [
                            InlineKeyboardButton("• ᴡᴀᴛᴄʜ ɪＮ ᴡᴇʙ ᴀᴘᴘ •", web_app=WebAppInfo(url=stream))
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(button)
                else:
                    reply_markup = None
                    
                await client.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_DOCUMENT)
                await asyncio.sleep(1) 
                
                del_msg = await msg.copy(chat_id=user_id, caption=f_caption, reply_markup=reply_markup, protect_content=is_protect)
            else:
                await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)
                del_msg = await msg.copy(chat_id=user_id, protect_content=is_protect)
                
            # Deleting the "Please wait" status message once the single file has successfully landed.
            await sts.delete()

            if is_autodelete:
                k = await client.send_message(
                    chat_id=user_id, 
                    text=f"<b><u>...IMPORTANT...</u></b>\n\nThis Movie File/Video will be deleted in <b><u>{del_time_minutes} minutes</u> ... <i></b>(Due to Copyright Issues)</i>.\n\n<b><i>Please forward this File/Video to your Saved Messages and Start Download there</b>"
                )
                await asyncio.sleep(del_time_seconds)
                try:
                    await del_msg.delete()
                except Exception:
                    pass
                try:
                    await k.edit_text("<b>Your File/Video is successfully deleted!!!</b>")
                except Exception:
                    pass
            return
            
    except Exception as e:
        logger.error(f"Error in file delivery route: {str(e)}")
        try:
            await sts.delete()
        except Exception:
            pass

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

# --- INTERACTIVE CALLBACKS ---

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    settings = await db.get_settings()
    start_photo = settings.get("start_photo", None)
    is_spoiler = settings.get("start_spoiler", False)
    db_start_text = settings.get("custom_start_text", None)
    start_caption = db_start_text if db_start_text else script.START_TXT

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
            [
                InlineKeyboardButton("📊 Qʀ Code", callback_data="show_premium_qr"),
                InlineKeyboardButton("💳 Uᴘɪ ID", callback_data="show_premium_upi")
            ],
            [InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data="start")]
        ])
        await query.message.edit_text(text=PREMIUM_PLANS_TEXT, reply_markup=premium_keyboard)

    elif query.data == "show_premium_qr":
        screenshot_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Sᴇɴᴅ Pᴀʏᴍᴇɴᴛ Sᴄʀᴇᴇɴsʜᴏᴛ", url=f"https://t.me/HDFILM0900_BOT")], # Yahan admin ya support handle ka link daal sakte hain
            [InlineKeyboardButton("❌ Close ❌", callback_data='close_data')]
        ])
        await query.message.reply_photo(
            photo=QR_IMAGE_URL,
            caption=f"⚡ <b>PAY AMOUNT ACCORDING TO YOUR PLAN AND ENJOY PREMIUM MEMBERSHIP !</b>\n\n‼️ <b>MUST SEND SCREENSHOT AFTER PAYMENT</b>\nपेमेंट होने के बाद हमें स्क्रीनशॉट भेजें।",
            reply_markup=screenshot_keyboard
        )
        await query.answer() 

    elif query.data == "show_premium_upi":
        screenshot_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Sᴇɴᴅ Pᴀʏᴍᴇɴᴛ Sᴄʀᴇᴇɴsʜᴏᴛ", url=f"https://t.me/HDFILM0900_BOT")],
            [InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data="buy_premium_panel")]
        ])
        await query.message.edit_text(
            text=f"👉 <b>PAY AMOUNT ACCORDING TO YOUR PLAN</b>\n\n📌 <b>UPI ID:</b> <code>{UPI_ID}</code> (Tap to copy)\n\n‼️ <b>MUST SEND SCREENSHOT AFTER PAYMENT</b>\nपेमेंट होने के बाद हमें स्क्रीनशॉट भेजें।",
            reply_markup=screenshot_keyboard
        )

    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        if start_photo:
            try:
                await client.edit_message_media(
                    query.message.chat.id, 
                    query.message.id, 
                    InputMediaPhoto(start_photo, has_spoiler=is_spoiler) 
                )
            except Exception:
                pass
        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(me2),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    
    elif query.data == "start":
        buttons = [
            [
                InlineKeyboardButton('🔍 Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url='https://t.me/pratilipifm0900'),
                InlineKeyboardButton('🤖 Sᴛᴏʀʏ Cʜᴀɴɴᴇʟ', url='https://t.me/freestoryhubMR')
            ],
            [
                InlineKeyboardButton('💁‍♀️ Fᴇᴀᴛᴜʀᴇs', callback_data='help'),
                InlineKeyboardButton('😊 Aʙᴏᴜᴛ', callback_data='about')
            ],
            [
                InlineKeyboardButton('⭐ Buy Premium ⭐', callback_data='buy_premium_panel')
            ],
            [
                InlineKeyboardButton('⁉️ Sᴇᴛᴛings ⁉️', callback_data='open_admin_from_start')
            ]
        ]
        if CLONE_MODE:
            buttons.append([InlineKeyboardButton('🤖 ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')])      
        reply_markup = InlineKeyboardMarkup(buttons)
        
        if start_photo:
            try:
                await client.edit_message_media(
                    query.message.chat.id, 
                    query.message.id, 
                    InputMediaPhoto(start_photo, has_spoiler=is_spoiler) 
                )
            except Exception:
                pass
        me2 = (await client.get_me()).mention
        await query.message.edit_text(
            text=start_caption.format(query.from_user.mention, me2),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    
    elif query.data == "clone":
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        if start_photo:
            try:
                await client.edit_message_media(
                    query.message.chat.id, 
                    query.message.id, 
                    InputMediaPhoto(start_photo, has_spoiler=is_spoiler) 
                )
            except Exception:
                pass
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CLONE_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )          
    
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        if start_photo:
            try:
                await client.edit_message_media(
                    query.message.chat.id, 
                    query.message.id, 
                    InputMediaPhoto(start_photo, has_spoiler=is_spoiler) 
                )
            except Exception:
                pass
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
