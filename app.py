import os
from flask import Flask, request
import telebot
import pytz
from datetime import datetime
import json

TOKEN = os.getenv("BOT_TOKEN")  # сохрани токен как переменную окружения
CHAT_ID = os.getenv("CHAT_ID")  # и chat_id тоже
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

@app.route('/tilda_order', methods=['POST'])
def tilda_order():
    try:
        data = request.form.to_dict()  # получаем данные из формы Тильды
        print("FORM DATA:", data)  # для отладки в логах

        # Достаём поля
        payment_data = json.loads(form_data.get("payment", "{}"))

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

        # Формируем сообщение
        message = (
            "🛒 Новый заказ с сайта\n\n"
            f"📦 Номер заказа: {order_id}\n"
            f"🕒 Дата и время: {now}\n\n"
            f"👕 Товары:\n{products_text}\n"
            f"💳 Сумма: {amount} руб\n\n"
            f"🙍 ФИО: {fio}\n"
            f"📧 Email: {email}\n"
            f"📞 Телефон: {phone}\n"
            f"🏠 Адрес: {address}\n"
            f"🌆 Город: {city}\n"
            f"✈️ Telegram: {tg_link}"
        )

        bot.send_message(CHAT_ID, message)
        return "ok"
    except Exception as e:
        print("Ошибка:", e)
        return "error", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)