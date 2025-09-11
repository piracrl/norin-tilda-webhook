from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TOKEN = "8209697873:AAHe9gzolpUdAnXtIgerB05EJZKJ5Y38Dqk"
SELLER_CHAT_ID = "1393754770"

@app.route("/tilda_order", methods=["POST"])
def tilda_order():
    data = request.json
    name = data.get('name', 'Не указано')
    telegram = data.get('telegram', 'Не указан')
    phone = data.get('phone', 'Не указан')
    city = data.get('city', 'Не указан')
    address = data.get('address', 'Не указан')
    product = data.get('Products', 'Товар не указан')

    # сообщение продавцу
    message = f"Новый заказ!\nИмя: {name}\nTelegram: {telegram}\nТелефон: {phone}\nГород: {city}\nАдрес: {address}\nТовар: {product}"
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                  data={"chat_id": SELLER_CHAT_ID, "text": message})

    # редирект в бота
    order_id = f"order_{phone[-4:]}"
    bot_link = f"https://t.me/nor1nstore_bot?start={order_id}"

    return jsonify({"result": "ok", "redirect": bot_link})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
