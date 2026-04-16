import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
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
    m.row("📊 My Stats", "🏆 Leaderboard")
    return m

def format_time(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m}m {s}s" if m else f"{s}s"

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
                        bot.send_message(int(uid), f"⚠️ Time exceeded for {user['activity']}")
                        user["warned"] = True

            save_data(data)
        except:
            pass
        time.sleep(10)

threading.Thread(target=auto_warning, daemon=True).start()

# ================= BOT ================= #
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(
        "🚀 Open Dashboard",
        web_app=WebAppInfo(f"{WEB_URL}/?uid={message.from_user.id}")
    ))

    bot.send_message(message.chat.id, "Welcome 👇", reply_markup=keyboard)

@bot.message_handler(func=lambda m: True)
def handle(message):
    data = load_data()
    uid = str(message.from_user.id)
    chat_id = message.chat.id
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
        user["working"] = True
        user["start_count"] += 1

    elif text in LIMITS:
        user["activity"] = text
        user["start_time"] = time.time()
        user["activity_count"] += 1
        user["warned"] = False

    elif text == "🔙 Back to Seat":
        if user["activity"]:
            used = time.time() - user["start_time"]
            user["total"] += used
            user["activity"] = None

    elif text == "⚫ Off Work":
        user["working"] = False
        user["activity"] = None

    elif text == "📊 My Stats":
        bot.send_message(chat_id,
            f"Start: {user['start_count']}\nActivities: {user['activity_count']}\nTotal: {format_time(user['total'])}",
            reply_markup=menu()
        )
        return

    elif text == "🏆 Leaderboard":
        ranking = sorted(data["users"].items(), key=lambda x: x[1]["start_count"], reverse=True)
        msg = "🏆 Leaderboard\n"
        for i, (u, d) in enumerate(ranking[:5], 1):
            msg += f"{i}. {u} → {d['start_count']}x\n"
        bot.send_message(chat_id, msg, reply_markup=menu())
        return

    save_data(data)
    bot.send_message(chat_id, "✅ Updated", reply_markup=menu())

# ================= WEB ================= #
HTML = """
<h2 style="text-align:center;">🚀 Dashboard</h2>
<button onclick="send('start')">Start</button>
<button onclick="send('off')">Off</button>
<script>
const uid = new URLSearchParams(window.location.search).get("uid");
function send(a){
fetch('/api',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({uid:uid,action:a})})
.then(r=>r.json()).then(d=>alert(d.msg))
}
</script>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/api", methods=["POST"])
def api():
    data = load_data()
    req = request.json
    uid = str(req["uid"])
    action = req["action"]

    if uid not in data["users"]:
        data["users"][uid] = {"working": False, "start_count": 0}

    user = data["users"][uid]

    if action == "start":
        user["working"] = True
        user["start_count"] += 1
    elif action == "off":
        user["working"] = False

    save_data(data)
    return jsonify({"msg": "✅ Done"})

# ================= RUN ================= #
def run_bot():
    bot.polling(none_stop=True)

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_bot).start()
run_web()
