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

db = Database(DB_URI, DB_NAME)
