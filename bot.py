import html
import os
import telebot
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN', '').strip()
CHANNEL = os.getenv('CHANNEL', '@sashoshamath').strip()
SITE = os.getenv('SITE_URL', 'https://sashoshaa.github.io/sashosha-math/').strip()
HERE = os.path.dirname(os.path.abspath(__file__))
TRAINER_FILE = os.path.join(HERE, 'index.html')

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


def subscribe_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('подписаться на канал 🎀', url=CHANNEL_LINK))
    kb.add(InlineKeyboardButton('я уже подписан(а) 🤍', callback_data='check'))
    return kb


def file_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('получить файл 🩰', callback_data='getfile'))
    return kb


def send_gate(chat_id, user=None):
    name = first_name(user)
    hello = f'Привет, {name} 🤍' if name else 'Привет 🤍'
    bot.send_message(
        chat_id,
        f'{hello}\n\n'
        'В моём канале много полезного — лайфхаки, шпаргалки, разборы и мотивация 🎀\n'
        'Хочешь забрать сайт-тренажер по математике? 🩰\n\n'
        f'Подпишись на {CHANNEL} и нажми «я уже подписан(а)».\n'
        'Проверю подписку и только потом открою тренажёр!!',
        reply_markup=subscribe_keyboard(),
        disable_web_page_preview=True,
    )


def send_unlocked(chat_id, user):
    if not is_subscribed(getattr(user, 'id', None)):
        send_gate(chat_id, user)
        return
    name = first_name(user)
    hello = f'{name}, ты с нами 🩰🤍' if name else 'Ты с нами 🩰🤍'
    bot.send_message(
        chat_id,
        f'{hello}\n\n'
        'Нажми «получить файл» — пришлю тренажёр.',
        reply_markup=file_keyboard(),
    )


def send_trainer_file(chat_id, user):
    if not is_subscribed(getattr(user, 'id', None)):
        send_gate(chat_id, user)
        return
    name = first_name(user)
    caption = (
        f'{name}, вот файл тренажёра 🩰🤍\n'
        'Открой его в браузере и решай в своём темпе.'
        if name else
        'Вот файл тренажёра 🩰🤍\n'
        'Открой его в браузере и решай в своём темпе.'
    )
    with open(TRAINER_FILE, 'rb') as f:
        bot.send_document(
            chat_id,
            f,
            visible_file_name='sashosha-math.html',
            caption=caption,
        )


@bot.message_handler(commands=['start'])
def on_start(message):
    send_gate(message.chat.id, message.from_user)


@bot.message_handler(commands=['site'])
def on_site(message):
    send_unlocked(message.chat.id, message.from_user)


@bot.callback_query_handler(func=lambda c: c.data == 'check')
def on_check(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, 'есть подписка 🎀')
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
        send_unlocked(call.message.chat.id, call.from_user)
    else:
        bot.answer_callback_query(call.id, 'пока не вижу подписку', show_alert=True)
        send_gate(call.message.chat.id, call.from_user)


@bot.callback_query_handler(func=lambda c: c.data == 'getfile')
def on_getfile(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, 'отправляю файл 🩰')
        send_trainer_file(call.message.chat.id, call.from_user)
    else:
        bot.answer_callback_query(call.id, 'пока не вижу подписку', show_alert=True)
        send_gate(call.message.chat.id, call.from_user)


@bot.message_handler(func=lambda m: True)
def on_any(message):
    send_gate(message.chat.id, message.from_user)


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
