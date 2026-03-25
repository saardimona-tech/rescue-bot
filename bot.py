


from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

TOKEN = "8625498364:AAHW0ieQt2WQfn6eEEmw93_OMji5Enqwcp4"
CHANNEL_ID = "@SaarDimona"

TEAMS = ["צוות 1", "צוות 2", "צוות 3", "צוות רפואה", "מודיעין אוכלוסייה"]
COMMANDERS = ["יבגני", "יהונתן", "אסף", "יניב", "סרג", "אבישג"]

users = {}
status = {}
locations = {}
arrival_times = {}
leave_times = {}

def is_commander(name):
    return name in COMMANDERS

def get_main_keyboard(user):
    buttons = [
        ["✅ הגעתי לזירה", "❌ יצאתי מהזירה"],
        ["📍 שלח מיקום", "📊 מי בזירה"]
    ]

    if is_commander(user["name"]):
        buttons.append(["🚨 הקפצת חירום"])
        buttons.append(["🛑 סיום אירוע"])
        buttons.append(["🗺️ הצג מיקומים"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ברוך הבא למערכת חילוץ 🚑\nרשום שם:")
    context.user_data["step"] = "name"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # הרשמה
    if context.user_data.get("step") == "name":
        context.user_data["name"] = text
        keyboard = [[team] for team in TEAMS]

        await update.message.reply_text(
            "בחר צוות:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

        context.user_data["step"] = "team"

    elif context.user_data.get("step") == "team":
        context.user_data["team"] = text
        users[user_id] = context.user_data.copy()

        await update.message.reply_text(
            "בחר פעולה:",
            reply_markup=get_main_keyboard(context.user_data)
        )

        context.user_data["step"] = "done"

    # הגעה
    elif text == "✅ הגעתי לזירה":
        user = users.get(user_id)
        status[user_id] = True
        arrival_times[user_id] = datetime.now()

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{user['name']} | {user['team']} הגיע לזירה 🟢"
        )

    # יציאה
    elif text == "❌ יצאתי מהזירה":
        user = users.get(user_id)
        status[user_id] = False
        leave_times[user_id] = datetime.now()

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{user['name']} | {user['team']} יצא מהזירה 🔴"
        )

    # מי בזירה
    elif text == "📊 מי בזירה":
        result = ""
        count = 0

        for team in TEAMS:
            result += f"\n{team}:\n"
            for uid, st in status.items():
                if st and users[uid]["team"] == team:
                    result += f"- {users[uid]['name']}\n"
                    count += 1

        result += f"\nסה\"כ: {count}"
        await update.message.reply_text(result)

    # שליחת מיקום
    elif text == "📍 שלח מיקום":
        user = users.get(user_id)

        if not is_commander(user["name"]):
            await update.message.reply_text("אין הרשאה לשלוח מיקום ❌")
            return

        button = [[KeyboardButton("שלח מיקום", request_location=True)]]

        await update.message.reply_text(
            "שלח מיקום:",
            reply_markup=ReplyKeyboardMarkup(button, resize_keyboard=True)
        )

    # קבלת מיקום
    elif update.message.location:
        user = users.get(user_id)
        loc = update.message.location

        locations[user_id] = (loc.latitude, loc.longitude)

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{user['name']} שלח מיקום 📍 https://maps.google.com/?q={loc.latitude},{loc.longitude}"
        )

        # החזרת הכפתורים 🔥
        await update.message.reply_text(
            "בחר פעולה:",
            reply_markup=get_main_keyboard(user)
        )

    # הצגת מיקומים (מפקדים בלבד)
    elif text == "🗺️ הצג מיקומים":
        user = users.get(user_id)

        if not is_commander(user["name"]):
            return

        if not locations:
            await update.message.reply_text("אין מיקומים עדיין")
            return

        msg = "🗺️ מיקומי מחלצים:\n\n"

        for uid, loc in locations.items():
            name = users[uid]["name"]
            msg += f"{name}:\nhttps://maps.google.com/?q={loc[0]},{loc[1]}\n\n"

        await update.message.reply_text(msg)

    # הקפצת חירום
    elif text == "🚨 הקפצת חירום":
        user = users.get(user_id)

        if not is_commander(user["name"]):
            return

        await update.message.reply_text("כתוב הודעת חירום:")
        context.user_data["step"] = "alert"

    elif context.user_data.get("step") == "alert":
        msg = f"🚨 הקפצת חירום 🚨\n{text}"

        for uid in users:
            await context.bot.send_message(chat_id=uid, text=msg)

        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)

        context.user_data["step"] = "done"

    # סיום אירוע + PDF
    elif text == "🛑 סיום אירוע":
        user = users.get(user_id)

        if not is_commander(user["name"]):
            return

        # יצירת PDF
        doc = SimpleDocTemplate("report.pdf")
        styles = getSampleStyleSheet()

        content = []

        content.append(Paragraph("דו\"ח אירוע חילוץ", styles["Title"]))
        content.append(Paragraph(datetime.now().strftime("%d/%m %H:%M"), styles["Normal"]))

        total = 0

        for team in TEAMS:
            content.append(Paragraph(f"<br/><b>{team}</b>", styles["Normal"]))

            for uid, u in users.items():
                if u["team"] == team:
                    total += 1
                    st = "בזירה" if status.get(uid) else "יצא"

                    content.append(Paragraph(
                        f"{u['name']} - {st}",
                        styles["Normal"]
                    ))

        doc.build(content)

        # שליחה למפקדים
        for uid, u in users.items():
            if is_commander(u["name"]):
                await context.bot.send_document(chat_id=uid, document=open("report.pdf", "rb"))

        await context.bot.send_message(chat_id=CHANNEL_ID, text="🛑 האירוע הסתיים")

        # איפוס
        status.clear()
        locations.clear()
        arrival_times.clear()
        leave_times.clear()

        await update.message.reply_text("אירוע אופס ✅")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle))

    app.run_polling()

if __name__ == "__main__":
    main()