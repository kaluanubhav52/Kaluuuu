# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from config import *
from plugins.users_api import get_user, get_short_link
import re
import os
import json
import base64

# Users ki dynamic state track karne ke liye dictionaries
AWAITING_CONTENT = {}
BATCH_STATE = {}  # Format: {user_id: {"step": 1, "first_chat": ..., "first_msg": ...}}
CUSTOM_BATCH_STATE = {}  # 🆕 Track files as well as last counter message ID

async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False

# Telegram link regex pattern
LINK_REGEX = re.compile("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")

def extract_msg_info(message):
    """Message link ya forwarded message se chat_id aur msg_id nikalne ke liye helper function"""
    if message.text:
        match = LINK_REGEX.match(message.text.strip())
        if match:
            chat_id = match.group(4)
            msg_id = int(match.group(5))
            if chat_id.isnumeric():
                chat_id = int(("-100" + chat_id))
            return chat_id, msg_id
            
    if message.forward_from_chat:
        return message.forward_from_chat.id, message.forward_from_message_id
        
    return None, None


# 🛠️ 1. INTERCEPT HANDLER (Sabhi states ko handle karne ke liye sabse upar)
@Client.on_message(filters.private & ~filters.command(["link", "batch", "cbatch", "cdone", "start", "api", "base_site"]) & filters.create(allowed), group=-1)
async def handle_conversations(bot, message):
    user_id = message.from_user.id
    username = (await bot.get_me()).username
    
    # ─── 🆕 CASE C: CUSTOM BATCH MEDIA CATCHING STATE ───
    if user_id in CUSTOM_BATCH_STATE:
        if not (message.document or message.video or message.audio or message.photo or message.text):
            return
            
        try:
            if CUSTOM_BATCH_STATE[user_id]["last_msg_id"]:
                try:
                    await bot.delete_messages(chat_id=message.chat.id, message_ids=CUSTOM_BATCH_STATE[user_id]["last_msg_id"])
                except Exception:
                    pass

            copied_msg = await message.copy(DB_CHANNEL)
            CUSTOM_BATCH_STATE[user_id]["files"].append({"channel_id": DB_CHANNEL, "msg_id": copied_msg.id})
            total_saved = len(CUSTOM_BATCH_STATE[user_id]["files"])
            
            status_msg = await message.reply_text(
                f"<b>📥 𝖥𝖨𝖫𝖤 #{total_saved} 𝖠𝖣𝖣𝖤𝖣 𝖲𝖴𝖢𝖢𝖤𝖲𝖲𝖥𝖴𝖫𝖫𝖸!</b>\n\n"
                "<i>Aur files bhejte rahiye... Jab poora ho jaye toh /cdone send karne link nikal lein.</i>"
            )
            CUSTOM_BATCH_STATE[user_id]["last_msg_id"] = status_msg.id

        except Exception as e:
            await message.reply_text(f"❌ **Error while saving file:** {e}")
            
        message.stop_propagation()

    # ─── CASE A: SINGLE LINK WAITING STATE ───
    elif AWAITING_CONTENT.get(user_id):
        AWAITING_CONTENT[user_id] = False
        processing_msg = await message.reply_text("<b>PROCESSING... 🚀</b>")
        
        try:
            post = await message.copy(DB_CHANNEL)
            file_id = str(post.id)
            string = 'file_' + file_id
            outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
            
            user = await get_user(user_id)
            share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}" if WEBSITE_URL_MODE else f"https://t.me/{username}?start={outstr}"
                
            if user["base_site"] and user["shortener_api"] != None:
                short_link = await get_short_link(user, share_link)
                response_text = f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\n🖇️ sʜᴏʀᴛ ʟɪɴᴋ :- {short_link}</b>"
            else:
                response_text = f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\n🔗 ᴏʀɪɢɪɴᴀʟ ʟɪɴᴋ :- {share_link}</b>"
            
            await processing_msg.delete()
            await message.reply(response_text)
        except Exception as e:
            await processing_msg.edit(f"❌ **Error:** {str(e)}")
            
        message.stop_propagation()

    # ─── CASE B: BATCH LINK WAITING STATE ───
    elif user_id in BATCH_STATE:
        state = BATCH_STATE[user_id]
        
        if state["step"] == 1:
            chat_id, msg_id = extract_msg_info(message)
            if not chat_id or not msg_id:
                return await message.reply_text("❌ **Invalid Input!** Kripya forward tag ke sath message forward karein ya sahi link bhejen.")
                
            state["first_chat"] = chat_id
            state["first_msg"] = msg_id
            state["step"] = 2
            
            await message.reply_text(
                "<b>Forward The Last Message From Your Batch Channel (With Forward Tag)... Or Give Me Last Message Link From Your Batch Channel\n\n"
                f"NOTE : MAKE SURE THIS @{username} BOT IS ADMIN IN YOUR CHANNEL WITH FULL RIGHT</b>"
            )
            message.stop_propagation()
            
        elif state["step"] == 2:
            chat_id, msg_id = extract_msg_info(message)
            if not chat_id or not msg_id:
                return await message.reply_text("❌ **Invalid Input!** Kripya last message link ya forward tag ke sath message bhejen.")
                
            f_chat_id = state["first_chat"]
            f_msg_id = state["first_msg"]
            l_chat_id = chat_id
            l_msg_id = msg_id
            
            del BATCH_STATE[user_id]
            
            if f_chat_id != l_chat_id:
                return await message.reply_text("❌ **Chat IDs matched nahi hui!** Dono messages ek hi channel ke hone chahiye.")
                
            try:
                await bot.get_chat(f_chat_id)
            except ChannelInvalid:
                return await message.reply_text('❌ This may be a private channel / group. Make me an admin over there to index the files.')
            except Exception as e:
                return await message.reply_text(f'❌ Error: {e}')
                
            sts = await message.reply_text("**ɢᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋ 𝖥𝖮𝖱 𝖸𝖮𝖴𝖱 𝖬𝖤𝖲𝖲𝖠𝖦𝖤**.\n**ᴛʜɪs ᴍᴀʏ ᴛᴀᴋᴇ ᴛɪᴍᴇ ᴅᴇᴘᴇɴᴅɪɴɢ ᴜᴘᴏɴ ɴᴜᴍʙᴇʀ ᴏғ ᴍᴇssᴀɢᴇs**")
            FRMT = "**ɢᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋ...**\n**ᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs:** {total}\n**ᴅᴏɴᴇ:** {current}\n**ʀᴇᴍᴀɪɴɪɴɢ:** {rem}\n**sᴛᴀᴛᴜs:** {sts}"
            
            outlist = []
            og_msg = 0
            tot = 0
            
            async for msg in bot.iter_messages(f_chat_id, l_msg_id, f_msg_id):
                tot += 1
                if og_msg % 20 == 0:
                    try:
                        await sts.edit(FRMT.format(total=l_msg_id-f_msg_id, current=tot, rem=((l_msg_id-f_msg_id) - tot), sts="Saving Messages"))
                    except:
                        pass
                if msg.empty or msg.service:
                    continue
                file = {"channel_id": f_chat_id, "msg_id": msg.id}
                og_msg += 1
                outlist.append(file)
                
            file_name = f"batchmode_{user_id}.json"
            with open(file_name, "w+") as out:
                json.dump(outlist, out)
                
            post = await bot.send_document(DB_CHANNEL, file_name, file_name="Batch.json", caption="⚠️ Batch Generated For Filestore.")
            os.remove(file_name)
            
            string = str(post.id)
            file_id = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
            
            user = await get_user(user_id)
            
            # 🛠️ MODIFIED: 'BATCH-' ko yahan se bilkul hata diya gaya hai
            share_link = f"{WEBSITE_URL}?Tech_VJ={file_id}" if WEBSITE_URL_MODE else f"https://t.me/{username}?start={file_id}"
            
            if user["base_site"] and user["shortener_api"] != None:
                short_link = await get_short_link(user, share_link)
                await sts.edit(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\nContains `{og_msg}` files.\n\n🖇️ sʜᴏʀᴛ ʟɪɴᴋ :- {short_link}</b>")
            else:
                await sts.edit(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\nContains `{og_msg}` files.\n\n🔗 ᴏʀɪɢɪɴᴀʟ ʟɪɴᴋ :- {share_link}</b>")
                
            message.stop_propagation()


# 🛠️ 2. DIRECT MEDIA GENERATOR
@Client.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private & filters.create(allowed))
async def incoming_gen_link(bot, message):
    user_id = message.from_user.id
    if user_id in CUSTOM_BATCH_STATE:
        return
        
    username = (await bot.get_me()).username
    post = await message.copy(DB_CHANNEL)
    file_id = str(post.id)
    string = 'file_' + file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    user = await get_user(user_id)
    share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}" if WEBSITE_URL_MODE else f"https://t.me/{username}?start={outstr}"
    
    if user["base_site"] and user["shortener_api"] != None:
        short_link = await get_short_link(user, share_link)
        await message.reply(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\n🖇️ sʜᴏʀᴛ ʟɪɴᴋ :- {short_link}</b>")
    else:
        await message.reply(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\n🔗 ᴏʀɪɢɪɴᴀʟ ʟɪɴᴋ :- {share_link}</b>")


# 🛠️ 3. COMMAND HANDLER: /link
@Client.on_message(filters.command(['link']) & filters.private & filters.create(allowed))
async def gen_link_s(bot, message):
    user_id = message.from_user.id
    if user_id in BATCH_STATE: del BATCH_STATE[user_id]
    if user_id in CUSTOM_BATCH_STATE: del CUSTOM_BATCH_STATE[user_id]
    
    AWAITING_CONTENT[user_id] = True
    await message.reply_text("<b>SEND ME YOUR MESSAGE WHICH YOU WANT TO STORE</b>")


# 🛠️ 4. COMMAND HANDLER: /batch
@Client.on_message(filters.command(['batch']) & filters.private & filters.create(allowed))
async def gen_link_batch(bot, message):
    user_id = message.from_user.id
    if user_id in AWAITING_CONTENT: AWAITING_CONTENT[user_id] = False
    if user_id in CUSTOM_BATCH_STATE: del CUSTOM_BATCH_STATE[user_id]
    
    username = (await bot.get_me()).username
    BATCH_STATE[user_id] = {"step": 1, "first_chat": None, "first_msg": None}
    
    await message.reply_text(
        "<b>Forward The First Message From Your Batch Channel (With Forward Tag)... Or Give Me First Message Link From Your Batch Channel\n\n"
        f"NOTE : MAKE SURE THIS @{username} BOT IS ADMIN IN YOUR CHANNEL WITH FULL RIGHT</b>"
    )


# 🛠️ 5. 🆕 COMMAND HANDLER: /cbatch
@Client.on_message(filters.command(['cbatch']) & filters.private & filters.create(allowed))
async def start_custom_batch(bot, message):
    user_id = message.from_user.id
    if user_id in AWAITING_CONTENT: AWAITING_CONTENT[user_id] = False
    if user_id in BATCH_STATE: del BATCH_STATE[user_id]
    
    CUSTOM_BATCH_STATE[user_id] = {
        "last_msg_id": None,
        "files": []
    }
    
    await message.reply_text(
        "<b>✨ ᴄᴜsᴛᴏᴍ ʙᴀᴛᴄʜ ᴍᴏᴅᴇ ᴀᴄᴛɪᴠᴇ! ✨\n\n"
        "Ab aap jo bhi files (Videos, Documents, Photos, Text) yahan send karenge, "
        "wo sab is batch me ek ke baad ek save hoti jayengi.\n"
        "Bot purane counter alerts ko background me clear karta chalega taaki workspace clean rahe.\n\n"
        "Jab aap saari files send kar dein, toh link generate karne ke liye /cdone command bhein.</b>"
    )


# 🛠️ 6. 🆕 COMMAND HANDLER: /cdone
@Client.on_message(filters.command(['cdone']) & filters.private & filters.create(allowed))
async def complete_custom_batch(bot, message):
    user_id = message.from_user.id
    username = (await bot.get_me()).username
    
    if user_id not in CUSTOM_BATCH_STATE:
        return await message.reply_text("❌ **Aapka koi bhi Custom Batch session active nahi hai!** Pehle /cbatch start karein.")
        
    outlist = CUSTOM_BATCH_STATE[user_id]["files"]
    last_msg_id = CUSTOM_BATCH_STATE[user_id]["last_msg_id"]
    
    if last_msg_id:
        try:
            await bot.delete_messages(chat_id=message.chat.id, message_ids=last_msg_id)
        except:
            pass
        
    if not outlist:
        del CUSTOM_BATCH_STATE[user_id]
        return await message.reply_text("⚠️ **Aapne batch me koi bhi file send nahi ki thi.** Session closed.")
        
    sts = await message.reply_text("<b>Processing your custom batch... 🚀</b>")
    
    try:
        file_name = f"batchmode_{user_id}.json"
        with open(file_name, "w+") as out:
            json.dump(outlist, out)
            
        post = await bot.send_document(DB_CHANNEL, file_name, file_name="Batch.json", caption="⚠️ Custom Batch Generated For Filestore.")
        os.remove(file_name)
        
        del CUSTOM_BATCH_STATE[user_id]
        
        string = str(post.id)
        file_id = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        
        user = await get_user(user_id)
        
        # 🛠️ MODIFIED: 'BATCH-' ko yahan se bhi bilkul hata diya gaya hai
        share_link = f"{WEBSITE_URL}?Tech_VJ={file_id}" if WEBSITE_URL_MODE else f"https://t.me/{username}?start={file_id}"
        
        if user["base_site"] and user["shortener_api"] != None:
            short_link = await get_short_link(user, share_link)
            await sts.edit(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ᴄᴜsᴛᴏᴍ ʙᴀᴛᴄʜ ʟɪɴᴋ:\n\nContains `{len(outlist)}` files.\n\n🖇️ sʜᴏʀᴛ ʟɪɴᴋ :- {short_link}</b>")
        else:
            await sts.edit(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ᴄᴜsᴛᴏᴍ ʙᴀᴛᴄʜ ʟɪɴᴋ:\n\nContains `{len(outlist)}` files.\n\n🔗 ᴏʀɪɢɪɴᴀʟ ʟɪɴᴋ :- {share_link}</b>")
            
    except Exception as e:
        await sts.edit(f"❌ **Error while generating custom batch:** {e}")
        if user_id in CUSTOM_BATCH_STATE:
            del CUSTOM_BATCH_STATE[user_id]
