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
        order_id = data.get("tildaorderid", "—")
        products_raw = data.get("tildaproducts", "[]")
        try:
            products_list = json.loads(products_raw)
        except:
            products_list = []

        products_text = ""
        total_sum = 0
        for item in products_list:
            title = item.get("title", "Товар")
            qty = item.get("quantity", 1)
            price = int(item.get("price", 0))
            total_sum += price * int(qty)
            products_text += f"• {title} x{qty} — {price} руб\n"

        if not products_text:
            products_text = "—"

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
            f"💳 Сумма: {total_sum} руб\n\n"
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