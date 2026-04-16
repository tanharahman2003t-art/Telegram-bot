import telebot
from telebot.types import ReplyKeyboardMarkup
from datetime import datetime
import time, json, os, threading
from flask import Flask, request, jsonify, render_template_string

# ================= CONFIG ================= #
TOKEN = "8778891878:AAGUsVF7XOs9iTv4hfxnLbpidDHBlv8tVjY"
WEB_URL = "https://telegram-bot-production-69ca.up.railway.app"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

DATA_FILE = "data.json"

LIMITS = {
    "🚿 Toilet": 10 * 60,
    "☕ Break": 15 * 60,
    "🍽 Eat": 30 * 60
}

# ================= DATABASE ================= #
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"users": {}}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= UI ================= #
def menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🟢 Start Work", "⚫ Off Work")
    m.row("🚿 Toilet", "☕ Break", "🍽 Eat")
    m.row("🔙 Back to Seat")
    return m

def format_time(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m} min {s} sec" if m else f"{s} sec"

def now():
    return datetime.now().strftime("%m/%d %H:%M:%S")

def checkin_msg(name, user_id, action, hint, details="", result=""):
    return f"""👤 {name}
User ID: {user_id}
----------
✅ Check-In Succeeded: {action} - {now()}
{details}
Hint: {hint}

----------
✅ {result}"""

# ================= AUTO WARNING ================= #
def auto_warning():
    while True:
        try:
            data = load_data()
            for uid, user in data["users"].items():
                if user.get("activity") and user.get("start_time"):
                    used = time.time() - user["start_time"]
                    limit = LIMITS.get(user["activity"], 0)

                    if used > limit and not user.get("warned"):
                        bot.send_message(int(uid), f"⚠️ Limit exceeded: {user['activity']}")
                        user["warned"] = True

            save_data(data)
        except:
            pass
        time.sleep(10)

threading.Thread(target=auto_warning, daemon=True).start()

# ================= BOT ================= #
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Welcome 👇", reply_markup=menu())

@bot.message_handler(func=lambda m: True)
def handle(message):
    data = load_data()
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    name = message.from_user.first_name
    text = message.text

    if uid not in data["users"]:
        data["users"][uid] = {
            "working": False,
            "activity": None,
            "start_time": None,
            "total": 0,
            "start_count": 0,
            "activity_count": 0,
            "warned": False
        }

    user = data["users"][uid]

    if text == "🟢 Start Work":
        if user["working"]:
            bot.send_message(chat_id, "⚠️ Already working!", reply_markup=menu())
            return

        user["working"] = True
        user["start_count"] += 1

        bot.send_message(chat_id,
            checkin_msg(name, uid, "Start Work",
            "Remember to check in when Off Work arrives.",
            result="Work Started Successfully"),
            reply_markup=menu()
        )

    elif not user["working"]:
        bot.send_message(chat_id, "⚠️ Please click 'Start Work' first!", reply_markup=menu())
        return

    elif text in LIMITS:
        if user["activity"]:
            bot.send_message(chat_id, f"⚠️ Already in {user['activity']}!", reply_markup=menu())
            return

        user["activity"] = text
        user["start_time"] = time.time()
        user["activity_count"] += 1
        user["warned"] = False

        bot.send_message(chat_id,
            checkin_msg(name, uid, text,
            "Remember to click Back to Seat when you return.",
            details=f"\n⏱ Time Limit: {format_time(LIMITS[text])}\n",
            result=f"{text} Started"),
            reply_markup=menu()
        )

    elif text == "🔙 Back to Seat":
        if not user["activity"]:
            bot.send_message(chat_id, "⚠️ No active task!", reply_markup=menu())
            return

        used = time.time() - user["start_time"]
        user["total"] += used
        activity = user["activity"]

        extra = used - LIMITS[activity]
        warning = f"\n⚠️ Exceeded: {format_time(extra)}" if extra > 0 else ""

        bot.send_message(chat_id,
            checkin_msg(name, uid, "Back to Seat",
            "Stay focused! You can do it 💪",
            details=f"\n📌 Activity: {activity}\n⏱ Used: {format_time(used)}\n📊 Total Today: {format_time(user['total'])}{warning}\n",
            result="Back to Seat Successfully"),
            reply_markup=menu()
        )

        user["activity"] = None
        user["start_time"] = None

    elif text == "⚫ Off Work":
        if not user["working"]:
            bot.send_message(chat_id, "⚠️ Work not started!", reply_markup=menu())
            return

        user["working"] = False
        user["activity"] = None
        user["start_time"] = None

        bot.send_message(chat_id,
            checkin_msg(name, uid, "Off Work",
            "See you tomorrow! Rest well 😴",
            details=f"\n📊 Total Time: {format_time(user['total'])}\n🔢 Activities Done: {user['activity_count']}\n",
            result="Work Finished. Good job 👍"),
            reply_markup=menu()
        )

    else:
        bot.send_message(chat_id, "❓ Unknown command", reply_markup=menu())

    save_data(data)

# ================= WEB ================= #
@app.route("/")
def home():
    return "Bot Running ✅"

# ================= RUN ================= #
def run_bot():
    bot.polling(none_stop=True)

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_bot).start()
run_web()
