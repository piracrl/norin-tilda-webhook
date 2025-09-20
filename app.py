import os
import json
from datetime import datetime

import pytz
import telebot
from telebot import types
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# --- Конфиг из окружения ---
TOKEN = os.getenv("TELEGRAM_TOKEN")  
CHAT_ID = os.getenv("CHAT_ID")  
WEBHOOK_URL = f"https://bot.nor1n-store.ru/bot_webhook"

if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN не задан в переменных окружения")
if not CHAT_ID:
    raise RuntimeError("CHAT_ID не задан в переменных окружения")

# --- Flask / DB ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- Модель заказа ---
class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50))
    products = db.Column(db.Text)
    amount = db.Column(db.String(20))
    fio = db.Column(db.String(200))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    city = db.Column(db.String(100))
    address = db.Column(db.String(200))
    telegram = db.Column(db.String(50))
    paid = db.Column(db.Boolean, default=False)

bot = telebot.TeleBot(TOKEN)

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
        data = request.form.to_dict()
        payment_data = json.loads(data.get("payment", "{}"))

        order_id = payment_data.get("orderid", "—")
        products = payment_data.get("products", [])
        amount = payment_data.get("amount", "—")

        products_text = "\n".join(products) if products else "—"

        tz = pytz.timezone("Asia/Yekaterinburg")
        now = datetime.now(tz).strftime("%d.%m.%Y %H:%M")

        fio = data.get("name", "—")
        email = data.get("email", "—")
        phone = data.get("phone", "—")
        address = data.get("address", "—")
        city = data.get("city", "—")
        tg_username = data.get("telegram", "")
        tg_link = f"@{tg_username}" if tg_username else "—"

        # сохраняем заказ в БД
        order = Order(
            order_id=order_id,
            products=products_text,
            amount=str(amount),
            fio=fio,
            email=email,
            phone=phone,
            city=city,
            address=address,
            telegram=tg_username or None
        )
        db.session.add(order)
        db.session.commit()

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
        print("Ошибка tilda_order:", e)
        db.session.rollback()
        return "error", 500

# ОБРАБОТКА КОМАНД КЛИЕНТА
@bot.message_handler(commands=["start"])
def start(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📋 Мой заказ")
    kb.add("💳 Реквизиты для оплаты", "📞 Связаться с менеджером")

    bot.send_message(
        message.chat.id,
        "Привет 👋\nЯ бот магазина Nor1n Store.\n\n"
        "Здесь ты можешь получить информацию о заказе, оплате и связаться с менеджером.",
        reply_markup=kb
    )

    username = message.from_user.username
    if username:
        order = (
            Order.query.filter_by(telegram=username)
            .order_by(Order.id.desc())
            .first()
        )
        if order:
            paid_text = "✅ Оплачен" if order.paid else "⌛ Ожидает оплаты"
            kb.add("✅ Я оплатил")
            order_msg = (
                f"📦 Мы нашли твой заказ!\n\n"
                f"Номер заказа: {order.order_id}\n"
                f"Статус: {paid_text}\n\n"
                f"Товары:\n{order.products}\n\n"
                f"Сумма: {order.amount} руб\n\n"
                f"ФИО: {order.fio}\n"
                f"Телефон: {order.phone}\n"
                f"Адрес: {order.city}, {order.address}\n"
                f"Email: {order.email}\n\n"
                f"Проверь данные, если что-то не сходится — напиши нам."
            )
            bot.send_message(message.chat.id, order_msg, reply_markup=kb)

@bot.message_handler(func=lambda m: isinstance(m.text, str) and "Реквизиты" in m.text and "оплат" in m.text)
def payment_info(message):
    username = message.from_user.username
    order = None
    if username:
        order = Order.query.filter_by(telegram=username).order_by(Order.id.desc()).first()

    amount_text = f"\nСумма к оплате: {order.amount} руб" if order else ""
    bot.send_message(
        message.chat.id,
        "💳 Реквизиты для оплаты:\n\nТ-Банк\n2200 7007 4343 1685\nСавелий П." + amount_text
    )

@bot.message_handler(func=lambda msg: msg.text == "📋 Мой заказ")
def my_order(message):
    username = message.from_user.username
    if not username:
        bot.send_message(message.chat.id, "Извини, не смогли найти заказ. У тебя не заполнен username в Telegram 😕")
        return
    
    order = (
            Order.query.filter_by(telegram=username)
            .order_by(Order.id.desc())
            .first()
        )

    if order:
        status_text = "✅ Оплачен" if order.paid else "⌛ Ожидает оплаты"
        bot.send_message(
            message.chat.id,
            f"Твой заказ:\n\n"
            f"Номер: {order.order_id}\n"
            f"{order.products}\n"
            f"Сумма: {order.amount} руб\n"
            f"Статус: {status_text}\n\n"
            f"Адрес доставки: {order.city}, {order.address}\n"
            f"Телефон: {order.phone}"
        )
    else:
        bot.send_message(message.chat.id, "Заказ не найден 😕")

@bot.message_handler(func=lambda msg: msg.text == "✅ Я оплатил")
def payment_confirmed(message):
    username = message.from_user.username
    if not username:
        bot.send_message(message.chat.id, "Извини, не сможем проверить оплату. У тебя не заполнен username в Telegram 😕")
        return

    order = Order.query.filter_by(telegram=username).order_by(Order.id.desc()).first()
    if order:
        order.paid = True
        db.session.commit()

        bot.send_message(message.chat.id, "Спасибо! Мы отметили, что ты оплатил заказ. Скоро мы всё проверим и свяжемся с тобой.")
        notify = (
            "💸 Клиент сообщил об оплате!\n\n"
            f"Номер заказа: {order_id}\n"
            f"Telegram: @{username}\n"
            f"Сумма: {amount} руб"
        )
        bot.send_message(CHAT_ID, notify)
    else:
        bot.send_message(message.chat.id, "❌ У нас нет данных о твоём заказе. Пожалуйста, напиши менеджеру @nor1nstore_buy.")

@bot.message_handler(func=lambda msg: msg.text == "📞 Связаться с менеджером")
def contact_manager(message):
    bot.send_message(message.chat.id, "📞 Связаться с менеджером можно тут: @nor1nstore_buy")

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)