import os
import sqlite3
from flask import Flask, request
import telebot
import pytz
from datetime import datetime
import json
from telebot import types

TOKEN = os.getenv("TELEGRAM_TOKEN")  
CHAT_ID = os.getenv("CHAT_ID")  
WEBHOOK_URL = f"https://bot.nor1n-store.ru/bot_webhook"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- база SQLite ---
DB_PATH = "orders.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            username TEXT,
            products TEXT,
            amount TEXT,
            fio TEXT,
            email TEXT,
            phone TEXT,
            city TEXT,
            address TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_order(order_id, username, products, amount, fio, email, phone, city, address):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO orders (id, username, products, amount, fio, email, phone, city, address, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (order_id, username, products, amount, fio, email, phone, city, address, "pending"))
    conn.commit()
    conn.close()

def get_order_by_username(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    return row

def update_order_status(order_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()

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

        username = tg_username or phone or email  # ключ для сохранения

        # Сохраняем заказ по telegram username
        save_order(order_id, tg_username, products_text, amount, fio, email, phone, city, address)

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
    username = message.from_user.username
    order = get_order_by_username(username) if username else None

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    if order:
        order_id, username, products, amount, fio, email, phone, city, address, status = order
        kb.add(f"💳 Реквизиты для оплаты ({amount} ₽)")
        kb.add("📋 Мой заказ", "📞 Связаться с менеджером")
        kb.add("✅ Я оплатил")

        order_msg = (
            f"📦 Мы нашли твой заказ!\n\n"
            f"Номер заказа: {order_id}\n"
            f"Товары:\n{products}\n\n"
            f"Сумма: {amount} руб\n\n"
            f"ФИО: {fio}\n"
            f"Телефон: {phone}\n"
            f"Адрес: {city}, {address}\n"
            f"Email: {email}\n\n"
            "Проверь данные, если что-то не сходится — напиши нам."
        )
        bot.send_message(message.chat.id, order_msg, reply_markup=kb)
    else:
        kb.add("📋 Мой заказ")
        kb.add("📞 Связаться с менеджером")

        bot.send_message(
            message.chat.id,
            "Привет 👋\nЯ бот магазина Nor1n Store.\n\n"
            "Здесь ты можешь получить информацию о заказе, оплате и связаться с менеджером.",
            reply_markup=kb
        )

@bot.message_handler(func=lambda msg: msg.text == "📋 Мой заказ")
def my_order(message):
    username = message.from_user.username or str(message.chat.id)
    order = get_order_by_username(username) if username else None

    if order:
        order_id, username, products, amount, fio, email, phone, city, address, status = order
        status_text = "✅ Оплачен" if status == "paid" else "⌛ Ожидает оплаты"
        bot.send_message(
            message.chat.id,
            f"Твой заказ:\n\n"
            f"Номер: {order_id}\n"
            f"{products}\n"
            f"Сумма: {amount} руб\n"
            f"Статус: {status_text}\n\n"
            f"Адрес доставки: {city}, {address}"
        )
    else:
        bot.send_message(message.chat.id, "Заказ не найден 😕")

@bot.message_handler(func=lambda msg: msg.text.startswith("💳 Реквизиты для оплаты"))
def payment_info(message):
    bot.send_message(
        message.chat.id,
        "💳 Реквизиты для оплаты:\n\nТ-Банк\n2200 7007 4343 1685\nСавелий П."
    )

@bot.message_handler(func=lambda msg: msg.text == "✅ Я оплатил")
def payment_confirmed(message):
    username = message.from_user.username
    order = get_order_by_username(username) if username else None

    if order:
        order_id, username, products, amount, fio, email, phone, city, address, status = order
        update_order_status(order_id, "paid")
        bot.send_message(message.chat.id, "Спасибо! 🙌 Мы получили информацию об оплате, менеджер скоро проверит её.")

        notify = (
            "💸 Клиент сообщил об оплате!\n\n"
            f"📦 Номер заказа: {order_id}\n"
            f"👤 Telegram: @{username}\n"
            f"💳 Сумма: {amount} руб"
        )
        bot.send_message(CHAT_ID, notify)
    else:
        bot.send_message(message.chat.id, "❌ У нас нет данных о твоём заказе. Пожалуйста, напиши менеджеру @nor1nstore_buy.")

@bot.message_handler(func=lambda msg: msg.text == "📞 Связаться с менеджером")
def contact_manager(message):
    bot.send_message(message.chat.id, "📞 Связаться с менеджером можно тут: @nor1nstore_buy")

if __name__ == "__main__":
    init_db()
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)