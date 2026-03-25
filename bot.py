
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime

TOKEN = "8625498364:AAHW0ieQt2WQfn6eEEmw93_OMji5Enqwcp4"
CHANNEL_ID = "@SaarDimona"

TEAMS = ["צוות 1", "צוות 2", "צוות 3", "צוות רפואה", "מודיעין אוכלוסייה"]
COMMANDERS = ["יבגני", "יהונתן", "אסף", "יניב", "סרג", "אבישג"]

users = {}
status = {}
locations = {}
log_times = {}

# ===== עזר =====
def is_commander(name):
    return name in COMMANDERS

def get_menu(name):
    buttons = [
        ["✅ הגעתי לזירה", "❌ יצאתי מהזירה"],
        ["📍 שלח מיקום", "📊 מי בזירה"],
        ["📍 מפת מחלצים"]
    ]

    if is_commander(name):
        buttons.append(["🚨 הקפצת חירום", "🧾 דוח אירוע"])
        buttons.append(["📊 דשבורד", "🛑 סיום אירוע"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

async def notify_commanders(context, message):
    for uid, u in users.items():
        if is_commander(u["name"]):
            try:
                await context.bot.send_message(chat_id=uid, text=message)
            except:
                pass

# ===== התחלה =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ברוך הבא 🚑\nרשום שם:")
    context.user_data["step"] = "name"

# ===== לוגיקה =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text if update.message.text else None

    # ===== מיקום =====
    if update.message.location:
        user = users.get(user_id)
        if not user or not is_commander(user["name"]):
            return

        loc = update.message.location
        locations[user_id] = (loc.latitude, loc.longitude)

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{user['name']} שלח מיקום 📍\nhttps://maps.google.com/?q={loc.latitude},{loc.longitude}"
        )

        await update.message.reply_text("נשמר מיקום 👍", reply_markup=get_menu(user["name"]))
        return

    if not text:
        return

    # ===== שם =====
    if context.user_data.get("step") == "name":
        context.user_data["name"] = text
        keyboard = [[team] for team in TEAMS]

        await update.message.reply_text("בחר צוות:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        context.user_data["step"] = "team"

    # ===== צוות =====
    elif context.user_data.get("step") == "team":
        context.user_data["team"] = text
        users[user_id] = context.user_data.copy()

        await update.message.reply_text("בחר פעולה:", reply_markup=get_menu(context.user_data["name"]))
        context.user_data["step"] = "done"

    # ===== הגעה =====
    elif text == "✅ הגעתי לזירה":
        user = users[user_id]
        status[user_id] = True
        log_times[user_id] = {"in": datetime.now(), "out": None}

        msg = f"{user['name']} | {user['team']} הגיע לזירה 🟢"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)

        await notify_commanders(context, f"🟢 {user['name']} נכנס לזירה")

        await update.message.reply_text("נרשמת 👍", reply_markup=get_menu(user["name"]))

    # ===== יציאה =====
    elif text == "❌ יצאתי מהזירה":
        user = users[user_id]
        status[user_id] = False

        if user_id in log_times:
            log_times[user_id]["out"] = datetime.now()

        msg = f"{user['name']} | {user['team']} יצא מהזירה 🔴"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)

        await notify_commanders(context, f"🔴 {user['name']} יצא מהזירה")

        await update.message.reply_text("עודכן 👍", reply_markup=get_menu(user["name"]))

    # ===== מי בזירה =====
    elif text == "📊 מי בזירה":
        user = users[user_id]

        if is_commander(user["name"]):
            result = ""
            for team in TEAMS:
                result += f"\n{team}:\n"
                for uid, st in status.items():
                    if st and users[uid]["team"] == team:
                        result += f"- {users[uid]['name']}\n"
        else:
            count = sum(1 for st in status.values() if st)
            result = f"סה\"כ בזירה: {count}"

        await update.message.reply_text(result, reply_markup=get_menu(user["name"]))

    # ===== מפה =====
    elif text == "📍 מפת מחלצים":
        links = ""
        for uid, loc in locations.items():
            name = users[uid]["name"]
            links += f"{name}: https://maps.google.com/?q={loc[0]},{loc[1]}\n"

        if not links:
            links = "אין מיקומים"

        await update.message.reply_text(links)

    # ===== דוח =====
    elif text == "🧾 דוח אירוע":
        user = users[user_id]
        if not is_commander(user["name"]):
            return

        report = "📊 דוח אירוע:\n\n"
        for uid, times in log_times.items():
            name = users[uid]["name"]
            report += f"{name}\nכניסה: {times['in']}\nיציאה: {times['out']}\n\n"

        await update.message.reply_text(report)

    # ===== דשבורד =====
    elif text == "📊 דשבורד":
        user = users[user_id]
        if not is_commander(user["name"]):
            return

        total = len(users)
        active = sum(1 for s in status.values() if s)
        with_location = len(locations)
        teams_active = len(set(u["team"] for uid, u in users.items() if status.get(uid)))

        dashboard = (
            "📊 דשבורד ניהולי\n\n"
            f"סה\"כ רשומים: {total}\n"
            f"בזירה עכשיו: {active}\n"
            f"שלחו מיקום: {with_location}\n"
            f"צוותים פעילים: {teams_active}"
        )

        await update.message.reply_text(dashboard)

    # ===== סיום אירוע =====
    elif text == "🛑 סיום אירוע":
        user = users[user_id]
        if not is_commander(user["name"]):
            return

        status.clear()
        locations.clear()
        log_times.clear()

        await context.bot.send_message(chat_id=CHANNEL_ID, text="🛑 האירוע הסתיים\nכל הנתונים אופסו")

        for uid in users:
            try:
                await context.bot.send_message(chat_id=uid, text="🛑 האירוע הסתיים")
            except:
                pass

        await update.message.reply_text("האירוע אופס ✅")

    # ===== הקפצה =====
    elif text == "🚨 הקפצת חירום":
        user = users[user_id]
        if not is_commander(user["name"]):
            return

        await update.message.reply_text("כתוב פרטים:")
        context.user_data["step"] = "alert"

    elif context.user_data.get("step") == "alert":
        msg = f"🚨 הקפצה 🚨\n{text}"

        for uid in users:
            try:
                await context.bot.send_message(chat_id=uid, text=msg)
            except:
                pass

        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)
        context.user_data["step"] = "done"

# ===== הרצה =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle))

    app.run_polling()

if __name__ == "__main__":
    main()