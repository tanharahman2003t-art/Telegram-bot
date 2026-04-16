import telebot
from telebot.types import ReplyKeyboardMarkup
from datetime import datetime
import time, json, os

# ===== CONFIG =====
TOKEN = "8778891878:AAGUsVF7XOs9iTv4hfxnLbpidDHBlv8tVjY"
bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"

LIMITS = {
    "🚿 Toilet": 10 * 60,
    "☕ Break": 15 * 60,
    "🍽 Eat": 30 * 60
}

# ===== DATABASE =====
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"users": {}}, f)
    return json.load(open(DATA_FILE))

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"), indent=4)

# ===== UI =====
def menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🟢 Start Work", "⚫ Off Work")
    m.row("🚿 Toilet", "☕ Break", "🍽 Eat")
    m.row("🔙 Back to Seat")
    return m

# ===== HELPER =====
def now():
    return datetime.now().strftime("%m/%d %H:%M:%S")

def format_time(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    if m > 0:
        return f"{m} min {s} sec"
    return f"{s} sec"

def checkin_msg(name, uid, action, hint, details="", result=""):
    return f"""👤 {name}
User ID: {uid}
----------
✅ Check-In Succeeded: {action} - {now()}
{details}
Hint: {hint}

----------
✅ {result}"""

# ===== BOT =====
@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, "Welcome 👇", reply_markup=menu())

@bot.message_handler(func=lambda m: True)
def handle(m):
    data = load_data()
    uid = str(m.from_user.id)
    name = m.from_user.first_name
    chat_id = m.chat.id
    text = m.text

    if uid not in data["users"]:
        data["users"][uid] = {
            "working": False,
            "activity": None,
            "start_time": None,
            "total": 0
        }

    user = data["users"][uid]

    # ===== START WORK =====
    if text == "🟢 Start Work":
        if user["working"]:
            bot.send_message(chat_id, "⚠️ Already working!", reply_markup=menu())
            return

        user["working"] = True

        bot.send_message(chat_id,
            checkin_msg(
                name, uid, "Start Work",
                "Remember to check in when Off Work arrives.",
                result="Work Started Successfully"
            ),
            reply_markup=menu()
        )

    # ===== MUST START FIRST =====
    elif not user["working"]:
        bot.send_message(chat_id, "⚠️ Please click 'Start Work' first!", reply_markup=menu())
        return

    # ===== ACTIVITY =====
    elif text in LIMITS:
        if user["activity"]:
            bot.send_message(chat_id, f"⚠️ Already in {user['activity']}!", reply_markup=menu())
            return

        user["activity"] = text
        user["start_time"] = time.time()

        bot.send_message(chat_id,
            checkin_msg(
                name, uid, text,
                "Remember to click Back to Seat when you return.",
                details=f"\n⏱ Time Limit: {format_time(LIMITS[text])}\n",
                result=f"{text} Started"
            ),
            reply_markup=menu()
        )

    # ===== BACK TO SEAT =====
    elif text == "🔙 Back to Seat":
        if not user["activity"]:
            bot.send_message(chat_id, "⚠️ No active task!", reply_markup=menu())
            return

        used = time.time() - user["start_time"]
        user["total"] += used

        activity = user["activity"]

        user["activity"] = None
        user["start_time"] = None

        bot.send_message(chat_id,
            checkin_msg(
                name, uid, "Back to Seat",
                "Stay focused! You can do it 💪",
                details=f"\n📌 Activity: {activity}\n⏱ Used: {format_time(used)}\n📊 Total Today: {format_time(user['total'])}\n",
                result="Back to Seat Successfully"
            ),
            reply_markup=menu()
        )

    # ===== OFF WORK =====
    elif text == "⚫ Off Work":
        if not user["working"]:
            bot.send_message(chat_id, "⚠️ Work not started!", reply_markup=menu())
            return

        user["working"] = False
        user["activity"] = None
        user["start_time"] = None

        bot.send_message(chat_id,
            checkin_msg(
                name, uid, "Off Work",
                "See you tomorrow! Rest well 😴",
                details=f"\n📊 Total Break Time: {format_time(user['total'])}\n",
                result="Work Finished. Good job 👍"
            ),
            reply_markup=menu()
        )

    save_data(data)

bot.polling()
