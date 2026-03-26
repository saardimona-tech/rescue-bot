
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

TOKEN = "8625498364:AAHW0ieQt2WQfn6eEEmw93_OMji5Enqwcp4"
CHANNEL_ID = "@SaarDimoma"

TEAMS = [
    "צוות 1",
    "צוות 2",
    "צוות 3",
    "צוות רפואה",
    "מודיעין אוכלוסייה",
    "צוות פיקוד"
]

COMMANDERS = ["יבגני", "יהונתן", "אסף", "יניב", "סרג", "אבישג"]

users = {}
status = {}
locations = {}

# ===== server (Render) =====
def run_server():
    port = int(os.environ.get("PORT", 10000))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot running")

    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

threading.Thread(target=run_server).start()

# ===== helpers =====
def is_commander(name):
    return name in COMMANDERS

def get_keyboard(user):
    buttons = [
        ["✅ הגעתי לזירה", "❌ יצאתי מהזירה"],
        ["📍 שלח מיקום", "📊 מי בזירה"]
    ]

    if is_commander(user["name"]):
        buttons.append(["🚨 הקפצת חירום"])
        buttons.append(["🛑 סיום אירוע"])
        buttons.append(["🗺️ הצג מיקומים"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ===== start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ברוך הבא 🚑\nרשום שם:")
    context.user_data["step"] = "name"

# ===== main =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text if update.message.text else ""
    user = users.get(user_id)

    # ===== מיקום =====
    if update.message.location:
        if not user:
            await update.message.reply_text("שלח /start קודם")
            return

        loc = update.message.location
        locations[user_id] = (loc.latitude, loc.longitude)

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{user['name']} 📍 https://maps.google.com/?q={loc.latitude},{loc.longitude}"
        )

        await update.message.reply_text("מיקום נשלח ✅", reply_markup=get_keyboard(user))
        return

    # ===== הרשמה =====
    if context.user_data.get("step") == "name":
        context.user_data["name"] = text
        keyboard = [[team] for team in TEAMS]

        await update.message.reply_text(
            "בחר צוות:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        context.user_data["step"] = "team"
        return

    elif context.user_data.get("step") == "team":
        context.user_data["team"] = text
        users[user_id] = context.user_data.copy()

        await update.message.reply_text(
            "בחר פעולה:",
            reply_markup=get_keyboard(users[user_id])
        )
        context.user_data["step"] = "done"
        return

    if not user:
        await update.message.reply_text("שלח /start")
        return

    # ===== הגעה =====
    if text == "✅ הגעתי לזירה":
        status[user_id] = True
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{user['name']} הגיע 🟢")

    # ===== יציאה =====
    elif text == "❌ יצאתי מהזירה":
        status[user_id] = False
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{user['name']} יצא 🔴")

    # ===== מי בזירה =====
    elif text == "📊 מי בזירה":
        result = ""
        total = 0
        global_counter = 1

        for team in TEAMS:
            result += f"\n🔹 {team}:\n"
            team_count = 0

            for uid, st in status.items():
                if st and users.get(uid) and users[uid]["team"] == team:
                    result += f"{global_counter}. {users[uid]['name']}\n"
                    team_count += 1
                    total += 1
                    global_counter += 1

            result += f"סה\"כ בצוות: {team_count}\n"

        result += f"\n👥 סה\"כ בזירה: {total}"

        await update.message.reply_text(result)

    # ===== שלח מיקום =====
    elif text == "📍 שלח מיקום":
        if not is_commander(user["name"]):
            await update.message.reply_text("אין הרשאה ❌")
            return

        button = [[KeyboardButton("שלח מיקום", request_location=True)]]

        await update.message.reply_text(
            "שלח מיקום:",
            reply_markup=ReplyKeyboardMarkup(button, resize_keyboard=True)
        )
        return

    # ===== הצגת מיקומים =====
    elif text == "🗺️ הצג מיקומים":
        if not is_commander(user["name"]):
            return

        msg = "🗺️ מיקומי מחלצים בזירה:\n\n"
        found = False

        for uid, loc in locations.items():
            if users.get(uid) and status.get(uid):
                name = users[uid]["name"]
                msg += f"{name}:\nhttps://maps.google.com/?q={loc[0]},{loc[1]}\n\n"
                found = True

        if not found:
            await update.message.reply_text("אין מיקומים של מחלצים בזירה ❌")
            return

        await update.message.reply_text(msg)

    # ===== הקפצת חירום =====
    elif text == "🚨 הקפצת חירום":
        if not is_commander(user["name"]):
            return

        await update.message.reply_text("כתוב הודעה:")
        context.user_data["step"] = "alert"
        return

    elif context.user_data.get("step") == "alert":
        msg = f"🚨 {text}"

        for uid in users:
            try:
                await context.bot.send_message(chat_id=uid, text=msg)
            except:
                pass

        context.user_data["step"] = "done"
        return

    # ===== סיום אירוע =====
    elif text == "🛑 סיום אירוע":
        if not is_commander(user["name"]):
            return

        for uid in users:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text="🛑 האירוע הסתיים\nשלח /start להתחלה חדשה"
                )
            except:
                pass

        users.clear()
        status.clear()
        locations.clear()
        context.user_data.clear()

        await update.message.reply_text("האירוע נסגר ✅")
        return

    # ===== תמיד מחזיר תפריט =====
    await update.message.reply_text("בחר פעולה:", reply_markup=get_keyboard(user))

# ===== run =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle))

    app.run_polling()

if __name__ == "__main__":
    main()