import html
import os
import telebot
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, MenuButtonWebApp

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN', '').strip()
CHANNEL = os.getenv('CHANNEL', '@sashoshamath').strip()
SITE = os.getenv('SITE_URL', 'https://sashoshaa.github.io/sashosha-math/').strip()

if not TOKEN:
    raise SystemExit('Нет BOT_TOKEN. Скопируй .env.example в .env и вставь токен от @BotFather.')

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')
CHANNEL_LINK = 'https://t.me/' + CHANNEL.lstrip('@')


def first_name(user):
    name = (getattr(user, 'first_name', None) or '').strip()
    return html.escape(name) if name else ''


def is_subscribed(user_id):
    if not user_id:
        return False
    try:
        member = bot.get_chat_member(CHANNEL, user_id)
    except Exception:
        return False
    if member.status in ('left', 'kicked'):
        return False
    if member.status in ('creator', 'administrator', 'member'):
        return True
    return member.status == 'restricted' and bool(getattr(member, 'is_member', False))


def start_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('забрать тренажёр 🩰', callback_data='activate'))
    return kb


def subscribe_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('подписаться на канал 🎀', url=CHANNEL_LINK))
    kb.add(InlineKeyboardButton('я уже подписан(а) 🤍', callback_data='check'))
    return kb


def trainer_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('открыть тренажёр 🩰', web_app=WebAppInfo(url=SITE)))
    return kb


def send_welcome(chat_id, user=None):
    name = first_name(user)
    hello = f'Привет, {name} 🤍' if name else 'Привет 🤍'
    bot.send_message(
        chat_id,
        f'{hello}\n\n'
        'В моём канале много полезного — лайфхаки, шпаргалки, разборы и мотивация 🎀\n'
        'Хочешь забрать сайт-тренажер по математике? 🩰',
        reply_markup=start_keyboard(),
        disable_web_page_preview=True,
    )


def send_gate(chat_id, user=None):
    bot.send_message(
        chat_id,
        f'Подпишись на {CHANNEL} и нажми «я уже подписан(а)».\n'
        'Проверю подписку и только потом открою тренажёр!!',
        reply_markup=subscribe_keyboard(),
        disable_web_page_preview=True,
    )


def send_trainer(chat_id, user):
    if not is_subscribed(getattr(user, 'id', None)):
        send_gate(chat_id, user)
        return
    name = first_name(user)
    hello = f'{name}, ты с нами 🩰🤍' if name else 'Ты с нами 🩰🤍'
    bot.send_message(
        chat_id,
        f'{hello}\n\n'
        'Тренажёр внутри бота — нажми кнопку ниже.',
        reply_markup=trainer_keyboard(),
        disable_web_page_preview=True,
    )
    try:
        bot.set_chat_menu_button(
            chat_id,
            MenuButtonWebApp(text='тренажёр', web_app=WebAppInfo(url=SITE)),
        )
    except Exception:
        pass


@bot.message_handler(commands=['start'])
def on_start(message):
    send_welcome(message.chat.id, message.from_user)


@bot.callback_query_handler(func=lambda c: c.data == 'activate')
def on_activate(call):
    bot.answer_callback_query(call.id)
    send_gate(call.message.chat.id, call.from_user)


@bot.callback_query_handler(func=lambda c: c.data == 'check')
def on_check(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, 'есть подписка 🎀')
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
        send_trainer(call.message.chat.id, call.from_user)
    else:
        bot.answer_callback_query(call.id, 'пока не вижу подписку', show_alert=True)
        send_gate(call.message.chat.id, call.from_user)


@bot.message_handler(func=lambda m: True)
def on_any(message):
    send_welcome(message.chat.id, message.from_user)


def webhook_base():
    return (os.getenv('WEBHOOK_URL') or os.getenv('RENDER_EXTERNAL_URL') or '').rstrip('/')


def run_webhook(url):
    from flask import Flask, request

    app = Flask(__name__)

    @app.get('/')
    @app.get('/health')
    def health():
        return 'ok', 200

    @app.post('/webhook')
    def telegram_webhook():
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return 'ok', 200

    bot.remove_webhook()
    bot.set_webhook(url=url + '/webhook')
    print('бот запущен по webhook:', url)
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '10000')))


if __name__ == '__main__':
    url = webhook_base()
    if url:
        run_webhook(url)
    else:
        try:
            bot.remove_webhook()
        except Exception:
            pass
        print('бот запущен, жду учеников…')
        bot.infinity_polling(skip_pending=True, allowed_updates=['message', 'callback_query'])
