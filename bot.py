from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
TOKEN = "8625498364:AAHW0ieQt2WQfn6eEEmw93_OMji5Enqwcp4"
CHANNEL_ID = "@SaarDimona"
TEAMS = ["צוות 1", "צוות 2", "צוות 3", "צוות רפואה", "מודיעין אוכלוסייה"]
COMMANDERS = ["יבגני", "יהונתן", "אסף", "יניב", "סרג", "אבישג"]
users = {}
status = {}
def is_commander(name):
    return name in COMMANDERS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ברוך הבא למערכת חילוץ 🚑\nרשום שם:")
    context.user_data["step"] = "name"
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if context.user_data.get("step") == "name":
        context.user_data["name"] = text
        keyboard = [[team] for team in TEAMS]
        await update.message.reply_text("בחר צוות:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        context.user_data["step"] = "team"
    elif context.user_data.get("step") == "team":
        context.user_data["team"] = text
        users[user_id] = context.user_data
        buttons = [
            ["✅ הגעתי לזירה", "❌ יצאתי מהזירה"],
            ["📍 שלח מיקום", "📊 מי בזירה"]
        ]
        if is_commander(context.user_data["name"]):
            buttons.append(["🚨 הקפצת חירום"])
        await update.message.reply_text("בחר פעולה:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        context.user_data["step"] = "done"
    elif text == "✅ הגעתי לזירה":
        user = users.get(user_id)
        status[user_id] = True
        msg = f"{user['name']} | {user['team']} הגיע לזירה 🟢"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)
    elif text == "❌ יצאתי מהזירה":
        user = users.get(user_id)
        status[user_id] = False
        msg = f"{user['name']} | {user['team']} יצא מהזירה 🔴"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)
    elif text == "📊 מי בזירה":
        result = ""
        count = 0
        for team in TEAMS:
            result += f"\n{team}:\n"
            for uid, st in status.items():
                if st and users[uid]["team"] == team:
                    result += f"- {users[uid]['name']}\n"
                    count += 1
        result += f"\nסה\"כ בזירה: {count}"
        await update.message.reply_text(result)
    elif text == "📍 שלח מיקום":
        button = [[KeyboardButton("שלח מיקום", request_location=True)]]
        await update.message.reply_text("שלח מיקום:", reply_markup=ReplyKeyboardMarkup(button, resize_keyboard=True))
    elif update.message.location:
        user = users.get(user_id)
        loc = update.message.location
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{user['name']} שלח מיקום 📍 https://maps.google.com/?q={loc.latitude},{loc.longitude}"
        )
    elif text == "🚨 הקפצת חירום":
        user = users.get(user_id)
        if not is_commander(user["name"]):
            return
        await update.message.reply_text("כתוב פרטי אירוע:")
        context.user_data["step"] = "alert"
    elif context.user_data.get("step") == "alert":
        msg = f"🚨 הקפצת חירום 🚨\n{text}"
        for uid in users:
            await context.bot.send_message(chat_id=uid, text=msg)
        context.user_data["step"] = "done"
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle))
    app.run_polling()
import asyncio

asyncio.run(main())