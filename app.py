import os
from flask import Flask, request
import telebot
import pytz
from datetime import datetime
import json
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")  # сохрани токен как переменную окружения
CHAT_ID = os.getenv("CHAT_ID")  # и chat_id тоже
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# временное хранилище заказов (потом можно заменить на БД)
orders = {}

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
        orders[tg_username] = {
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

        bot.send_message(CHAT_ID, message)
        return "ok"
    except Exception as e:
        print("Ошибка:", e)
        return "error", 500

# ОБРАБОТКА КОМАНД КЛИЕНТА
@bot.message_handler(commands=["start"])
def start(message):
    username = message.from_user.username
    if username in orders:
        order = orders[username]

        #Кнопки
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("📑 Реквизиты для оплаты")
        btn2 = types.KeyboardButton("💬 Связаться с менеджером")
        btn3 = types.KeyboardButton("✅ Я оплатил")
        markup.add(btn1, btn2, btn3)

        bot.send_message(
            message.chat.id,
            f"""Привет! Мы нашли твой заказ 🎉

📦 Номер заказа: {order['id']}
👕 Товары: {chr(10).join(order['products'])}
💳 Сумма: {order['amount']} руб

Выбери действие ниже:""",
            reply_markup=markup
            )
    else:
        bot.send_message(message.chat.id, "Привет! Пока заказов за тобой не числится 🙂")

# ОБРАБОТКА КНОПОК
@bot.message_handler(func=lambda m: m.text == "📑 Реквизиты для оплаты")
def payment_info(message):
    username = message.from_user.username
    order = orders.get(username)
    if order:
        bot.send_message(message.chat.id, f"""Реквизиты для оплаты заказа №{order['id']}:

💳 2202 2020 3030 4040
Получатель: Иван Иванов
Сумма: {order['amount']} руб

После оплаты нажми кнопку ✅ Я оплатил""")
    else:
        bot.send_message(message.chat.id, "У тебя пока нет заказов.")

@bot.message_handler(func=lambda m: m.text == "💬 Связаться с менеджером")
def contact_manager(message):
    bot.send_message(message.chat.id, "Напиши @username_менеджера для связи с менеджером.")


@bot.message_handler(func=lambda m: m.text == "✅ Я оплатил")
def paid(message):
    bot.send_message(message.chat.id, "Спасибо! Мы проверим оплату и скоро с тобой свяжемся 🙌")


# Вебхук для Telegram
@app.route("/" + TOKEN, methods=["POST"])
def getMessage():
    json_str = request.stream.read().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url="https://norin-tilda-webhook.onrender.com/" + TOKEN)
    return "!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)