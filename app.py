import os
import telebot
from flask import Flask, request
from datetime import datetime
import pytz

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route("/tilda_order", methods=["POST"])
def tilda_order():
    data = request.form.to_dict(flat=False)

    # Читаем данные из формы
    order_id = data.get("orderid", ["—"])[0]
    products = data.get("products", [])
    amount = data.get("amount", ["—"])[0]
    fio = data.get("name", ["—"])[0]
    phone = data.get("phone", ["—"])[0]
    email = data.get("email", ["—"])[0]
    address = data.get("Адрес", ["—"])[0]
    telegram = data.get("Telegram", ["—"])[0]
    city = data.get("City", ["—"])[0]

    # Время по Екатеринбургу
    tz = pytz.timezone("Asia/Yekaterinburg")
    now = datetime.now(tz).strftime("%d.%m.%Y %H:%M")

    print(request.json)

    # Красивый список товаров
    product_lines = "\n".join([f"— {p}" for p in products]) if products else "—"

    # Ссылка на телеграм
    tg_link = f"[{telegram}](https://t.me/{telegram})" if telegram != "—" else "—"

    # Финальное сообщение
    message = (
        f"🛒 *Новый заказ с сайта*\n\n"
        f"📦 *Номер заказа:* {order_id}\n"
        f"🕒 *Дата и время:* {now}\n\n"
        f"👕 *Товары:*\n{product_lines}\n\n"
        f"💳 *Сумма:* {amount} руб\n\n"
        f"🙍 *ФИО:* {fio}\n"
        f"📧 *Email:* {email}\n"
        f"📞 *Телефон:* {phone}\n"
        f"🏠 *Адрес:* {address}\n"
        f"🌆 *Город:* {city}\n"
        f"✈️ *Telegram:* {tg_link}"
    )

    bot.send_message(CHAT_ID, message, parse_mode="Markdown")
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)