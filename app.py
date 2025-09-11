from flask import Flask, request
import requests

app = Flask(__name__)

# Твой токен и id чата для уведомлений в Телеграм
TELEGRAM_TOKEN = "8209697873:AAHe9gzolpUdAnXtIgerB05EJZKJ5Y38Dqk"
CHAT_ID = "747738200"

@app.route("/tilda_order", methods=["POST"])
def tilda_order():
    data = request.form.to_dict()  # Тильда шлёт form-data
    print("Получен заказ:", data)

    # Красивое сообщение
    message = "🛒 Новый заказ с сайта\n\n"
    
    if "payment" in data:  # если есть способ оплаты
        message += f"💳 Оплата: {data['payment']}\n"

    if "product" in data:  # если Тильда прислала название товара
        message += f"👕 Товар: {data['product']}\n"

    if "size" in data:
        message += f"📏 Размер: {data['size']}\n"

    # Общие поля
    if "name" in data:
        message += f"🙍 Имя: {data['name']}\n"
    if "surname" in data:
        message += f"🙍‍♂️ Фамилия: {data['surname']}\n"
    if "phone" in data:
        message += f"📞 Телефон: {data['phone']}\n"
    if "email" in data:
        message += f"✉️ Почта: {data['email']}\n"
    if "address" in data:
        message += f"📦 Адрес: {data['address']}\n"

    # Всё остальное (чтобы ничего не потерялось)
    for key, value in data.items():
        if key not in ["payment", "product", "size", "name", "surname", "phone", "email", "address"]:
            message += f"{key.capitalize()}: {value}\n"

    # Отправка в Телеграм
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": message
    })

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
