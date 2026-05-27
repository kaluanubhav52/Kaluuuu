# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging, asyncio, os, re, random, pytz, aiohttp, requests, string, json, http.client, time
from datetime import date, datetime
from config import VERIFY_EXPIRE_TIME # Yeh fallback ke liye rahega
from shortzy import Shortzy
from plugins.dbusers import db


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
TOKENS = {}

async def get_verify_shorted_link(link):
    # 🌟 Live values from Database
    settings = await db.get_settings()
    shortlink_url = settings.get("shortlink_url", "linkshortify.com")
    shortlink_api = settings.get("shortlink_api", "9d9199caec2c2e30e0670f1549ffa1a316caa541")

    if shortlink_url == "api.shareus.io":
        url = f'https://{shortlink_url}/easy_api'
        params = {
            "key": shortlink_api,
            "link": link,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.text()
                    return data
        except Exception as e:
            logger.error(e)
            return link
    else:
        try:
            shortzy = Shortzy(api_key=shortlink_api, base_site=shortlink_url)
            link = await shortzy.convert(link)
            return link
        except Exception as e:
            logger.error(f"Shortener Error: {e}")
            return link

async def check_token(bot, userid, token):
    user = await bot.get_users(userid)
    if user.id in TOKENS.keys():
        TKN = TOKENS[user.id]
        if token in TKN.keys():
            is_used = TKN[token]
            if is_used == True:
                return False
            else:
                return True
    else:
        return False

async def get_token(bot, userid, link, file_data=""):
    user = await bot.get_users(userid)
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
    TOKENS[user.id] = {token: False}
    
    # 📥 File data ko verification link ke sath embed kar rahe hain taaki Get File button work kare
    if file_data:
        link = f"{link}verify-{user.id}-{token}-{file_data}"
    else:
        link = f"{link}verify-{user.id}-{token}"
        
    shortened_verify_url = await get_verify_shorted_link(link)
    return str(shortened_verify_url)

async def verify_user(bot, userid, token):
    user = await bot.get_users(userid)
    TOKENS[user.id] = {token: True}
    
    # MongoDB database permanent verification log
    current_time = int(time.time())
    await db.update_verify_time(user.id, current_time)

async def check_verification(bot, userid):
    user = await bot.get_users(userid)
    
    # 👑 PREMIUM BYPASS: Agar user premium member hai toh shortlink bypass ho jayega
    is_premium = await db.check_premium_status(user.id)
    if is_premium:
        return True

    # Admin panel switch control
    settings = await db.get_settings()
    if not settings.get("verify_mode", True):
        return True  

    # Database se user ka last verified timestamp
    last_verified = await db.get_verify_time(user.id)
    
    if last_verified == 0:
        return False 
        
    # FIXED PRIORITY LOGIC HERE:
    # Pehle database ki setting check hogi, agar wahan kuch nahi mila tabhi config ka fallback (VERIFY_EXPIRE_TIME) use hoga.
    db_expire_time = settings.get("verify_expire_time")
    expiry_limit = int(db_expire_time) if db_expire_time is not None else VERIFY_EXPIRE_TIME
    
    if (int(time.time()) - last_verified) > expiry_limit:
        return False  # Expired
    else:
        return True   # Valid
