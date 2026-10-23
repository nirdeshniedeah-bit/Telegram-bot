import os
import telebot
from flask import Flask, request

# Ungaloda Bot Token mattrum Render Live URL
BOT_TOKEN = "8793044253:AAE_x5dh5MOON16vYUsblliyvRtjqwtv1xY"
WEBHOOK_URL = "https://telegram-bot-1-18bj.onrender.com"

bot = telebot.TeleBot(8793044253:AAE_x5dh5MOON16vYUsblliyvRtjqwtv1xY)
app = Flask(__name__)

# Basic start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Vanakkam! Bot ippo Render-la vetrigaramaaga run aaguthu.")

# Matha commands mattrum messages handle panna
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Neengal sonnathu: {message.text}")

# Telegram-la irunthu updates vara webhook route
@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def receive_update():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# Render port check panna default root route
@app.route("/")
def index():
    return "Bot Server is Running Live!", 200

if __name__ == "__main__":
    # Webhook setup seithal
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    
    # Render kudukura Port-la server-ai bind seithal
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
