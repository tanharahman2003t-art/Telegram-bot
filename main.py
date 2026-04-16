import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from datetime import datetime
import time, json, os, threading
from flask import Flask, request, jsonify, render_template_string

# ===== CONFIG =====
TOKEN = "8778891878:AAGUsVF7XOs9iTv4hfxnLbpidDHBlv8tVjY"
WEB_URL = "https://your-railway-url.up.railway.app"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

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
    m.row("📊 My Stats", "🏆 Leaderboard")
    return m

# ===== HELPER =====
def now():
    return datetime.now().strftime("%m/%d %H:%M:%S")

def format_time(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m} min {s} sec" if m else f"{s} sec"

def checkin_msg(name, uid, action, hint, details="", result=""):
    return f"""👤 {name}
User ID: {uid}
----------
✅ Check-In Succeeded: {action} - {now()}
{details}
Hint: {hint}

----------
✅ {result}"""

# ===== LIVE TIMER =====
def live_timer(chat_id, msg_id, uid):
    while True:
        data = load_data()
        user = data["users"].get(uid)

        if not user or not user.get("activity"):
            break

        used = time.time() - user["start_time"]

        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=f"⏱ {user['activity']} Running...\n{format_time(used)}"
            )
        except:
            pass

        time.sleep(5)

# ===== BOT =====
@bot.message_handler(commands=['start'])
def start(msg):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🌐 Open Dashboard",
        web_app=WebAppInfo(f"{WEB_URL}/?uid={msg.from_user.id}")))

    bot.send_message(msg.chat.id, "Welcome 👇", reply_markup=kb)
    bot.send_message(msg.chat.id, "Use menu 👇", reply_markup=menu())

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
            "start_count": 0,
            "activity_count": 0
        }

    user = data["users"][uid]

    # START
    if text == "🟢 Start Work":
        if user["working"]:
            bot.send_message(chat_id, "⚠️ Already working!", reply_markup=menu())
            return

        user["working"] = True
        user["start_count"] += 1

        bot.send_message(chat_id,
            checkin_msg(name, uid, "Start Work",
            "Stay focused 💪",
            result="Work Started Successfully"),
            reply_markup=menu())

    elif not user["working"]:
        bot.send_message(chat_id, "⚠️ Start Work first!", reply_markup=menu())
        return

    # ACTIVITY
    elif text in LIMITS:
        if user["activity"]:
            bot.send_message(chat_id, f"⚠️ Already in {user['activity']}!", reply_markup=menu())
            return

        user["activity"] = text
        user["start_time"] = time.time()
        user["activity_count"] += 1

        msg = bot.send_message(chat_id,
            f"⏱ {text} Started...\n0 sec",
            reply_markup=menu())

        threading.Thread(target=live_timer, args=(chat_id, msg.message_id, uid)).start()

    # BACK
    elif text == "🔙 Back to Seat":
        if not user["activity"]:
            bot.send_message(chat_id, "⚠️ No active task!", reply_markup=menu())
            return

        used = time.time() - user["start_time"]
        user["total"] += used
        act = user["activity"]

        user["activity"] = None

        bot.send_message(chat_id,
            checkin_msg(name, uid, "Back to Seat",
            "Stay focused 💪",
            details=f"\n📌 Activity: {act}\n⏱ Used: {format_time(used)}\n📊 Total Today: {format_time(user['total'])}\n",
            result="Back to Seat Successfully"),
            reply_markup=menu())

    # OFF
    elif text == "⚫ Off Work":
        user["working"] = False
        user["activity"] = None

        bot.send_message(chat_id,
            checkin_msg(name, uid, "Off Work",
            "Good rest 😴",
            details=f"\n📊 Total: {format_time(user['total'])}\n",
            result="Work Finished"),
            reply_markup=menu())

    # STATS
    elif text == "📊 My Stats":
        bot.send_message(chat_id,
            f"📊 Stats\nStart: {user['start_count']}\nActivities: {user['activity_count']}\nTotal: {format_time(user['total'])}",
            reply_markup=menu())

    # LEADERBOARD
    elif text == "🏆 Leaderboard":
        ranking = sorted(data["users"].items(), key=lambda x: x[1]["total"])
        msg = "🏆 Leaderboard\n"
        for i, (u, d) in enumerate(ranking[:5], 1):
            msg += f"{i}. {u} → {format_time(d['total'])}\n"
        bot.send_message(chat_id, msg, reply_markup=menu())

    save_data(data)

# ===== WEB =====
HTML = """
<!DOCTYPE html>
<html>
<body style="background:black;color:white;text-align:center">
<h2>Dashboard</h2>
<p>Bot Connected ✅</p>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

# ===== RUN =====
def run_bot():
    bot.polling(none_stop=True)

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_bot).start()
run_web()
