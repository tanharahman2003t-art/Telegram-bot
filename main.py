import telebot
from telebot.types import ReplyKeyboardMarkup
from datetime import datetime
import time, json, os, threading

# ================= CONFIG ================= #
TOKEN = "8778891878:AAGUsVF7XOs9iTv4hfxnLbpidDHBlv8tVjY"
bot = telebot.TeleBot(TOKEN)

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
    return json.load(open(DATA_FILE))

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"), indent=4)

# ================= UI ================= #
def menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🟢 Start Work", "⚫ Off Work")
    m.row("🚿 Toilet", "☕ Break", "🍽 Eat")
    m.row("🔙 Back to Seat")
    m.row("📊 My Stats", "🏆 Leaderboard")
    return m

def now():
    return datetime.now().strftime("%m/%d %H:%M:%S")

def format_time(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m}m {s}s" if m else f"{s}s"

def checkin_msg(name, uid, action, hint, details="", result=""):
    return f"""👤 {name}
User ID: {uid}
----------
✅ Check-In Succeeded: {action} - {now()}
{details}
Hint: {hint}

----------
✅ {result}"""

# ================= AUTO WARNING ================= #
def auto_warning():
    while True:
        data = load_data()
        for uid, user in data["users"].items():
            if user.get("activity") and user.get("start_time"):
                used = time.time() - user["start_time"]
                limit = LIMITS[user["activity"]]

                try:
                    if used > limit and not user.get("warn100"):
                        bot.send_message(int(uid), "🚨 Limit Exceeded!")
                        user["warn100"] = True

                    elif used > limit * 0.8 and not user.get("warn80"):
                        bot.send_message(int(uid), "⚠️ Almost limit reached")
                        user["warn80"] = True
                except:
                    pass

        save_data(data)
        time.sleep(10)

threading.Thread(target=auto_warning, daemon=True).start()

# ================= DAILY REPORT ================= #
def daily_report():
    while True:
        now_time = datetime.now().strftime("%H:%M")
        if now_time == "23:59":
            data = load_data()
            for uid, u in data["users"].items():
                try:
                    bot.send_message(int(uid),
                        f"📊 Daily Report\n⏱ Total: {format_time(u['total'])}\n🔢 Activities: {u['activity_count']}")
                except:
                    pass
            time.sleep(60)
        time.sleep(30)

threading.Thread(target=daily_report, daemon=True).start()

# ================= BOT ================= #
@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, "Welcome 👇", reply_markup=menu())

@bot.message_handler(commands=['history'])
def history(msg):
    data = load_data()
    uid = str(msg.from_user.id)
    if uid not in data["users"]:
        bot.send_message(msg.chat.id, "No history")
        return

    logs = data["users"][uid].get("logs", [])
    text = "📅 History\n"
    for l in logs[-10:]:
        text += f"{l}\n"

    bot.send_message(msg.chat.id, text)

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
            "total": 0,
            "activity_count": 0,
            "start_count": 0,
            "logs": []
        }

    user = data["users"][uid]

    # Anti spam
    if user.get("last") and time.time() - user["last"] < 1:
        bot.send_message(chat_id, "⚠️ Slow down bro 😅")
        return
    user["last"] = time.time()

    if text == "🟢 Start Work":
        user["working"] = True
        user["start_count"] += 1
        user["logs"].append(f"🟢 Start - {now()}")

        bot.send_message(chat_id,
            checkin_msg(name, uid, "Start Work",
            "Stay consistent 💪",
            result="Work Started"),
            reply_markup=menu())

    elif text in LIMITS:
        user["activity"] = text
        user["start_time"] = time.time()
        user["activity_count"] += 1
        user["logs"].append(f"{text} - {now()}")
        user["warn80"] = False
        user["warn100"] = False

        bot.send_message(chat_id,
            checkin_msg(name, uid, text,
            "Return fast!",
            details=f"\n⏱ Limit: {format_time(LIMITS[text])}",
            result=f"{text} Started"),
            reply_markup=menu())

    elif text == "🔙 Back to Seat":
        if user["activity"]:
            used = time.time() - user["start_time"]
            user["total"] += used
            act = user["activity"]

            bot.send_message(chat_id,
                checkin_msg(name, uid, "Back to Seat",
                "Focus again 💪",
                details=f"\n📌 {act}\n⏱ Used: {format_time(used)}\n📊 Total: {format_time(user['total'])}",
                result="Back Successfully"),
                reply_markup=menu())

            user["activity"] = None

    elif text == "⚫ Off Work":
        user["working"] = False
        user["logs"].append(f"⚫ Off - {now()}")

        bot.send_message(chat_id,
            checkin_msg(name, uid, "Off Work",
            "Good rest 😴",
            details=f"\n📊 Total: {format_time(user['total'])}",
            result="Finished"),
            reply_markup=menu())

    elif text == "📊 My Stats":
        bot.send_message(chat_id,
            f"📊 Stats\nStart: {user['start_count']}\nActivities: {user['activity_count']}\nTotal: {format_time(user['total'])}",
            reply_markup=menu())

    elif text == "🏆 Leaderboard":
        ranking = sorted(data["users"].items(), key=lambda x: x[1]["total"])
        msg = "🏆 Productivity\n"
        for i, (u, d) in enumerate(ranking[:5], 1):
            msg += f"{i}. {u} → {format_time(d['total'])}\n"
        bot.send_message(chat_id, msg, reply_markup=menu())

    save_data(data)

bot.polling()
