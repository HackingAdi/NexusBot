import telebot
from telebot import types
import os
import time
import threading
from flask import Flask

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# Dictionary to store accepted users
accepted_users = {}


@app.route('/')
def home():
    return "Bot is Alive!"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = threading.Thread(target=run)
    t.start()


def is_user_in_channel(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        # Check if status is "left" or "kicked"
        if member.status in ["left", "kicked"]:
            return False
        return True
    except Exception as e:
        print(f"Error checking user in channel: {e}")
        return False


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id in accepted_users:
        if not is_user_in_channel(user_id):
            # User left channel, allow again
            accepted_users.pop(user_id)
        else:
            bot.send_message(message.chat.id,
                             "⚠️ You have already accepted your invite.")
            return

    markup = types.InlineKeyboardMarkup()
    accept_button = types.InlineKeyboardButton("✅ Accept",
                                               callback_data="accept_invite")
    markup.add(accept_button)
    bot.send_message(message.chat.id,
                     "👋 Welcome! Press 'Accept' to get your invite link.",
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "accept_invite")
def accept_invite(call):
    user_id = call.from_user.id
    if user_id in accepted_users:
        if not is_user_in_channel(user_id):
            accepted_users.pop(user_id)  # Allow if left earlier
        else:
            bot.answer_callback_query(call.id,
                                      "You already accepted your invite!")
            return

    try:
        # Generate invite link valid for 10 seconds
        invite_link = bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            expire_date=int(time.time()) + 10,
            member_limit=1)
        sent = bot.send_message(
            call.message.chat.id,
            f"Here is your join link (valid for 10 seconds):\n{invite_link.invite_link}"
        )
        accepted_users[user_id] = True

        # After 10 seconds, delete link message and notify
        def delete_and_notify():
            time.sleep(10)
            try:
                bot.delete_message(chat_id=call.message.chat.id,
                                   message_id=sent.message_id)
                bot.send_message(
                    call.message.chat.id,
                    "⚠️ Your invite link has expired. Please click /start to generate a new one."
                )
            except Exception as e:
                print(f"Error deleting message: {e}")

        threading.Thread(target=delete_and_notify).start()

    except Exception as e:
        bot.send_message(call.message.chat.id,
                         f"Error generating invite link: {str(e)}")


if __name__ == "__main__":
    keep_alive()
    print("Bot is running...")
    bot.infinity_polling()
