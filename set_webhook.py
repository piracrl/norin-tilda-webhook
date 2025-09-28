import os
import telebot

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = "https://bot.nor1n-store.ru/bot_webhook"

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)
print("Webhook установлен")