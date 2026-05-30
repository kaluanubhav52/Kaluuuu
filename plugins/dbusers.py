import motor.motor_asyncio
from config import DB_NAME, DB_URI
from datetime import datetime, timedelta

class Database:
    
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.settings = self.db.settings
        # 👑 Premium Users ke liye alag collection
        self.premium = self.db.premium_users

    def new_user(self, id, name):
        return dict(
            id = id,
            name = name,
            verify_time = 0
        )
    
    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)
    
    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count
    
    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    # User verification ke liye
    async def update_verify_time(self, user_id, verify_time):
        await self.col.update_one({'id': int(user_id)}, {'$set': {'verify_time': verify_time}}, upsert=True)

    async def get_verify_time(self, user_id):
        user = await self.col.find_one({'id': int(user_id)})
        return user.get('verify_time', 0) if user else 0

        # =============================================================
    # 🔑 LIVE TOKEN TRACKER SYSTEM
    # =============================================================

    async def get_today_string(self):
        """Aaj ki date nikalega (YYYY-MM-DD) taaki daily track ho sake"""
        return datetime.utcnow().strftime("%Y-%m-%d")

    async def increment_token_count(self):
        """Jab bhi koi user naya token/shortlink generate karega, yeh +1 karega"""
        today = await self.get_today_string()
        await self.settings.update_one(
            {"_id": f"tokens_{today}"},
            {"$inc": {"count": 1}},
            upsert=True
        )

    async def get_today_tokens(self):
        """Aaj total kitne tokens generate hue, woh nikalega"""
        today = await self.get_today_string()
        data = await self.settings.find_one({"_id": f"tokens_{today}"})
        return data.get("count", 0) if data else 0
        

    # =============================================================
    # --- PREMIUM USER MANAGEMENT SYSTEM (UPDATED) ---
    # =============================================================

    async def add_premium_user(self, user_id, days=0, hours=0):
        """
        User ko premium list mein add ya update karega.
        Ab aap 'days' aur 'hours' dono ek sath ya alag-alag de sakte hain.
        """
        expiry_date = datetime.utcnow() + timedelta(days=int(days), hours=int(hours))
        
        await self.premium.update_one(
            {"id": int(user_id)},
            {"$set": {"expire_at": expiry_date, "is_premium": True}},
            upsert=True
        )
        return expiry_date

    async def remove_premium_user(self, user_id):
        """User ko premium list se delete karega (Sirf UID se command chalegi)"""
        result = await self.premium.delete_one({"id": int(user_id)})
        return bool(result.deleted_count > 0)

    async def check_premium_status(self, user_id):
        """Check karega ki user premium hai ya nahi. Expire hone par automatic remove karega."""
        user = await self.premium.find_one({"id": int(user_id)})
        if not user:
            return False
            
        if user["expire_at"] < datetime.utcnow():
            await self.remove_premium_user(user_id)
            return False
            
        return True

    async def get_remaining_premium_time(self, user_id):
        """
        Yeh return karega ki user ke paas kitna time bacha hai (Days aur Hours mein).
        """
        user = await self.premium.find_one({"id": int(user_id)})
        if not user or user["expire_at"] < datetime.utcnow():
            return None
            
        time_left = user["expire_at"] - datetime.utcnow()
        days = time_left.days
        hours = time_left.seconds // 3600
        
        return {"days": days, "hours": hours}

    async def get_all_premium_users(self):
        """Sirf un users ki list nikalega jo abhi tak expire nahi hue hain"""
        current_time = datetime.utcnow()
        cursor = self.premium.find({"expire_at": {"$gt": current_time}})
        users = await cursor.to_list(length=5000)
        return [user["id"] for user in users]

    async def get_all_premium_users_with_time(self):
        """👑 NEW: Premium users ka poora data nikalega bacha hua time dikhane ke liye"""
        current_time = datetime.utcnow()
        cursor = self.premium.find({"expire_at": {"$gt": current_time}})
        return await cursor.to_list(length=5000)

    # =============================================================

    # Dynamic Admin Panel Settings (Get and Update)
    async def get_settings(self):
        settings = await self.settings.find_one({"_id": "bot_config"})
        if not settings:
            default = {
                "_id": "bot_config",
                "verify_mode": True,
                "premium_mode": False,
                "auto_delete_mode": True,
                "auto_delete_time": 1800,
                "protect_content": False,
                "start_photo": None,       
                "custom_start_text": None, 
                "shortlink_url": "linkshortify.com",
                "shortlink_api": "9d9199caec2c2e30e0670f1549ffa1a316caa541",
                "verify_expire_time": 86400
            }
            await self.settings.insert_one(default)
            return default
        return settings

    async def update_setting(self, key, value):
        await self.settings.update_one({"_id": "bot_config"}, {"$set": {key: value}}, upsert=True)

    async def channel_exist(self, channel_id: int):
        found = await self.fsub_data.find_one({'_id': channel_id})
        return bool(found)

    async def add_channel(self, channel_id: int):
        if not await self.channel_exist(channel_id):
            await self.fsub_data.insert_one({'_id': channel_id})
            return

    async def rem_channel(self, channel_id: int):
        if await self.channel_exist(channel_id):
            await self.fsub_data.delete_one({'_id': channel_id})
            return

    async def show_channels(self):
        channel_docs = await self.fsub_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids

    
# Get current mode of a channel
    async def get_channel_mode(self, channel_id: int):
        data = await self.fsub_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    # Set mode of a channel
    async def set_channel_mode(self, channel_id: int, mode: str):
        await self.fsub_data.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    # REQUEST FORCE-SUB MANAGEMENT

    # Add the user to the set of users for a   specific channel
    async def req_user(self, channel_id: int, user_id: int):
        try:
            await self.rqst_fsub_Channel_data.update_one(
                {'_id': int(channel_id)},
                {'$addToSet': {'user_ids': int(user_id)}},
                upsert=True
            )
        except Exception as e:
            print(f"[DB ERROR] Failed to add user to request list: {e}")


    # Method 2: Remove a user from the channel set
    async def del_req_user(self, channel_id: int, user_id: int):
        # Remove the user from the set of users for the channel
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id}, 
            {'$pull': {'user_ids': user_id}}
        )

    # Check if the user exists in the set of the channel's users
    async def req_user_exist(self, channel_id: int, user_id: int):
        try:
            found = await self.rqst_fsub_Channel_data.find_one({
                '_id': int(channel_id),
                'user_ids': int(user_id)
            })
            return bool(found)
        except Exception as e:
            print(f"[DB ERROR] Failed to check request list: {e}")
            return False  


    # Method to check if a channel exists using show_channels
    async def reqChannel_exist(self, channel_id: int):
    # Get the list of all channel IDs from the database
        channel_ids = await self.show_channels()
        #print(f"All channel IDs in the database: {channel_ids}")

    # Check if the given channel_id is in the list of channel IDs
        if channel_id in channel_ids:
            #print(f"Channel {channel_id} found in the database.")
            return True
        else:
            #print(f"Channel {channel_id} NOT found in the database.")
            return False

db = Database(DB_URI, DB_NAME)
