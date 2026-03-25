
    
    
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

TOKEN = "8625498364:AAHW0ieQt2WQfn6eEEmw93_OMji5Enqwcp4"
CHANNEL_ID = "@SaarDimona"


TEAMS = ["צוות 1", "צוות 2", "צוות 3", "צוות רפואה", "מודיעין אוכלוסייה"]
COMMANDERS = ["יבגני", "יהונתן", "אסף", "יניב", "סרג", "אבישג"]

users = {}
status = {}
locations = {}

def is_commander(name):
    return name in COMMANDERS

def get_keyboard(user):
    buttons = [
        ["✅ הגעתי לזירה", "❌ יצאתי מהזירה"],
        ["📍 שלח מיקום", "📊 מי בזירה"]
    ]

    if is_commander(user["name"]):
        buttons += [
            ["🚨 הקפצת חירום"],
            ["🛑 סיום אירוע"],
            ["🗺️ הצג מיקומים"]
        ]

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ברוך הבא 🚑\nרשום שם:")
    context.user_data["step"] = "name"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text if update.message.text else ""

    # ===== הרשמה =====
    if context.user_data.get("step") == "name":
        context.user_data["name"] = text
        keyboard = [[team] for team in TEAMS]

        await update.message.reply_text("בחר צוות:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

        context.user_data["step"] = "team"
        return

    elif context.user_data.get("step") == "team":
        context.user_data["team"] = text
        users[user_id] = context.user_data.copy()

        await update.message.reply_text("נרשמת ✅",
            reply_markup=get_keyboard(context.user_data))

        context.user_data["step"] = "done"
        return

    user = users.get(user_id)
    if not user:
        await update.message.reply_text("לא רשום ❌ /start")
        return

    # ===== הגעה =====
    if text == "✅ הגעתי לזירה":
        status[user_id] = True
        await context.bot.send_message(chat_id=CHANNEL_ID,
            text=f"{user['name']} | {user['team']} הגיע 🟢")

    # ===== יציאה =====
    elif text == "❌ יצאתי מהזירה":
        status[user_id] = False
        await context.bot.send_message(chat_id=CHANNEL_ID,
            text=f"{user['name']} | {user['team']} יצא 🔴")

    # ===== מי בזירה =====
    elif text == "📊 מי בזירה":
        msg = ""
        count = 0

        for team in TEAMS:
            msg += f"\n{team}:\n"
            for uid, st in status.items():
                if st and users.get(uid) and users[uid]["team"] == team:
                    msg += f"- {users[uid]['name']}\n"
                    count += 1

        msg += f"\nסה\"כ: {count}"
        await update.message.reply_text(msg)

    # ===== שלח מיקום =====
    elif text == "📍 שלח מיקום":
        if not is_commander(user["name"]):
            await update.message.reply_text("אין הרשאה ❌")
            return

        button = [[KeyboardButton("שלח מיקום", request_location=True)]]
        await update.message.reply_text("שלח מיקום:",
            reply_markup=ReplyKeyboardMarkup(button, resize_keyboard=True))
        return

    # ===== קבלת מיקום =====
    elif update.message.location:
        loc = update.message.location
        locations[user_id] = (loc.latitude, loc.longitude)

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{user['name']} 📍 https://maps.google.com/?q={loc.latitude},{loc.longitude}"
        )

    # ===== הצג מיקומים =====
    elif text == "🗺️ הצג מיקומים":
        if not is_commander(user["name"]):
            return

        if not locations:
            await update.message.reply_text("אין מיקומים")
            return

        msg = "🗺️ מיקומים:\n\n"
        for uid, loc in locations.items():
            if users.get(uid):
                msg += f"{users[uid]['name']}:\nhttps://maps.google.com/?q={loc[0]},{loc[1]}\n\n"

        await update.message.reply_text(msg)

    # ===== הקפצת חירום =====
    elif text == "🚨 הקפצת חירום":
        if not is_commander(user["name"]):
            return

        await update.message.reply_text("כתוב הודעה:")
        context.user_data["step"] = "alert"
        return

    elif context.user_data.get("step") == "alert":
        msg = f"🚨 הקפצה 🚨\n{text}"

        for uid in users:
            await context.bot.send_message(chat_id=uid, text=msg)

        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)

        context.user_data["step"] = "done"
        return

    # ===== סיום אירוע =====
    elif text == "🛑 סיום אירוע":
        if not is_commander(user["name"]):
            return

        doc = SimpleDocTemplate("report.pdf")
        styles = getSampleStyleSheet()
        content = []

        content.append(Paragraph("דו\"ח חילוץ", styles["Title"]))
        content.append(Paragraph(datetime.now().strftime("%d/%m %H:%M"), styles["Normal"]))

        for team in TEAMS:
            content.append(Paragraph(f"<br/><b>{team}</b>", styles["Normal"]))
            for uid, u in users.items():
                if u["team"] == team:
                    st = "בזירה" if status.get(uid) else "יצא"
                    content.append(Paragraph(f"{u['name']} - {st}", styles["Normal"]))

        doc.build(content)

        for uid, u in users.items():
            if is_commander(u["name"]):
                await context.bot.send_document(chat_id=uid, document=open("report.pdf", "rb"))

        await context.bot.send_message(chat_id=CHANNEL_ID, text="🛑 האירוע הסתיים")

        status.clear()
        locations.clear()

    # תמיד מחזיר תפריט
    await update.message.reply_text("בחר פעולה:",
        reply_markup=get_keyboard(user))


# ===== שרת קטן ל-Render =====
def run_web():
    port = int(os.environ.get("PORT", 10000))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot running")

    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle))

    app.run_polling()


if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    main()