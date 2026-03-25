from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import asyncio

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
    user_id = update.effective_user.id
    text = update.message.text if update.message.text else None

    # מיקום
    if update.message.location:
        user = users.get(user_id)
        if not user:
            return

        loc = update.message.location
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{user['name']} שלח מיקום 📍\nhttps://maps.google.com/?q={loc.latitude},{loc.longitude}"
        )
        return

    if not text:
        return

    # שם
    if context.user_data.get("step") == "name":
        context.user_data["name"] = text

        keyboard = [[team] for team in TEAMS]
        await update.message.reply_text(
            "בחר צוות:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

        context.user_data["step"] = "team"

    # צוות
    elif context.user_data.get("step") == "team":
        context.user_data["team"] = text
        users[user_id] = context.user_data.copy()

        buttons = [
            ["✅ הגעתי לזירה", "❌ יצאתי מהזירה"],
            ["📍 שלח מיקום", "📊 מי בזירה"]
        ]

        if is_commander(context.user_data["name"]):
            buttons.append(["🚨 הקפצת חירום"])

        await update.message.reply_text(
            "בחר פעולה:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )

        context.user_data["step"] = "done"

    # הגעה
    elif text == "✅ הגעתי לזירה":
        user = users.get(user_id)
        if not user:
            return

        status[user_id] = True
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{user['name']} | {user['team']} הגיע לזירה 🟢"
        )

    # יציאה
    elif text == "❌ יצאתי מהזירה":
        user = users.get(user_id)
        if not user:
            return

        status[user_id] = False
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
                if st and uid in users and users[uid]["team"] == team:
                    result += f"- {users[uid]['name']}\n"
                    count += 1

        result += f"\nסה\"כ בזירה: {count}"
        await update.message.reply_text(result)

    # בקשת מיקום
    elif text == "📍 שלח מיקום":
        button = [[KeyboardButton("שלח מיקום", request_location=True)]]
        await update.message.reply_text(
            "שלח מיקום:",
            reply_markup=ReplyKeyboardMarkup(button, resize_keyboard=True)
        )

    # הקפצה
    elif text == "🚨 הקפצת חירום":
        user = users.get(user_id)
        if not user or not is_commander(user["name"]):
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

    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())