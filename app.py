import os
from flask import Flask, request
import telebot
import pytz
from datetime import datetime
import json
from telebot import types

TOKEN = os.getenv("TELEGRAM_TOKEN")  # сохрани токен как переменную окружения
CHAT_ID = os.getenv("CHAT_ID")  # и chat_id тоже
WEBHOOK_URL = f"https://bot.nor1n-store.ru/bot_webhook"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# временное хранилище заказов (потом можно заменить на БД)
ORDERS = {}

# --- Вебхук для Telegram ---
@app.route(f"/bot_webhook", methods=["POST"])
def telegram_webhook():
    json_str = request.get_data(as_text=True)
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# --- Вебхук для Тильды ---
@app.route('/tilda_order', methods=['POST'])
def tilda_order():
    try:
        data = request.form.to_dict()  # получаем данные из формы Тильды
        print("FORM DATA:", data)  # для отладки в логах

        # Достаём поля
        payment_data = json.loads(data.get("payment", "{}"))

        order_id = payment_data.get("orderid", "—")
        products = payment_data.get("products", [])
        amount = payment_data.get("amount", "—")

        # красиво собрать товары
        products_text = "\n".join(products) if products else "—"

        # Время по Екатеринбургу
        tz = pytz.timezone("Asia/Yekaterinburg")
        now = datetime.now(tz).strftime("%d.%m.%Y %H:%M")

        # Остальные поля
        fio = data.get("name", "—")
        email = data.get("email", "—")
        phone = data.get("phone", "—")
        address = data.get("address", "—")
        city = data.get("city", "—")
        tg_username = data.get("telegram", "")
        tg_link = f"@{tg_username}" if tg_username else "—"

        # Сохраняем заказ по telegram username
        ORDERS[tg_link] = {
            "id": order_id,
            "products": products,
            "amount": amount,
            "fio": data.get("name", ""),
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "city": data.get("city", ""),
            "address": data.get("address", ""),
        }

        # Формируем сообщение
        message = (
            "🛒 Новый заказ с сайта NOR1N STORE\n\n"
            f"📦 Номер заказа: {order_id}\n"
            f"🕒 Дата и время: {now}\n\n"
            f"Товары:\n{products_text}\n\n"
            f"Cумма: {amount} руб\n\n"
            f"ФИО: {fio}\n"
            f"Email: {email}\n"
            f"Телефон: {phone}\n"
            f"Адрес: {address}\n"
            f"Город: {city}\n"
            f"Telegram: {tg_link}"
        )

        #Отправка сообщения продавцу
        bot.send_message(CHAT_ID, message)
        return "ok"
    except Exception as e:
        print("Ошибка:", e)
        return "error", 500

# ОБРАБОТКА КОМАНД КЛИЕНТА
@bot.message_handler(commands=["start"])
def start(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📋 Мой заказ")
    kb.add("💳 Реквизиты для оплаты", "📞 Связаться с менеджером")

    bot.send_message(
        message.chat.id,
        "Привет 👋\nЯ бот магазина Norin Store.\n\n"
        "Здесь ты можешь получить информацию о заказе, оплате и связаться с менеджером.",
        reply_markup=kb
    )

    # --- Проверяем, есть ли заказ у клиента ---
    username = message.from_user.username
    if username in ORDERS:
        order = ORDERS[username]
        order_msg = (
            f"📦 Мы нашли твой заказ!\n\n"
            f"Номер заказа: {order['order_id']}\n"
            f"👕 Товары:\n{order['products']}\n\n"
            f"💳 Сумма: {order['amount']} руб\n\n"
            f"🙍 ФИО: {order['name']}\n"
            f"📞 Телефон: {order['phone']}\n"
            f"🏠 Адрес: {order['address']}, {order['city']}\n"
            f"📧 Email: {order['email']}\n\n"
            "Проверь данные, если что-то не сходится — напиши нам."
        )
    bot.send_message(message.chat.id, order_msg)  

# ОБРАБОТКА КНОПОК
def my_order(message):
    username = message.from_user.username
    if username and username in ORDERS:
        order = ORDERS[username]
        bot.send_message(
            message.chat.id,
            f"Ваш заказ:\n\n"
            f"📦 Номер: {order['order_id']}\n"
            f"👕 {order['products']}\n"
            f"💳 Сумма: {order['amount']} руб"
        )
    else:
        bot.send_message(message.chat.id, "Заказ не найден 😕")

@bot.message_handler(func=lambda msg: msg.text == "💳 Реквизиты для оплаты")
def payment_info(message):
    bot.send_message(message.chat.id, "💳 Реквизиты для оплаты:\n\nСбербанк\n1234 5678 9012 3456\nИван Иванов")

@bot.message_handler(func=lambda msg: msg.text == "📞 Связаться с менеджером")
def contact_manager(message):
    bot.send_message(message.chat.id, "📞 Напишите менеджеру: @your_manager")

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)