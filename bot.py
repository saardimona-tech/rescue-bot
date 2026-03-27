from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

# ===== נסיון פונט + עברית =====
try:
    from reportlab.pdfbase import ttfonts, pdfmetrics
    from bidi.algorithm import get_display
    pdfmetrics.registerFont(ttfonts.TTFont('Hebrew', 'Rubik-Regular.ttf'))
    def fix(text): return get_display(text)
except:
    def fix(text): return text  # fallback בלי פונט

TOKEN = "8625498364:AAEdQyQMRa_PQUTBnGVmf8sPLC6B_-GDPRI"
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
arrival_times = {}
leave_times = {}

# ===== server =====
def run_server():
    port = int(os.environ.get("PORT", 10000))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot running")

    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Server running on port {port}")
    server.serve_forever()

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

# ===== PDF =====
def generate_pdf():
    doc = SimpleDocTemplate("report.pdf")
    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph(fix("דו\"ח אירוע חילוץ"), styles["Title"]))

    for team in TEAMS:
        content.append(Paragraph(fix(f"\n{team}"), styles["Heading2"]))

        for uid, user in users.items():
            if user["team"] == team:
                name = user["name"]
                arrival = arrival_times.get(uid, "-")
                leave = leave_times.get(uid, "עדיין בזירה")

                line = f"{name} | נכנס: {arrival} | יצא: {leave}"
                content.append(Paragraph(fix(line), styles["Normal"]))

    doc.build(content)

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

        await update.message.reply_text("📍 מיקום התקבל!", reply_markup=get_keyboard(user))
        return

    # ===== הרשמה =====
    if context.user_data.get("step") == "name":
        context.user_data["name"] = text
        keyboard = [[team] for team in TEAMS]

        await update.message.reply_text("בחר צוות:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        context.user_data["step"] = "team"
        return

    elif context.user_data.get("step") == "team":
        context.user_data["team"] = text
        users[user_id] = context.user_data.copy()

        await update.message.reply_text("בחר פעולה:", reply_markup=get_keyboard(users[user_id]))
        context.user_data["step"] = "done"
        return

    if not user:
        await update.message.reply_text("שלח /start")
        return

    # ===== הגעה =====
    if text == "✅ הגעתי לזירה":
        status[user_id] = True
        arrival_times[user_id] = datetime.now().strftime("%H:%M")

        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{user['name']} הגיע 🟢")

    # ===== יציאה =====
    elif text == "❌ יצאתי מהזירה":
        status[user_id] = False
        leave_times[user_id] = datetime.now().strftime("%H:%M")

        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{user['name']} יצא 🔴")

    # ===== מי בזירה =====
    elif text == "📊 מי בזירה":
        result = ""
        total = 0
        counter = 1

        for team in TEAMS:
            result += f"\n🔹 {team}:\n"
            team_count = 0

            for uid, st in status.items():
                if st and users.get(uid) and users[uid]["team"] == team:
                    result += f"{counter}. {users[uid]['name']}\n"
                    counter += 1
                    total += 1
                    team_count += 1

            result += f"סה\"כ בצוות: {team_count}\n"

        result += f"\n👥 סה\"כ בזירה: {total}"
        await update.message.reply_text(result)

    # ===== שלח מיקום =====
    elif text == "📍 שלח מיקום":
        button = [[KeyboardButton("שלח מיקום", request_location=True)]]
        await update.message.reply_text("שלח מיקום:", reply_markup=ReplyKeyboardMarkup(button, resize_keyboard=True))
        return

    # ===== הצגת מיקומים =====
    elif text == "🗺️ הצג מיקומים":
        if not is_commander(user["name"]):
            return

        msg = "🗺️ מיקומים:\n\n"
        for uid, loc in locations.items():
            if users.get(uid) and status.get(uid):
                msg += f"{users[uid]['name']}:\nhttps://maps.google.com/?q={loc[0]},{loc[1]}\n\n"

        await update.message.reply_text(msg)

    # ===== סיום אירוע =====
    elif text == "🛑 סיום אירוע":
        if not is_commander(user["name"]):
            return

        generate_pdf()

        for uid, u in users.items():
            if is_commander(u["name"]):
                await context.bot.send_document(chat_id=uid, document=open("report.pdf", "rb"))

        for uid in users:
            await context.bot.send_message(chat_id=uid, text="🛑 האירוע הסתיים\nשלח /start")

        users.clear()
        status.clear()
        locations.clear()
        arrival_times.clear()
        leave_times.clear()

        await update.message.reply_text("האירוע נסגר ✅")
        return

    await update.message.reply_text("בחר פעולה:", reply_markup=get_keyboard(user))

# ===== run =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle))

    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    main()