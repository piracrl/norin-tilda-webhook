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
PROJECT_ID = "13927899"

if not TOKEN or not CHAT_ID or not PROJECT_ID:
    raise RuntimeError("Отсутствуют переменные окружения TELEGRAM_TOKEN, CHAT_ID или PROJECT_ID")

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
    lead_id = db.Column(db.String(50))
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
        lead_id = payment_data.get("tranid", "")
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

        with app.app_context():
            # сохраняем заказ с lead_id и order_id
            order = Order(
                order_id=order_id,
                lead_id=lead_id,
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
            "🛒 Новый заказ!\n\n"
            f"📦 Номер для клиента: {order_id}\n"
            f"Номер заказа в Тильде: {lead_id}\n"
            f"🕒 Дата: {now}\n\n"
            f"Товары:\n{products_text}\n\n"
            f"Cумма: {amount} руб\n\n"
            f"Заявка в Тильде:\n"
            f"https://tilda.ru/projects/leads/?projectid={PROJECT_ID}&id={PROJECT_ID}:{lead_id}"
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
    kb.add("💳 Реквизиты для оплаты")
    kb.add("📞 Связаться с менеджером")

    bot.send_message(
        message.chat.id,
        "Привет 👋\nЯ бот магазина Nor1n Store.\n\n"
        "Здесь ты можешь получить информацию о заказе, оплате и связаться с менеджером.",
        reply_markup=kb
    )

@bot.message_handler(func=lambda m: isinstance(m.text, str) and "Мой заказ" in m.text)
def my_order(message):
    try:
        with app.app_context():
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("📋 Мой заказ")
            kb.add("💳 Реквизиты для оплаты")
            kb.add("📞 Связаться с менеджером")
            username = message.from_user.username
            order = Order.query.filter_by(telegram=username).order_by(Order.id.desc()).first() if username else None
            if order:
                status_text = "✅ Оплачен" if order.paid else "⌛ Ожидает оплаты"
                bot.send_message(
                    message.chat.id,
                    f"Твой заказ:\n\n"
                    f"Номер: {order.order_id}\n"
                    f"{order.products}\n"
                    f"Сумма: {order.amount} руб\n"
                    f"Статус: {status_text}\n\n"
                    f"Для вопросов: напиши менеджеру @nor1nstore_buy",
                    reply_markup=kb,
                )
            else:
                bot.send_message(message.chat.id, "Заказ не найден 😕", reply_markup=kb)
                print("All good")
    except Exception as e:
        print(f"Ошибка в my_order: {e}")

@bot.message_handler(func=lambda m: isinstance(m.text, str) and "Реквизиты" in m.text and "оплат" in m.text)
def payment_info(message):
    try:
        with app.app_context():
            username = message.from_user.username
            order = Order.query.filter_by(telegram=username).order_by(Order.id.desc()).first() if username else None
            amount_text = f"\nСумма к оплате: {order.amount} руб" if order else ""

            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("✅ Я оплатил")
            kb.add("📞 Связаться с менеджером")

            bot.send_message(
                message.chat.id,
                "💳 Реквизиты для оплаты:\n\nТ-Банк\n2200 7007 4343 1685\nСавелий П." + amount_text,
                reply_markup=kb
            )
    except Exception as e:
        print(f"Ошибка в payment_info: {e}")

@bot.message_handler(func=lambda m: isinstance(m.text, str) and m.text == "✅ Я оплатил")
def payment_confirmed_request(message):
    try:
        with app.app_context():
            username = message.from_user.username
            if not username:
                bot.send_message(message.chat.id, "Извини, не сможем проверить оплату. У тебя не заполнен username в Telegram. Пожалуйста, напиши менеджеру: @nor1nstore_buy")
                return

            order = Order.query.filter_by(telegram=username).order_by(Order.id.desc()).first()
            if not order:
                bot.send_message(message.chat.id, "Не нашли заказ. Пожалуйста, напиши с менеджеру: @nor1nstore_buy")
                return
            if order.paid:
                bot.send_message(message.chat.id, "Оплату уже подтвердили. Спасибо!")
                return

            lead_id = order.lead_id or "неизвестен"    
            crm_link = f"https://tilda.ru/projects/leads/?projectid={project_id}&id={project_id}:{lead_id}"

            keyboard = types.InlineKeyboardMarkup()
            confirm_button = types.InlineKeyboardButton(
                text="Подтвердить оплату",
                callback_data=f"confirm_payment:{order.id}"
            )
            keyboard.add(confirm_button)

            notify_text = (
                f"💳 Клиент @{username} сообщил об оплате!\n"
                f"Номер заказа: {order.order_id}\n"
                f"Сумма: {order.amount} руб\n"
                f"Ссылка на CRM: {crm_link}"
            )
            bot.send_message(int(CHAT_ID), notify_text, reply_markup=keyboard)

            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("📞 Связаться с менеджером")
            bot.send_message(message.chat.id, "Спасибо! В ближайшее время мы проверим оплату и вернёмся с ответом.", reply_markup=kb)
    except Exception as e:
        print(f"Ошибка в payment_confirmed_request: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_payment:"))
def callback_confirm_payment(call):
    try:
        order_id = int(call.data.split(":")[1])
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                bot.answer_callback_query(call.id, "Заказ не найден.")
                return
            if order.paid:
                bot.answer_callback_query(call.id, "Оплата уже была подтверждена.")
                return

            order.paid = True
            db.session.commit()

            if order.telegram:
                bot.send_message(
                    f"@{order.telegram}",
                    "Менеджер подтвердил оплату! Скоро мы свяжемся с тобой для уточнения деталей доставки."
                )

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Оплата заказа {order.order_id} подтверждена менеджером."
            )
            bot.answer_callback_query(call.id, "Оплата подтверждена")
    except Exception as e:
        print(f"Ошибка в callback_confirm_payment: {e}")
        bot.answer_callback_query(call.id, "Ошибка при подтверждении оплаты.")        

@bot.message_handler(func=lambda m: isinstance(m.text, str) and "Связаться" in m.text and "менеджер" in m.text)
def contact_manager(message):
    bot.send_message(message.chat.id, "📞 Связаться с менеджером можно тут: @nor1nstore_buy")

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)