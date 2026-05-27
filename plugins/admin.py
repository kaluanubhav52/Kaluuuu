import asyncio
import re
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS
from plugins.dbusers import db  # Explicit import to avoid namespace issues
from utils import *
import pytz
import time
from datetime import datetime

logger = logging.getLogger(__name__)

ADMIN_STATE = {}

def is_valid_domain(domain):
    pattern = r"^(?!:\/\/)([a-zA-Z0-9-_]+\.)*[a-zA-Z0-9][a-zA-Z0-9-_]+\.[a-zA-Z]{2,11}$"
    return bool(re.match(pattern, domain.strip()))

def is_valid_api(api):
    api_clean = api.strip()
    if " " in api_clean or len(api_clean) < 8:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_\-]+$", api_clean))

async def auto_delete_message(msg, delay=120):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass

TEMP_BACK_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("≤ ʙᴀᴄᴋ", callback_data="adm_temp_back")]])

async def get_main_panel_layout(settings):
    p_status = "🟢 ᴏɴ" if settings.get("protect_content", False) else "🔴 ᴏғғ"
    text = (
        "⚡ **ʜᴇʀᴇ ɪs ᴛʜᴇ sᴇᴛᴛɪɴɢs ᴍᴇɴᴜ** ⚡\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "ᴄᴜsᴛᴏᴍɪᴢᴇ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ᴀs ᴘᴇʀ ʏᴏᴜʀ ɴᴇᴇᴅ.\n"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴍᴇɴᴜ", callback_data="adm_sub_verify")],
        [InlineKeyboardButton("⏱️ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴍᴇɴᴜ", callback_data="adm_sub_delete")],
        [InlineKeyboardButton("🎨 sᴛᴀʀᴛ ᴍᴇɴᴜ", callback_data="adm_sub_start_page")],
        [InlineKeyboardButton("👑 ᴘʀᴇᴍɪᴜᴍ ᴍᴇɴᴜ", callback_data="adm_sub_premium")],
        [InlineKeyboardButton(f"🛡️ ᴘʀᴏᴛᴇᴄᴛ ᴄᴏɴᴛᴇɴᴛ: {p_status}", callback_data="adm_toggle_protect")],
        [InlineKeyboardButton("ʜᴏᴍᴇ", callback_data='start')]
    ])
    return text, keyboard

# 🔥 UPDATED: Added Live Token Progress Bar Logic Inside Verification Layout
async def get_verify_menu_layout(settings):
    v_status = "🟢 ᴏɴ" if settings.get("verify_mode", True) else "🔴 ᴏғғ"
    prem_mode_status = "🟢 ᴏɴ" if settings.get("premium_mode", False) else "🔴 ᴏғғ"
    v_expire_hours = settings.get("verify_expire_time", 86400) // 3600
    
    # 📊 Live Token Progress Bar Settings
    try:
        today_tokens = await db.get_today_tokens()
    except Exception:
        today_tokens = 0
        
    daily_target = 1000  # Aap apna target change kar sakte ho (e.g. 500, 1000, 2000)
    percentage = min(int((today_tokens / daily_target) * 100), 100)
    
    # Custom Progress Bar Build
    bar_length = 10
    filled_length = int(bar_length * percentage // 100)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    text = (
        "🔐 **ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴛᴏᴋᴇɴ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ sᴇᴛᴛɪɴɢs**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ *Nᴏᴛᴇ: Oɴʟʏ ᴏɴᴇ ᴍᴏᴅᴇ ᴄᴀɴ ʀᴜɴ ᴀᴛ ᴀ ᴛɪᴍᴇ, ᴇɪᴛʜᴇʀ Vᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴏʀ Pʀᴇᴍɪᴜᴍ Mᴏᴅᴇ.*\n\n"
        f"🔗 **Sʜᴏʀᴛᴇɴᴇʀ Sɪᴛᴇ:** `{settings.get('shortlink_url')}`\n"
        f"🔑 **Sʜᴏʀᴛᴇɴᴇʀ API:** `{settings.get('shortlink_api')}`\n"
        f"⏱️ **Tᴏᴋᴇɴ Vᴀʟɪᴅɪᴛʏ:** `{v_expire_hours} Hᴏᴜʀs`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **ᴛᴏᴅᴀʏ's ʟɪᴠᴇ ᴛᴏᴋᴇɴs:** `{today_tokens}/{daily_target}`\n"
        f"📈 **ᴘʀᴏɢʀᴇss:** `[{bar}] {percentage}%`"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴍᴏᴅᴇ: {v_status}", callback_data="adm_toggle_verify")],
        [InlineKeyboardButton(f"ᴘʀᴇᴍɪᴜᴍ ᴍᴏᴅᴇ: {prem_mode_status}", callback_data="adm_toggle_premium_mode")],
        [InlineKeyboardButton("sᴇᴛ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ 🔑", callback_data="adm_set_token_time")],
        [InlineKeyboardButton("sᴇᴛ sʜᴏʀᴛᴇɴᴇʀ ᴀᴘɪ ɪᴅ 🔗", callback_data="adm_change_link")],
        [InlineKeyboardButton("🔄 ʀᴇғʀᴇsʜ sᴛᴀᴛs", callback_data="adm_sub_verify")],  # Loop response refresh key
        [InlineKeyboardButton("ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="adm_back_main")]
    ])
    return text, keyboard

async def get_delete_menu_layout(settings):
    d_status = "🟢 ᴏɴ" if settings.get("auto_delete_mode", True) else "🔴 ᴏғғ"
    del_time = settings.get("auto_delete_time", 1800) // 60
    text = (
        "⏱️ **ʜᴇʀᴇ ʏᴏᴜ ᴄᴀɴ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ʙᴏᴛ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ sᴇᴛᴛɪɴɢ.**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ **ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ:** `{del_time} Mɪɴᴜᴛᴇs`"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴍᴏᴅᴇ: {d_status}", callback_data="adm_toggle_delete")],
        [InlineKeyboardButton("sᴇᴛ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ ⏱️", callback_data="adm_set_time")],
        [InlineKeyboardButton("ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="adm_back_main")]
    ])
    return text, keyboard

async def get_start_page_menu_layout(settings):
    has_text = "🟢 ᴄᴜsᴛᴏᴍ ᴛᴇxᴛ ᴇɴᴀʙʟᴇᴅ" if settings.get("custom_start_text") else "⚪ ᴅᴇғᴀᴜʟᴛ ᴛᴇxᴛ ᴇɴᴀʙʟᴇᴅ"
    s_status = "🟢 ᴏɴ (ʙʟᴜʀʀᴇᴅ ɪᴍᴀɢᴇ)" if settings.get("start_spoiler", False) else "🔴 ᴏғғ (ᴄʟᴇᴀʀ ɪᴍᴀɢᴇ)"
    text = (
        "🎨 **sᴛᴀʀᴛ ᴘᴀɢᴇ ᴄᴏɴғɪɢᴜʀᴀᴛɪᴏɴ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🖼️ **Sᴛᴀʀᴛ Pʜᴏᴛᴏ Sᴛᴀᴛᴜs:** `{settings.get('start_photo', 'Nᴏɴᴇ')}`\n"
        f"📝 **Sᴛᴀʀᴛ Tᴇxᴛ Sᴛᴀᴛᴜs:** `{has_text}`\n"
        f"⚠️ **Sᴘᴏɪʟᴇʀ Sᴛᴀᴛᴜs:** `{s_status}`"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ sᴇᴛ sᴛᴀʀᴛ ᴛᴇxᴛ", callback_data="adm_set_start_txt")], 
        [InlineKeyboardButton("🗑️ ʀᴇsᴇᴛ sᴛᴀʀᴛ ᴛᴇxᴛ", callback_data="adm_reset_start_txt")],
        [InlineKeyboardButton("🖼️ sᴇᴛ sᴛᴀʀᴛ ᴘʜᴏᴛᴏ (ᴜʀʟ)", callback_data="adm_set_start_img")], 
        [InlineKeyboardButton("🗑️ ʀᴇᴍᴏᴠᴇ sᴛᴀʀᴛ ᴘʜᴏᴛᴏ", callback_data="adm_remove_start_img")],
        [InlineKeyboardButton(f"🎭 sᴘᴏɪʟᴇʀ ᴍᴏᴅᴇ: {'🟢 ᴏɴ' if settings.get('start_spoiler', False) else '🔴 ᴏғғ'}", callback_data="adm_toggle_spoiler")],
        [InlineKeyboardButton("ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="adm_back_main")]
    ])
    return text, keyboard

async def get_premium_menu_layout(settings):
    try:
        users_list = await db.get_all_premium_users()
        total_premium = len(users_list)
    except Exception:
        total_premium = 0
    current_buy_link = settings.get("premium_buy_link", "https://t.me/HDFILM0900_BOT")
    text = (
        "👑 **ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀ ᴄᴏɴғɪɢᴜʀᴀᴛɪᴏɴ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 **Tᴏᴛᴀʟ Pʀᴇᴍɪᴜᴍ Usᴇʀs:** `{total_premium}`\n"
        f"🔗 **Cᴜʀʀᴇɴᴛ Bᴜʏ Lɪɴᴋ:** `{current_buy_link}`"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ ᴀᴅᴅ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs", callback_data="adm_add_prem")],
        [InlineKeyboardButton("🗑️ ʀᴇᴍᴏᴠᴇ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs", callback_data="adm_rem_prem")],
        [InlineKeyboardButton("📜 ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs ʟɪsᴛ", callback_data="adm_list_prem")],
        [InlineKeyboardButton("🔘 sᴇᴛ ᴘʀᴇᴍɪᴜᴍ ʙᴜᴛᴛᴏɴ ʟɪɴᴋ", callback_data="adm_set_buy_link")],
        [InlineKeyboardButton("ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="adm_back_main")]
    ])
    return text, keyboard

@Client.on_message(filters.command("settings") & filters.user(ADMINS))
async def admin_panel(client, message):
    settings = await db.get_settings()
    text, keyboard = await get_main_panel_layout(settings)
    await message.reply_text(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("open_admin_from_start"))
async def open_admin_from_start(client, query):
    if query.from_user.id not in ADMINS:
        await query.answer("🚫 ᴏɴʟʏ ғᴏʀ ʙᴏᴛ ᴏᴡɴᴇʀ!", show_alert=True)
        return
    settings = await db.get_settings()
    text, keyboard = await get_main_panel_layout(settings)
    keyboard.inline_keyboard[-1] = [InlineKeyboardButton("ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="start")]
    try:
        await query.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await query.message.reply_text(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex(r"^adm_"))
async def admin_callback(client, query):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ!", show_alert=True)
        return

    action = query.data.replace("adm_", "")
    settings = await db.get_settings()
    chat_id = query.message.chat.id
    
    if action == "back_main":
        text, keyboard = await get_main_panel_layout(settings)
        if "🔙 Back to Home" in str(query.message.reply_markup):
            keyboard.inline_keyboard[-1] = [InlineKeyboardButton("🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ", callback_data="start")]
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=keyboard)
        return
    elif action == "sub_verify":
        text, keyboard = await get_verify_menu_layout(settings)
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=keyboard)
        return
    elif action == "sub_delete":
        text, keyboard = await get_delete_menu_layout(settings)
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=keyboard)
        return
    elif action == "sub_start_page":
        text, keyboard = await get_start_page_menu_layout(settings)
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=keyboard)
        return
    elif action == "sub_premium":
        text, keyboard = await get_premium_menu_layout(settings)
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=keyboard)
        return
    elif action == "temp_back":
        try:
            await query.message.delete()
        except Exception:
            pass
        text, keyboard = await get_main_panel_layout(settings)
        await client.send_message(chat_id, text, reply_markup=keyboard)
        return

    elif action == "toggle_verify":
        new_val = not settings.get("verify_mode", True)
        await db.update_setting("verify_mode", new_val)
        if new_val == True:
            await db.update_setting("premium_mode", False)
            await query.answer("ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴍᴏᴅᴇ ᴏɴ & ᴘʀᴇᴍɪᴜᴍ ᴍᴏᴅᴇ ᴏғғ! 🔄", show_alert=True)
        else:
            await query.answer("ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴍᴏᴅᴇ ᴜᴘᴅᴀᴛᴇᴅ! ✅")
        settings = await db.get_settings()
        text, keyboard = await get_verify_menu_layout(settings)
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=keyboard)

    elif action == "toggle_premium_mode":
        new_val = not settings.get("premium_mode", False)
        await db.update_setting("premium_mode", new_val)
        if new_val == True:
            await db.update_setting("verify_mode", False)
            await query.answer("ᴘʀᴇᴍɪᴜᴍ ᴍᴏᴅᴇ ᴏɴ & ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴏғғ! 👑", show_alert=True)
        else:
            await query.answer("ᴘʀᴇᴍɪᴜᴍ ᴍᴏᴅᴇ ᴜᴘᴅᴀᴛᴇᴅ! ✅")
        settings = await db.get_settings()
        text, keyboard = await get_verify_menu_layout(settings)
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=keyboard)
        
    elif action == "toggle_delete":
        new_val = not settings.get("auto_delete_mode", True)
        await db.update_setting("auto_delete_mode", new_val)
        await query.answer("ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴍᴏᴅᴇ ᴜᴘᴅᴀᴛᴇᴅ! ✅")
        settings = await db.get_settings()
        text, keyboard = await get_delete_menu_layout(settings)
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=keyboard)
        
    elif action == "toggle_protect":
        new_val = not settings.get("protect_content", False)
        await db.update_setting("protect_content", new_val)
        await query.answer("ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ ᴜᴘᴅᴀᴛᴇᴅ! ✅")
        settings = await db.get_settings()
        text, keyboard = await get_main_panel_layout(settings)
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=keyboard)

    elif action == "toggle_spoiler":
        new_val = not settings.get("start_spoiler", False)
        await db.update_setting("start_spoiler", new_val)
        await query.answer(f"sᴘᴏɪʟᴇʀ ᴍᴏᴅᴇ {'ᴇɴᴀʙʟᴇᴅ 🟢' if new_val else 'ᴅɪsᴀʙʟᴇdisabled 🔴'}")
        settings = await db.get_settings()
        text, keyboard = await get_start_page_menu_layout(settings)
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=keyboard)

    elif action == "reset_start_txt":
        await db.update_setting("custom_start_text", None) 
        await query.answer("sᴛᴀʀᴛ ᴍᴇssᴀɢᴇ ʀᴇsᴇᴛ ᴛᴏ ᴅᴇғᴀᴜʟᴛ ᴛᴇxᴛ! ⚪", show_alert=True)
        settings = await db.get_settings()
        text, keyboard = await get_start_page_menu_layout(settings)
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=keyboard)

    elif action == "remove_start_img":
        await db.update_setting("start_photo", None) 
        await query.answer("sᴛᴀʀᴛ ɪᴍᴀɢᴇ sᴜᴄᴄᴇssғᴜʟʟʏ ʀᴇᴍᴏᴠᴇᴅ! 🗑️", show_alert=True)
        settings = await db.get_settings()
        text, keyboard = await get_start_page_menu_layout(settings)
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=keyboard)

    elif action == "list_prem":
        try:
            users = await db.get_all_premium_users_with_time()
        except Exception:
            users = []
        if not users:
            list_text = "ℹ️ **ᴛʜᴇ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀ ʟɪsᴛ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴇᴍᴘᴛʏ!**"
        else:
            list_text = "📜 **ᴄᴜʀʀᴇɴᴛ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs ʟɪsᴛ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            current_time = datetime.utcnow()
            for idx, user in enumerate(users, start=1):
                u_id = user["id"]
                expire_at = user["expire_at"]
                
                time_left = expire_at - current_time
                days = time_left.days
                hours = time_left.seconds // 3600
                
                time_str = ""
                if days > 0:
                    time_str += f"{days}ᴅ "
                if hours > 0 or days == 0:
                    time_str += f"{hours}ʜ"
                if days <= 0 and hours <= 0:
                    time_str = "ᴇxᴘɪʀɪɴɢ sᴏᴏɴ"

                list_text += f"{idx}. 👤 ɪᴅ: <code>{u_id}</code> | ⏱️ ᴛɪᴍᴇ: `({time_str.strip()})`\n"

        back_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="adm_sub_premium")]])
        try:
            await query.message.edit_text(text=list_text, reply_markup=back_keyboard)
        except Exception:
            await client.send_message(chat_id, text=list_text, reply_markup=back_keyboard)

    elif action in ["add_prem", "rem_prem", "set_buy_link", "set_start_txt", "set_start_img", "set_time", "set_token_time", "change_link"]:
        await query.answer() 
        try:
            await query.message.delete()
        except Exception:
            pass
        
        prompt_text = ""
        step = ""
        
        if action == "add_prem":
            prompt_text = "👑 **[sᴛᴇᴘ 1/3] sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀ's ᴜɪᴅ (ᴛᴇʟᴇɢʀᴀᴍ ɪᴅ):**\n\n*(ᴏɴʟʏ ɴᴜᴍʙᴇʀs ᴀʟʟᴏᴡᴇᴅ. ᴛʏᴘᴇ /cancel ᴛᴏ ᴄᴀɴᴄᴇʟ)*"
            step = "add_prem_id"
        elif action == "rem_prem":
            prompt_text = "🗑️ **sᴇɴᴅ ᴛʜᴇ ᴜsᴇʀ's ᴜɪᴅ ᴛᴏ ʀᴇᴍᴏᴠᴇ ғʀᴏᴍ ᴘʀᴇᴍɪᴜᴍ:**\n\n*(ᴛʏᴘᴇ /cancel ᴛᴏ ᴄᴀɴᴄᴇʟ)*"
            step = "rem_prem_id"
        elif action == "set_buy_link":
            prompt_text = "🔗 **sᴇɴᴅ ᴛʜᴇ ᴘʀᴇᴍɪᴜᴍ ᴘᴜʀᴄʜᴀsᴇ ʟɪɴᴋ ғᴏʀ ᴜsᴇʀs:**\n*(ᴇx: `https://t.me/your_username`)*\n\n*(ᴛʏᴘᴇ /cancel ᴛᴏ ᴄᴀɴᴄᴇʟ)*"
            step = "set_buy_link"
        elif action == "set_start_txt":
            prompt_text = "✍️ **sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ /start ᴍᴇssᴀɢᴇ ᴛᴇxᴛ:**\n*(ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ʜᴛᴍʟ/ᴍᴀʀᴋᴅᴏᴡɴ ᴛᴀɢs)*\n\n*(ᴛʏᴘᴇ /cancel ᴛᴏ ᴄᴀɴᴄᴇʟ)*"
            step = "set_start_txt"
        elif action == "set_start_img":
            prompt_text = "🖼️ **sᴇɴᴅ ᴛʜᴇ ᴜʀʟ (ʟɪɴᴋ) ᴏғ ᴛʜᴇ ɴᴇᴡ sᴛᴀʀᴛ ᴘʜᴏᴛᴏ:**\n*(ᴇxᴀᴍᴘʟᴇ: `https://site.com/image.png`)*\n\n*(ᴛʏᴘᴇ /cancel ᴛᴏ ᴄᴀɴᴄᴇʟ)*"
            step = "set_start_img"
        elif action == "set_time":
            prompt_text = "⏱️ **sᴇɴᴅ ᴛʜᴇ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ ɪɴ ᴍɪɴᴜᴛᴇs:**\n\n*(ᴛʏᴘᴇ /cancel ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜᴇ ᴘʀᴏᴄᴇss)*"
            step = "set_delete_time"
        elif action == "set_token_time":
            prompt_text = "🔑 **sᴇɴᴅ ᴛʜᴇ ᴛᴏᴋᴇɴ ᴠᴀʟɪᴅɪᴛʏ ᴛɪᴍᴇ ɪɴ ʜᴏᴜʀs:**\n\n*(ᴛʏᴘᴇ /cancel ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜᴇ ᴘʀᴏᴄᴇss)*"
            step = "set_token_time"
        elif action == "change_link":
            prompt_text = "🔗 **sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ sʜᴏʀᴛᴇɴᴇʀ ᴅᴏᴍᴀɪɴ ɴᴀᴍᴇ:**\n*(ᴇxᴀᴍᴘʟᴇ: `site.com`)*\n\n*(ᴛʏᴘᴇ /cancel ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜᴇ ᴘʀᴏᴄᴇss)*"
            step = "set_shortener_domain"

        ask_msg = await client.send_message(chat_id, prompt_text)
        ADMIN_STATE[chat_id] = {"step": step, "bot_msg_id": ask_msg.id}

@Client.on_message(filters.private & filters.text & filters.user(ADMINS), group=1)
async def admin_state_listener(client: Client, message):
    chat_id = message.from_user.id
    if chat_id not in ADMIN_STATE:
        return
    state = ADMIN_STATE[chat_id]
    step = state.get("step")
    if not step:
        del ADMIN_STATE[chat_id]
        return
    try:
        await message.delete()
    except Exception:
        pass
    if "bot_msg_id" in state:
        try:
            await client.delete_messages(chat_id, state["bot_msg_id"])
        except Exception:
            pass

    text = message.text.strip()

    if text == "/cancel":
        del ADMIN_STATE[chat_id]
        cancel_msg = await message.reply("** ᴄᴀɴᴄᴇʟʟᴇᴅ ᴛʜɪs ᴘʀᴏᴄᴇss...**", reply_markup=TEMP_BACK_BTN)
        asyncio.create_task(auto_delete_message(cancel_msg, 120))
        return

    if step == "add_prem_id":
        if not text.isdigit():
            err_msg = await message.reply("❌ **ɪɴᴠᴀʟɪᴅ ғᴏʀᴍᴀᴛ!** ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ɴᴜᴍᴇʀɪᴄᴀʟ ᴛᴇʟᴇɢʀᴀᴍ ɪᴅ (ᴄᴀɴᴄᴇʟ: /cancel).")
            ADMIN_STATE[chat_id]["bot_msg_id"] = err_msg.id
            return
        target_id = int(text)
        ADMIN_STATE[chat_id]["target_id"] = target_id
        ADMIN_STATE[chat_id]["step"] = "add_prem_days"
        ask_msg = await message.reply(f"⏱️ **[sᴛᴇᴘ 2/3] ʜᴏᴡ ᴍᴀɴʏ ᴅᴀʏs ᴏғ ᴘʀᴇᴍɪᴜᴍ sʜᴏᴜʟʙ ʙᴇ ɢɪᴠᴇɴ ᴛᴏ ᴜsᴇʀ `{target_id}`?**\n*(ᴇx: 30, 0 for hours)*")
        ADMIN_STATE[chat_id]["bot_msg_id"] = ask_msg.id

    elif step == "add_prem_days":
        if not text.isdigit() or int(text) < 0:
            err_msg = await message.reply("❌ **ɪɴᴠᴀʟɪᴅ ᴅᴀʏs!** ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ.")
            ADMIN_STATE[chat_id]["bot_msg_id"] = err_msg.id
            return
        ADMIN_STATE[chat_id]["days"] = int(text)
        ADMIN_STATE[chat_id]["step"] = "add_prem_hours"
        ask_msg = await message.reply(f"⏱️ **[sᴛᴇᴘ 3/3] ʜᴏᴡ ᴍᴀɴʏ ᴇxᴛʀᴀ ʜᴏᴜʀs (ɢʜᴀɴᴛᴇ) sʜᴏᴜʟᴅ ʙᴇ ɢɪᴠᴇɴ?**\n*(ᴇx: 6, 0 for days only)*")
        ADMIN_STATE[chat_id]["bot_msg_id"] = ask_msg.id

    elif step == "add_prem_hours":
        if not text.isdigit() or int(text) < 0:
            err_msg = await message.reply("❌ **ɪɴᴠᴀʟɪᴅ ʜᴏᴜʀs!** ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ.")
            ADMIN_STATE[chat_id]["bot_msg_id"] = err_msg.id
            return
        premium_hours = int(text)
        premium_days = ADMIN_STATE[chat_id].get("days", 0)
        target_id = ADMIN_STATE[chat_id].get("target_id")
        del ADMIN_STATE[chat_id] 
        if not target_id:
            await message.reply("❌ **sᴛᴀᴛᴇ ʟᴏsᴛ ᴅᴜᴇ ᴛᴏ ᴄᴀᴄʜᴇ ᴄʟᴇᴀʀ!** Restart process using /settings.", reply_markup=TEMP_BACK_BTN)
            return
        if premium_days == 0 and premium_hours == 0:
            err_msg = await message.reply("❌ **ʙᴏᴛʜ ᴅᴀʏs ᴀɴᴅ ʜᴏᴜʀs ᴄᴀɴɴᴏᴛ ʙᴇ ᴢᴇʀᴏ!** process cancelled.", reply_markup=TEMP_BACK_BTN)
            asyncio.create_task(auto_delete_message(err_msg, 120))
            return

        expiry_date = await db.add_premium_user(target_id, days=premium_days, hours=premium_hours)
        ist_timezone = pytz.timezone('Asia/Kolkata')
        ist_expiry = expiry_date.replace(tzinfo=pytz.utc).astimezone(ist_timezone)
        formatted_expiry = ist_expiry.strftime('%Y-%m-%d %H:%M IST')
        duration_str = ""
        if premium_days > 0: duration_str += f"{premium_days} ᴅᴀʏs "
        if premium_hours > 0: duration_str += f"{premium_hours} ʜᴏᴜʀs"
        success_text = f"**ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ᴀᴅᴅᴇᴅ ᴛᴏ ᴛʜᴇ ᴜsᴇʀ ᴡɪᴛʜ ɪᴅ -\n<code>{target_id}</code> for {duration_str.strip()}.**"
        success_msg = await message.reply(success_text, reply_markup=TEMP_BACK_BTN)
        asyncio.create_task(auto_delete_message(success_msg, 120))
        try:
            await client.send_message(
                target_id, 
                f"🎉 **ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs !!**\n"
                f"ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ʜᴀs ʙᴇᴇɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ᴡɪᴛʜ **👑 ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss** ғᴏʀ **{duration_str.strip()}**!\n"
                f"📅 **ᴇxᴘɪʀʏ ᴅᴀᴛᴇ:** `{formatted_expiry}`"
            )
        except Exception as e: logger.error(f"Failed to notify user {target_id}: {e}")

    elif step == "rem_prem_id":
        if not text.isdigit():
            err_msg = await message.reply("❌ **ɪɴᴠᴀʟɪᴅ ғᴏʀᴍᴀᴛ!** ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ɴᴜᴍᴇʀɪᴄᴀʟ ᴛᴇʟᴇɢʀᴀᴍ ɪᴅ.")
            ADMIN_STATE[chat_id]["bot_msg_id"] = err_msg.id
            return
        target_id = int(text)
        del ADMIN_STATE[chat_id]
        is_removed = await db.remove_premium_user(target_id)
        if is_removed:
            success_msg = await message.reply(f"**ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ʀᴇᴍᴏᴠᴇᴅ ғᴏʀ ᴜsᴇʀ ɪᴅ -\n{target_id}.**", reply_markup=TEMP_BACK_BTN)
            try: await client.send_message(target_id, "⚠️ **ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ ᴇxᴘɪʀᴇᴅ / ʀᴇᴍᴏᴠᴇᴅ**\nʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ʜᴀs ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ.")
            except Exception: pass
        else:
            success_msg = await message.reply(f"❌ **ᴜsᴇʀ ɪᴅ {target_id} ɴᴏᴛ ғᴏᴜɴᴅ ɪɴ ᴛʜᴇ ᴘʀᴇᴍɪᴜᴍ ʟɪsᴛ.**", reply_markup=TEMP_BACK_BTN)
        asyncio.create_task(auto_delete_message(success_msg, 120))

    elif step == "set_buy_link":
        del ADMIN_STATE[chat_id]
        await db.update_setting("premium_buy_link", text)
        success_msg = await message.reply(f"✅ **ᴘʀᴇᴍɪᴜᴍ ʙᴜʏ ʟɪɴᴋ ᴜᴘᴅᴀ態ᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!**", reply_markup=TEMP_BACK_BTN)
        asyncio.create_task(auto_delete_message(success_msg, 120))

    elif step == "set_start_txt":
        del ADMIN_STATE[chat_id]
        await db.update_setting("custom_start_text", text)
        success_msg = await message.reply("✅ **sᴛᴀʀᴛ ᴘᴀɢᴇ ᴍᴇssᴀɢᴇ ᴛᴇxᴛ ᴜᴘᴅᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!**", reply_markup=TEMP_BACK_BTN)
        asyncio.create_task(auto_delete_message(success_msg, 120))

    elif step == "set_start_img":
        if not text.startswith(("http://", "https://")):
            err_msg = await message.reply("❌ **ɪɴᴠᴀʟɪᴅ ғᴏʀᴍᴀᴛ!** ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ɪᴍᴀɢᴇ ᴜʀʟ/ʟɪɴᴋ.")
            ADMIN_STATE[chat_id]["bot_msg_id"] = err_msg.id
            return
        del ADMIN_STATE[chat_id]
        await db.update_setting("start_photo", text)
        success_msg = await message.reply("✅ **sᴛᴀʀᴛ ᴘᴀɢᴇ ɪᴍᴀɢᴇ ᴜʀʟ ᴜᴘᴅᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!**", reply_markup=TEMP_BACK_BTN)
        asyncio.create_task(auto_delete_message(success_msg, 120))

    elif step == "set_delete_time":
        try:
            minutes = int(text)
            del ADMIN_STATE[chat_id]
            await db.update_setting("auto_delete_time", minutes * 60)
            success_msg = await message.reply(f"✅ **ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ sᴇᴛ ᴛᴏ {minutes} ᴍɪɴᴜᴛᴇs!**", reply_markup=TEMP_BACK_BTN)
            asyncio.create_task(auto_delete_message(success_msg, 120))
        except ValueError:
            err_msg = await message.reply("❌ **ɪɴᴠᴀʟɪᴅ ғᴏʀᴍᴀᴛ!** ᴏɴʟʏ ɴᴜᴍʙᴇʀs ᴀʀᴇ ᴀʟʟᴏᴡᴇᴅ.")
            ADMIN_STATE[chat_id]["bot_msg_id"] = err_msg.id

    elif step == "set_token_time":
        try:
            hours = int(text)
            del ADMIN_STATE[chat_id]
            await db.update_setting("verify_expire_time", hours * 3600)
            success_msg = await message.reply(f"✅ **ᴛᴏᴋᴇɴ ᴠᴀʟɪᴅɪᴛʏ sᴇᴛ ᴛᴏ {hours} ʜᴏᴜʀs!**", reply_markup=TEMP_BACK_BTN)
            asyncio.create_task(auto_delete_message(success_msg, 120))
        except ValueError:
            err_msg = await message.reply("❌ **ɪɴᴠᴀʟɪᴅ ғᴏʀᴍᴀᴛ!** ᴏɴʟʏ ɪɴᴛᴇɢᴇʀs/ɴᴜᴍʙᴇʀs ᴀʀᴇ ᴀʟʟᴏᴡᴇᴅ.")
            ADMIN_STATE[chat_id]["bot_msg_id"] = err_msg.id

    elif step == "set_shortener_domain":
        if not is_valid_domain(text):
            err_msg = await message.reply("❌ **ɪɴᴠᴀʟɪᴅ ᴅᴏᴍᴀɪɴ ғᴏʀᴍᴀᴛ!** ᴜsᴇ `site.com`.")
            ADMIN_STATE[chat_id]["bot_msg_id"] = err_msg.id
            return
        ADMIN_STATE[chat_id]["domain"] = text
        ADMIN_STATE[chat_id]["step"] = "set_shortener_api"
        ask_msg = await message.reply("🔑 **sᴇɴᴅ ᴛʜᴇ ᴀᴘɪ ᴋᴇʏ ғᴏʀ ᴛʜᴀᴛ ᴡᴇʙsɪᴛᴇ:**\n\n*(ᴛʏᴘᴇ /cancel ᴛᴏ ᴄᴀɴᴄᴇʟ)*")
        ADMIN_STATE[chat_id]["bot_msg_id"] = ask_msg.id

    elif step == "set_shortener_api":
        if not is_valid_api(text):
            err_msg = await message.reply("❌ **ɪɴᴠᴀʟɪᴅ ᴀᴘɪ ғᴏʀᴍᴀᴛ!**")
            ADMIN_STATE[chat_id]["bot_msg_id"] = err_msg.id
            return
        domain = ADMIN_STATE[chat_id]["domain"]
        api = text
        del ADMIN_STATE[chat_id]
        await db.update_setting("shortlink_url", domain)
        await db.update_setting("shortlink_api", api)
        success_msg = await message.reply("✅ **sʜᴏʀᴛᴇɴᴇʀ ᴅᴇᴛᴀɪʟs ᴜᴘᴅᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!**", reply_markup=TEMP_BACK_BTN)
        asyncio.create_task(auto_delete_message(success_msg, 120))


# =============================================================
# 🔔 AUTOMATIC BACKGROUND EXPIRY MONITOR (CRON JOB)
# =============================================================
async def premium_expiry_monitor(client: Client):
    while True:
        try:
            current_time = datetime.utcnow()
            expired_cursor = db.premium.find({"expire_at": {"$lte": current_time}})
            expired_users = await expired_cursor.to_list(length=100)
            
            for user in expired_users:
                target_id = user["id"]
                await db.remove_premium_user(target_id)
                
                try:
                    await client.send_message(
                        chat_id=int(target_id),
                        text=(
                            "⚠️ **ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ ᴇxᴘɪʀᴇᴅ / ʀᴇᴍᴏᴠᴇᴅ**\nʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ʜᴀs ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ"
                        )
                    )
                    logger.info(f"[Auto-Expiry] Notification successfully sent to {target_id}")
                except Exception as e:
                    logger.warning(f"[Auto-Expiry] Could not message user {target_id}: {e}")
                    
        except Exception as e:
            logger.error(f"[Auto-Expiry Loop Error]: {e}")
            
        await asyncio.sleep(60)
