import telebot
from telebot.types import ReplyKeyboardMarkup
from datetime import datetime
import time

TOKEN = "8778891878:AAGUsVF7XOs9iTv4hfxnLbpidDHBlv8tVjY"

bot = telebot.TeleBot(TOKEN)

user_data = {}
work_log = []
activity_log = []

LIMITS = {
    "🚿 Toilet": 10 * 60,
    "☕ Break": 15 * 60,
    "🍽 Eat": 30 * 60
}

def menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🟢 Start Work", "⚫ Off Work")
    markup.row("🚿 Toilet", "☕ Break", "🍽 Eat")
    markup.row("🔙 Back to Seat")
    return markup

def format_time(seconds):
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    if minutes > 0:
        return f"{minutes} min {sec} sec"
    return f"{sec} sec"

def now():
    return datetime.now().strftime("%d %b %Y | %I:%M %p")

def checkin_time():
    return datetime.now().strftime("%m/%d %H:%M:%S")

def checkin_msg(name, user_id, action, hint, details="", result=""):
    return f"""👤 {name}
User ID: {user_id}
----------
✅ Check-In Succeeded: {action} - {checkin_time()}
{details}
Hint: {hint}

----------
✅ {result}"""

@bot.message_handler(commands=['report'])
def report(message):
    if not work_log:
        bot.send_message(message.chat.id, "📋 No records yet.")
        return

    lines = ["📋 Work Log\n"]
    for i, entry in enumerate(work_log, 1):
        lines.append(
            f"{i}. 👤 {entry['name']} (ID: {entry['user_id']})\n"
            f"   🕒 {entry['time']}\n"
            f"   🔢 Start #{entry['start_count']}\n"
        )
    lines.append(f"\n📊 Total Start Work events: {len(work_log)}")

    user_counts = {}
    for entry in work_log:
        key = f"{entry['name']} ({entry['user_id']})"
        user_counts[key] = user_counts.get(key, 0) + 1

    lines.append("\n👥 Per User Summary:")
    for user, count in user_counts.items():
        lines.append(f"  • {user} → {count}x Start Work")

    bot.send_message(message.chat.id, "\n".join(lines))

@bot.message_handler(func=lambda message: True)
def handle(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    name = message.from_user.first_name
    username = message.from_user.username or "N/A"
    text = message.text

    if user_id not in user_data:
        user_data[user_id] = {
            "working": False,
            "activity": None,
            "start_time": None,
            "total": 0,
            "start_count": 0,
            "activity_count": 0
        }

    user = user_data[user_id]

    if text == "🟢 Start Work":
        if user["working"]:
            bot.send_message(chat_id, "⚠️ Already working!", reply_markup=menu())
            return
        user["working"] = True
        user["start_count"] += 1
        work_log.append({"name": name, "username": username, "user_id": user_id, "time": now(), "start_count": user["start_count"]})
        bot.send_message(chat_id, checkin_msg(name, user_id, "Start Work", "Remember to check in when Off Work arrives.", result="Work Started Successfully"), reply_markup=menu())

    elif not user["working"]:
        bot.send_message(chat_id, "⚠️ Please click 'Start Work' first!", reply_markup=menu())
        return

    elif text in ["🚿 Toilet", "☕ Break", "🍽 Eat"]:
        if user["activity"] is not None:
            bot.send_message(chat_id, f"⚠️ You are already in {user['activity']}!", reply_markup=menu())
            return
        user["activity"] = text
        user["start_time"] = time.time()
        user["activity_count"] += 1
        activity_log.append({"name": name, "user_id": user_id, "activity": text, "time": now()})
        bot.send_message(chat_id, checkin_msg(name, user_id, text, "Remember to click Back to Seat when you return.", details=f"\n⏱️ Time Limit: {format_time(LIMITS[text])}\n", result=f"{text} Started"), reply_markup=menu())

    elif text == "🔙 Back to Seat":
        if user["activity"] is None:
            bot.send_message(chat_id, "⚠️ No active task!", reply_markup=menu())
            return
        used = time.time() - user["start_time"]
        total = user["total"] + used
        extra = used - LIMITS[user["activity"]]
        user["total"] = total
        activity = user["activity"]
        user["activity"] = None
        user["start_time"] = None
        warning = f"\n⚠️ Exceeded: {format_time(extra)}" if extra > 0 else ""
        bot.send_message(chat_id, checkin_msg(name, user_id, "Back to Seat", "Stay focused! You can do it 💪", details=f"\n📌 Activity: {activity}\n⏱️ Used: {format_time(used)}\n📊 Total Today: {format_time(total)}{warning}\n", result="Back to Seat Successfully"), reply_markup=menu())

    elif text == "⚫ Off Work":
        if not user["working"]:
            bot.send_message(chat_id, "⚠️ Work not started!", reply_markup=menu())
            return
        user["working"] = False
        user["activity"] = None
        user["start_time"] = None
        bot.send_message(chat_id, checkin_msg(name, user_id, "Off Work", "See you tomorrow! Rest well 😴", details=f"\n📊 Total Break Time: {format_time(user['total'])}\n🔢 Activities Done: {user['activity_count']}\n", result="Work Finished. Good job 👍"), reply_markup=menu())

    else:
        bot.send_message(chat_id, "❓ Unknown command", reply_markup=menu())

bot.polling()
