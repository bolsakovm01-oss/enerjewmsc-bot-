import logging
import os
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)

TOKEN = "8656435167:AAGIbXldIlfmUteZuGZwdbbz3x7-i7yR3R8"
ADMIN_ID = 1018190689
SHEET_ID = "1F1Ae-f739jSpQx2ehX1h4UZg7pRSDuCxNa1tjSSDGLo"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

google_creds_b64 = os.environ.get("GOOGLE_CREDENTIALS")
if google_creds_b64:
    import json, base64
    creds_dict = json.loads(base64.b64decode(google_creds_b64).decode("utf-8"))
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
else:
    creds = Credentials.from_service_account_file("credentials.json", scopes=scope)

gc = gspread.authorize(creds)
workbook = gc.open_by_key(SHEET_ID)
sheet = workbook.sheet1

try:
    events_sheet = workbook.get_worksheet(1)
    if events_sheet is None:
        events_sheet = workbook.add_worksheet(title="Мероприятия", rows=100, cols=3)
        events_sheet.append_row(["Название", "Дата", "Описание"])
except:
    events_sheet = workbook.add_worksheet(title="Мероприятия", rows=100, cols=3)
    events_sheet.append_row(["Название", "Дата", "Описание"])

try:
    users_sheet = workbook.get_worksheet(2)
    if users_sheet is None:
        users_sheet = workbook.add_worksheet(title="Участники", rows=1000, cols=4)
        users_sheet.append_row(["Telegram ID", "Имя", "Телефон", "Username"])
except:
    users_sheet = workbook.add_worksheet(title="Участники", rows=1000, cols=4)
    users_sheet.append_row(["Telegram ID", "Имя", "Телефон", "Username"])

subscribers = set()
REG_NAME, REG_PHONE = range(2)
ADD_EVENT_NAME, ADD_EVENT_DATE, ADD_EVENT_DESC = range(2, 5)


def find_user(telegram_id):
    try:
        ids = users_sheet.col_values(1)
        if str(telegram_id) in ids:
            row_index = ids.index(str(telegram_id)) + 1
            row = users_sheet.row_values(row_index)
            return {"name": row[1], "phone": row[2]}
    except:
        pass
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribers.add(update.effective_user.id)
    keyboard = [["📅 Мероприятия", "ℹ️ О проекте"], ["📞 Контакты", "❓ Помощь"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    user = find_user(update.effective_user.id)
    if user:
        await update.message.reply_text(
            f"Шалом, {user['name']}! 👋 Рад снова тебя видеть!\n\n"
            f"Выбери что тебя интересует:",
            reply_markup=markup
        )
    else:
        await update.message.reply_text(
            "Шалом! 👋 Добро пожаловать в EnerJew Moscow!\n\n"
            "Мы помогаем подросткам найти свою связь с еврейской культурой и традицией 🕍\n\n"
            "Сначала создай профиль чтобы записываться на мероприятия: /profile\n\n"
            "Или посмотри что у нас есть 👇",
            reply_markup=markup
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Вот что я умею:\n\n"
        "📅 Мероприятия — ближайшие события и запись\n"
        "👤 /profile — твой профиль\n"
        "ℹ️ О проекте — что такое EnerJew Moscow\n"
        "📞 Контакты — как с нами связаться"
    )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "EnerJew Moscow — современный еврейский молодёжный проект.\n\n"
        "Помогаем подросткам найти свою связь с традицией "
        "и культурой еврейского народа 🕍\n\n"
        "Мы проводим:\n"
        "• Образовательные занятия\n"
        "• Фан-встречи\n"
        "• Шаббатоны\n"
        "• Еврейские праздники"
    )


async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Связаться с нами:\n\n"
        "📱 Telegram: https://t.me/enerjewmoscow\n"
        "📸 Instagram: @enerjewmsc"
    )


async def events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rows = events_sheet.get_all_records()
        if not rows:
            await update.message.reply_text(
                "📅 Пока мероприятий нет.\n\nСледи за обновлениями! 🌟"
            )
            return
        buttons = []
        for i, row in enumerate(rows):
            label = f"🗓 {row['Дата']} — {row['Название']}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"event_{i}")])
        markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            "📅 Ближайшие мероприятия EnerJew Moscow:\n\n"
            "Нажми на мероприятие чтобы узнать подробнее 👇",
            reply_markup=markup
        )
    except Exception as e:
        await update.message.reply_text("Не удалось загрузить мероприятия 😔")
        logging.error(f"Ошибка: {e}")


async def event_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    index = int(query.data.split("_")[1])
    rows = events_sheet.get_all_records()
    if index >= len(rows):
        await query.edit_message_text("Мероприятие не найдено 😔")
        return
    event = rows[index]
    context.user_data["selected_event"] = event["Название"]
    context.user_data["selected_date"] = event["Дата"]
    desc = event["Описание"] if event["Описание"] else "Подробности уточняйте у организаторов."
    user = find_user(query.from_user.id)
    if user:
        buttons = [[InlineKeyboardButton("✅ Записаться", callback_data=f"quickreg_{index}")]]
        extra = f"\n\n👤 Запись на имя: {user['name']}"
    else:
        buttons = [[InlineKeyboardButton("👤 Создать профиль и записаться", callback_data=f"needprofile_{index}")]]
        extra = "\n\n⚠️ Для записи сначала создай профиль — один раз, и больше не нужно!"
    markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(
        f"🗓 {event['Дата']} — {event['Название']}\n\n{desc}{extra}",
        reply_markup=markup
    )


async def quick_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = find_user(query.from_user.id)
    event = context.user_data.get("selected_event", "—")
    date = context.user_data.get("selected_date", "—")
    username = query.from_user.username or str(query.from_user.id)
    try:
        sheet.append_row([user["name"], user["phone"], event, date, f"@{username}"])
        await query.edit_message_text(
            f"✅ Готово, {user['name']}!\n\n"
            f"Ты записан(а) на:\n"
            f"🗓 {date} — {event}\n\n"
        )
    except Exception as e:
        await query.edit_message_text("Что-то пошло не так 😔 Напиши нам: @enerjew_moscow")
        logging.error(f"Ошибка быстрой записи: {e}")


async def need_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Сначала создай профиль — это займёт 30 секунд!\n\nНапиши /profile 👇"
    )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = find_user(update.effective_user.id)
    if user:
        await update.message.reply_text(
            f"👤 Твой профиль:\n\n"
            f"Имя: {user['name']}\n"
            f"Телефон: {user['phone']}\n\n"
            f"Чтобы обновить данные — напиши /updateprofile"
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Давай познакомимся! 👋\n\nКак тебя зовут? (Имя и фамилия)"
        )
        return REG_NAME


async def update_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи новое имя:")
    return REG_NAME


async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Напиши свой номер телефона:")
    return REG_PHONE


async def reg_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data["name"]
    phone = update.message.text
    telegram_id = update.effective_user.id
    username = update.effective_user.username or "—"
    try:
        existing = find_user(telegram_id)
        if existing:
            ids = users_sheet.col_values(1)
            row_index = ids.index(str(telegram_id)) + 1
            users_sheet.update(f"B{row_index}:C{row_index}", [[name, phone]])
        else:
            users_sheet.append_row([str(telegram_id), name, phone, f"@{username}"])
        await update.message.reply_text(
            f"✅ Отлично, {name}! Профиль сохранён.\n\n"
            f"Теперь ты можешь записываться на мероприятия в один клик!\n"
            f"Нажми 📅 Мероприятия чтобы посмотреть что у нас есть 🗓"
        )
    except Exception as e:
        await update.message.reply_text("Ошибка при сохранении 😔 Попробуй снова.")
        logging.error(f"Ошибка сохранения профиля: {e}")
    return ConversationHandler.END


async def addevent_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У тебя нет прав для этой команды.")
        return ConversationHandler.END
    await update.message.reply_text("Как называется мероприятие?")
    return ADD_EVENT_NAME


async def addevent_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["event_name"] = update.message.text
    await update.message.reply_text("Какая дата? (например: 15 мая)")
    return ADD_EVENT_DATE


async def addevent_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["event_date"] = update.message.text
    await update.message.reply_text("Краткое описание (или напиши «-» если не нужно):")
    return ADD_EVENT_DESC


async def addevent_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text
    if desc == "-":
        desc = ""
    name = context.user_data["event_name"]
    date = context.user_data["event_date"]
    try:
        events_sheet.append_row([name, date, desc])
        await update.message.reply_text(
            f"✅ Мероприятие добавлено!\n\n🗓 {date} — {name}\n\nУчастники увидят его в Мероприятиях"
        )
    except Exception as e:
        await update.message.reply_text("Ошибка при сохранении 😔")
        logging.error(f"Ошибка: {e}")
    return ConversationHandler.END


async def delevent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У тебя нет прав для этой команды.")
        return
    rows = events_sheet.get_all_records()
    if not rows:
        await update.message.reply_text("Мероприятий нет.")
        return
    text = "Какое мероприятие удалить? Напиши номер:\n\n"
    for i, row in enumerate(rows, 1):
        text += f"{i}. {row['Дата']} — {row['Название']}\n"
    await update.message.reply_text(text)
    context.user_data["delete_mode"] = True


async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У тебя нет прав для рассылки.")
        return
    if not context.args:
        await update.message.reply_text("Напиши текст после команды:\n/announce Привет всем!")
        return
    text = " ".join(context.args)
    success = 0
    for user_id in subscribers:
        try:
            await context.bot.send_message(chat_id=user_id, text=f"📢 EnerJew Moscow:\n\n{text}")
            success += 1
        except:
            pass
    await update.message.reply_text(f"Рассылка отправлена {success} участникам ✅")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Окей, отменили 👌")
    return ConversationHandler.END


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📅 Мероприятия":
        await events(update, context)
    elif text == "ℹ️ О проекте":
        await about(update, context)
    elif text == "📞 Контакты":
        await contact(update, context)
    elif text == "❓ Помощь":
        await help_command(update, context)
    elif context.user_data.get("delete_mode"):
        try:
            num = int(text)
            events_sheet.delete_rows(num + 1)
            context.user_data["delete_mode"] = False
            await update.message.reply_text("✅ Мероприятие удалено!")
        except:
            await update.message.reply_text("Напиши просто номер из списка.")
    else:
        await update.message.reply_text("Напиши ❓ Помощь чтобы увидеть что я умею 😊")


app = ApplicationBuilder().token(TOKEN).build()

profile_handler = ConversationHandler(
    entry_points=[
        CommandHandler("profile", profile),
        CommandHandler("updateprofile", update_profile)
    ],
    states={
        REG_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
        REG_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_phone)],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

addevent_handler = ConversationHandler(
    entry_points=[CommandHandler("addevent", addevent_start)],
    states={
        ADD_EVENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addevent_name)],
        ADD_EVENT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addevent_date)],
        ADD_EVENT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, addevent_desc)],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("about", about))
app.add_handler(CommandHandler("contact", contact))
app.add_handler(CommandHandler("events", events))
app.add_handler(CommandHandler("announce", announce))
app.add_handler(CommandHandler("delevent", delevent))
app.add_handler(profile_handler)
app.add_handler(addevent_handler)
app.add_handler(CallbackQueryHandler(event_selected, pattern="^event_"))
app.add_handler(CallbackQueryHandler(quick_register, pattern="^quickreg_"))
app.add_handler(CallbackQueryHandler(need_profile, pattern="^needprofile_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Бот запущен! 🚀")
app.run_polling()