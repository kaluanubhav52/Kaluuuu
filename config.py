import re
import os
from os import environ
from Script import script

id_pattern = re.compile(r'^.\d+$')
def is_enabled(value, default):
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default
      
# Bot Information
API_ID = int(environ.get("API_ID", ""))
API_HASH = environ.get("API_HASH", "")
BOT_TOKEN = environ.get("BOT_TOKEN", "")

PICS = (environ.get('PICS', 'https://i.ibb.co/Pv9w1khk/photo-2026-05-23-15-55-01-7643116408875778072.jpg https://i.ibb.co/jZ6zGxpp/photo-2026-05-23-15-55-21-7643116464710352900.jpg https://i.ibb.co/NnC4Ht8N/photo-2026-05-23-15-55-34-7643116516249960464.jpg https://i.ibb.co/FLnGTrf1/photo-2026-05-23-15-55-46-7643116567789568016.jpg')).split() # Bot Start Picture
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '5898522531').split()]
BOT_USERNAME = environ.get("BOT_USERNAME", "usekaluubot") # without @
PORT = environ.get("PORT", "8080")

# Clone Info :-
CLONE_MODE = bool(environ.get('CLONE_MODE', False)) # Set True or False

# If Clone Mode Is True Then Fill All Required Variable, If False Then Don't Fill.
CLONE_DB_URI = environ.get("CLONE_DB_URI", "")
CDB_NAME = environ.get("CDB_NAME", "clonekcbotz")

# Database Information
DB_URI = environ.get("DB_URI", "")
DB_NAME = environ.get("DB_NAME", "kcbotz")

# Auto Delete Information
AUTO_DELETE_MODE = bool(environ.get('AUTO_DELETE_MODE', False)) # Set True or False

# If Auto Delete Mode Is True Then Fill All Required Variable, If False Then Don't Fill.
AUTO_DELETE = int(environ.get("AUTO_DELETE", "30")) # Time in Minutes
AUTO_DELETE_TIME = int(environ.get("AUTO_DELETE_TIME", "1800")) # Time in Seconds

# Channel Information
LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "-1003793273994"))
DB_CHANNEL = int(environ.get("DB_CHANNEL", "-1003935596893"))
# File Caption Information
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", f"{script.CAPTION}")
BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", CUSTOM_FILE_CAPTION)

# Enable - True or Disable - False
PUBLIC_FILE_STORE = is_enabled((environ.get('PUBLIC_FILE_STORE', "False")), True)

# upi & qr details 
UPI_ID = os.environ.get("UPI_ID", "6398324472@fam") 
QR_IMAGE_URL = os.environ.get("QR_IMAGE_URL", "https://i.ibb.co/PGbZztgZ/photo-2026-05-04-16-41-38-7636287934861148164.jpg") 
PREMIUM_PLANS_TEXT = (
    "💳 <b>PREMIUM SUBSCRIPTION PLAN</b>\n\n"
    "1. 15₹ = 7 DAY\n"
    "2. 50₹ = 1 MONTH\n"
    "3. 120₹ = 3 MONTH\n"
    "4. 220₹ = 6 MONTH\n\n"
    "👑 <b>PREMIUM FEATURES :</b>\n"
    "🛑 SEARCH IN THE BOT\n"
    "🛑 GET UNLIMITED FILES\n"
    "🛑 NO NEED TO OPEN LINKS\n"
    "🛑 NO NEED VERIFY\n"
    "🛑 DIRECT FILES\n\n"
    "➡️ CHECK YOUR ACTIVE PLAN BY USING: /myplan\n\n"
    "‼️ <b>MUST SEND SCREENSHOT AFTER PAYMENT</b>"
)

# Verify Info :-
VERIFY_MODE = bool(environ.get('VERIFY_MODE', True)) # Set True or False

# If Verify Mode Is True Then Fill All Required Variable, If False Then Don't Fill.
SHORTLINK_URL = environ.get("SHORTLINK_URL", "linkshortify.com") # shortlink domain without https://
SHORTLINK_API = environ.get("SHORTLINK_API", "9d9199caec2c2e30e0670f1549ffa1a316caa541") # shortlink api
VERIFY_TUTORIAL = environ.get("VERIFY_TUTORIAL", "https://t.me/howanubhav/14") # how to open link 
VERIFY_EXPIRE_TIME = int(environ.get("VERIFY_EXPIRE_TIME", "300"))

#Reaction /start
REACTIONS = ["🤝", "😇", "🤗", "😍", "👍", "🎅", "😐", "🥰", "🤩", "😱", "🤣", "😘", "👏", "😛", "😈", "🎉", "⚡️", "🫡", "🤓", "😎", "🏆", "🔥", "🤭", "🌚", "🆒", "👻", "😁"] 

# Website Info:
WEBSITE_URL_MODE = bool(environ.get('WEBSITE_URL_MODE', False)) # Set True or False

# If Website Url Mode Is True Then Fill All Required Variable, If False Then Don't Fill.
WEBSITE_URL = environ.get("WEBSITE_URL", "") # For More Information Check Video On Yt - @Tech_VJ

# File Stream Config
STREAM_MODE = bool(environ.get('STREAM_MODE', False)) # Set True or False

# If Stream Mode Is True Then Fill All Required Variable, If False Then Don't Fill.
MULTI_CLIENT = False
SLEEP_THRESHOLD = int(environ.get('SLEEP_THRESHOLD', '60'))
PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200"))  # 20 minutes
if 'DYNO' in environ:
    ON_HEROKU = True
else:
    ON_HEROKU = False
URL = environ.get("URL", "https://testofvjfilter-1fa60b1b8498.herokuapp.com/")


# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
    
