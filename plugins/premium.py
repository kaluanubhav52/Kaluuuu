import math
from datetime import datetime, timedelta
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from plugins.dbusers import db  # Aapka updated database instance
from config import *


def generate_status_bar(filled_percent):
    """
    Filled percent ke basis par 10 blocks ki status bar generate karta hai.
    Filled blocks ke liye '█' aur empty ke liye '░' ka use hota hai.
    """
    filled_percent = max(0, min(100, filled_percent))
    filled_length = int(round(10 * filled_percent / 100))
    bar = '█' * filled_length + '░' * (10 - filled_length)
    return bar

@Client.on_message(filters.command("plan") & filters.private)
async def plan_command_handler(client: Client, message: Message):
    """User ke liye subscription plans display karne ke liye command."""
    premium_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Qʀ Code", callback_data="show_premium_qr", style=enums.ButtonStyle.PRIMARY),
            InlineKeyboardButton("💳 Uᴘɪ ID", callback_data="show_premium_upi", style=enums.ButtonStyle.SUCCESS)
        ],
        [InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close_data", style=enums.ButtonStyle.DANGER)]
    ])
    await message.reply_text(text=PREMIUM_PLANS_TEXT, reply_markup=premium_keyboard)


@Client.on_message(filters.command("myplan") & filters.private)
async def my_plan_handler(client: Client, message: Message):
    """Premium user validity track karne aur IST time ke sath dynamic progress bar dikhane ke liye command."""
    user_id = message.from_user.id
    user_mention = message.from_user.mention
    
    # Check user premium status
    is_premium = await db.check_premium_status(user_id)

    if is_premium:
        # DB collection se document direct fetch karenge expiry calculation ke liye
        user_data = await db.premium.find_one({"id": int(user_id)})
        
        if user_data and "expire_at" in user_data:
            expire_at_utc = user_data["expire_at"]
            current_time_utc = datetime.utcnow()
            
            # Time components calculation (UTC me hi chalega backend gap ke liye)
            time_left = expire_at_utc - current_time_utc
            total_seconds_left = time_left.total_seconds()
            
            # 🇮🇳 UTC time ko IST (Indian Standard Time) me convert karne ke liye (+5:30)
            expire_at_ist = expire_at_utc + timedelta(hours=5, minutes=30)
            
            if total_seconds_left > 0:
                rem_days = time_left.days
                rem_hours = time_left.seconds // 3600
                
                # Dynamic Percentage calculation for Status Bar
                if rem_days >= 30:
                    max_expected_days = 90  # 3 Month plan fallback
                elif rem_days >= 7:
                    max_expected_days = 30  # 1 Month plan fallback
                else:
                    max_expected_days = 7   # Weekly plan fallback
                    
                total_duration_seconds = max_expected_days * 86400
                remaining_percent = (total_seconds_left / total_duration_seconds) * 100
                remaining_percent = max(1, min(100, remaining_percent))
                
                status_bar = generate_status_bar(remaining_percent)
                validity_text = f"⏳ <b>{rem_days} Days, {rem_hours} Hours remaining</b>"
                
                # 🇮🇳 Indian Format me date aur time (DD-MM-YYYY HH:MM AM/PM)
                expiry_date_str = expire_at_ist.strftime('%d-%m-%Y %I:%M %p') + " (IST)"
            else:
                status_bar = generate_status_bar(0)
                remaining_percent = 0
                validity_text = "⚠️ <b>Expiring soon / Expired</b>"
                expiry_date_str = "Expired"
        else:
            status_bar = generate_status_bar(100)
            remaining_percent = 100
            validity_text = "✨ <b>Lifetime Premium Active</b>"
            expiry_date_str = "Unlimited"

        success_text = (
            "👑 <b>YOUR PREMIUM STATUS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> {user_mention}\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            "✨ <b>Status:</b> Premium User (Active)\n"
            f"📅 <b>Expiry:</b> <code>{expiry_date_str}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Usage Limit/Time:</b>\n"
            f"|{status_bar}| {int(remaining_percent)}%\n\n"
            f"{validity_text}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 No ads, no limits! Direct high-speed files active."
        )

        buy_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Close", callback_data="close_data", style=enums.ButtonStyle.DANGER)]
        ])
        await message.reply_text(text=success_text, reply_markup=buy_keyboard)
        
    else:
        # Non-premium / Free User Setup (With Empty Status Bar)
        empty_bar = generate_status_bar(0)
        free_text = (
            "⚠️ <b>YOUR PREMIUM STATUS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> {user_mention}\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            "✨ <b>Status:</b> Free User (No Active Plan)\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Premium Bar:</b>\n"
            f"|{empty_bar}| 0%\n\n"
            "❌ Aap free plan par hain. Har file download karne ke liye aapko links bypass ya verify karna hoga.\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👉 Premium access chahiye? Niche diye button par click karein."
        )
        
        buy_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ Buy Premium ⭐", callback_data="buy_premium_panel", style=enums.ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("❌ Close", callback_data="close_data", style=enums.ButtonStyle.DANGER)]
        ])
        await message.reply_text(text=free_text, reply_markup=buy_keyboard)
