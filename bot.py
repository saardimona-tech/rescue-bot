
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

# ---------- helpers ----------

def is_commander(name):
    return name in COMMANDERS

def get_main_keyboard(user):
    buttons = [
        ["✅ הגעתי לזירה", "❌ יצאתי מהזירה"],
        ["📍 שלח מיקום", "📊 מי בזירה"]
    ]

    if user and is_commander(user["name"]):
        buttons.append(["🚨 הקפצת חירום"])
        buttons.append(["🛑 סיום אירוע"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ---------- start ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ברוך הבא למערכת חילוץ 🚑\nרשום שם:")
    context.user_data["step"] = "name"

# ---------- main handler ----------

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text if update.message.text else ""

    user = users.get(user_id)

    # ----- הרשמה -----
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
            reply_markup=get_main_keyboard(users[user_id])
        )

        context.user_data["step"] = "done"
        return

    if not user:
        await update.message.reply_text("שלח /start להתחלה")
        return

    # ----- הגעה -----
    if text == "✅ הגעתי לזירה":
        status[user_id] = True
        arrival_times[user_id] = datetime.now()

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{user['name']} | {user['team']} הגיע לזירה 🟢"
        )

        await update.message.reply_text("נרשמת כהגעה ✅", reply_markup=get_main_keyboard(user))
        return

    # ----- יציאה -----
    elif text == "❌ יצאתי מהזירה":
        status[user_id] = False
        leave_times[user_id] = datetime.now()

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{user['name']} | {user['team']} יצא מהזירה 🔴"
        )

        await update.message.reply_text("נרשמת יציאה ❌", reply_markup=get_main_keyboard(user))
        return

    # ----- מי בזירה -----
    elif text == "📊 מי בזירה":
        result = ""
        count = 0

        for team in TEAMS:
            result += f"\n{team}:\n"
            for uid, st in status.items():
                if st and users.get(uid) and users[uid]["team"] == team:
                    result += f"- {users[uid]['name']}\n"
                    count += 1

        result += f"\nסה\"כ: {count}"

        await update.message.reply_text(result, reply_markup=get_main_keyboard(user))
        return

    # ----- שליחת מיקום -----
    elif text == "📍 שלח מיקום":
        if not is_commander(user["name"]):
            await update.message.reply_text("אין הרשאה לשלוח מיקום ❌")
            return

        button = [[KeyboardButton("שלח מיקום", request_location=True)]]

        await update.message.reply_text(
            "שלח מיקום:",
            reply_markup=ReplyKeyboardMarkup(button, resize_keyboard=True)
        )
        return

    # ----- קבלת מיקום -----
    elif update.message.location:
        loc = update.message.location
        locations[user_id] = (loc.latitude, loc.longitude)

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{user['name']} 📍 https://maps.google.com/?q={loc.latitude},{loc.longitude}"
        )

        await update.message.reply_text(
            "המיקום נשלח ✅\nבחר פעולה:",
            reply_markup=get_main_keyboard(user)
        )
        return

    # ----- הקפצת חירום -----
    elif text == "🚨 הקפצת חירום":
        if not is_commander(user["name"]):
            return

        await update.message.reply_text("כתוב הודעת חירום:")
        context.user_data["step"] = "alert"
        return

    elif context.user_data.get("step") == "alert":
        msg = f"🚨 הקפצת חירום 🚨\n{text}"

        for uid in users:
            try:
                await context.bot.send_message(chat_id=uid, text=msg)
            except:
                pass

        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)

        context.user_data["step"] = "done"

        await update.message.reply_text("נשלח לכולם ✅", reply_markup=get_main_keyboard(user))
        return

    # ----- סיום אירוע -----
    elif text == "🛑 סיום אירוע":
        if not is_commander(user["name"]):
            return

        doc = SimpleDocTemplate("report.pdf")
        styles = getSampleStyleSheet()
        content = []

        content.append(Paragraph("דו\"ח אירוע חילוץ", styles["Title"]))
        content.append(Paragraph(datetime.now().strftime("%d/%m %H:%M"), styles["Normal"]))

        for team in TEAMS:
            content.append(Paragraph(f"<br/><b>{team}</b>", styles["Normal"]))

            for uid, u in users.items():
                if u["team"] == team:
                    st = "בזירה" if status.get(uid) else "יצא"
                    content.append(Paragraph(f"{u['name']} - {st}", styles["Normal"]))

        doc.build(content)

        # שליחת PDF למפקדים
        for uid, u in users.items():
            if is_commander(u["name"]):
                await context.bot.send_document(chat_id=uid, document=open("report.pdf", "rb"))

        await context.bot.send_message(chat_id=CHANNEL_ID, text="🛑 האירוע הסתיים")

        # 🔥 שליחה לכולם להתחלה מחדש
        for uid in users:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text="🛑 האירוע הסתיים\nשלח /start להתחלה מחדש"
                )
            except:
                pass

        # איפוס מלא
        users.clear()
        status.clear()
        locations.clear()
        arrival_times.clear()
        leave_times.clear()

        context.user_data.clear()

        await update.message.reply_text("המערכת אופסה ✅\nשלח /start להתחלה")
        return

# ---------- run ----------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle))

    app.run_polling()

if __name__ == "__main__":
    main()
