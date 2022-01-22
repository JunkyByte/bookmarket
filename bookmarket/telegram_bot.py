import logging
import time
import socket
import telegram
from bs4 import BeautifulSoup
from telegram.ext import (
        Updater, CommandHandler, CallbackContext, MessageHandler, Filters,
        CallbackQueryHandler, InvalidCallbackData
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from bookmarket import Bookmarket, Record
from dataclasses import replace
from urllib.error import URLError
import urllib.request as urllib
from tinydb import Query
Q = Query()
hdr = { 'User-Agent': 'Magic Browser' }

bm = Bookmarket('./data/test_db.json')
# bm = Bookmarket('/tmp/bookmarket_db_test.py')
# bm.truncate()
# r = Record(url='https://www.google.com', title='Google', info='A bookmark with a slightly longer des', ts=time.time())
# bm.write(r)
# r = Record(url='https://asselin.engineer/stylus', ts=time.time())
# bm.write(r)
# r = Record(url='https://github.com/yenchenlin/nerf-pytorch', ts=time.time())
# bm.write(r)


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hi! I am the bookmarket bot')


def find_name(url):
    try:
        req = urllib.Request(url, headers=hdr)
        o = urllib.urlopen(req)
    except (URLError, socket.timeout):
        return None, None

    soup = BeautifulSoup(o, features='lxml')
    try:
        title = str(soup.title.string)
    except AttributeError:
        return None, None

    max_size = 40
    if len(title) > max_size:
        title = title[:max_size] + '...'

    try:
        info = soup.find('meta', property='og:description')['content']
    except TypeError:
        info = None
    return title, info

def handle_msg(update: Update, context: CallbackContext) -> None:
    msg = update['message']['text']
    if not len(msg):
        update.message.reply_text('Something went wrong')
        return None
    if msg.lower()[0] == 's':
        search(update, context)
        return None

    add(update, context)
    return None

def any_in(field, *patterns):
    if field is None:
        return False
    return all(p.lower() in field.lower() for p in patterns)

def search(update: Update, context: CallbackContext) -> None:
    msg = set(update['message']['text'].split()[1:])

    rs = set(bm.search(Q.title.test(any_in, *msg)))
    rs.update(bm.search(Q.url.test(any_in, *msg)))
    rs.update(bm.search(Q.info.test(any_in, *msg)))

    if rs:
        msg_records(update, rs)
    return None

def add(update: Update, context: CallbackContext) -> None:
    msg = update['message']['text'].split()
    url = msg.pop(0)
    try:
        req = urllib.Request(url, headers=hdr)
        _ = urllib.urlopen(req)
    except (URLError, socket.timeout, ValueError):
        update.message.reply_text('Could not open the link you passed')
        return None

    # title = None  # TODO
    # if msg:
    #     title = msg.pop(0)

    info = None
    if msg:
        info = ' '.join(msg)

    title, info2 = find_name(url)
    if info2 is not None:
        info += ' ' + info2

    r = Record(url=url, title=title, info=info)

    keyboard = [
        InlineKeyboardButton("Confirm", callback_data=r),
        InlineKeyboardButton("Cancel", callback_data='cancel'),
    ]

    reply_markup = InlineKeyboardMarkup.from_column(keyboard)
    update.message.reply_text(preview_record(r), reply_markup=reply_markup,
                              parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=True)
    return None


def preview_record(r):
    return f'Does this look good?\n<b>Title: {r.title}</b>\nurl: {r.url}\ninfo: <pre>{r.info}</pre>\nts: {r.human_ts}'


def add_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'cancel':
        query.edit_message_text(text='Okay whatever 🤨')
        return None

    try:
        bm.write(query.data)
    except FileExistsError:
        query.edit_message_text(text='The url already exists! 🙃')
    query.edit_message_text(text=f"Added the new record for a total of {len(bm)} bookmarks 👍")
    return None

def msg_records(update, rs, show_desc=True):
    for r in rs:
        url = r.url
        if url.endswith('.pdf'):
            url = url[:url.rfind('.pdf')]
            if 'arxiv.org' in url:
                url = url.replace('pdf', 'abs')

        title = r.title
        info = r.info
        if r.title is None or r.info is None:
            title, info = find_name(url)  # TODO

        if r.title is None and title is not None:
            r_up = replace(r, title=title)
            bm.update(r_up)
        if r.info is None and info is not None:
            r_up = replace(r, info=info)
            bm.update(r_up)

        # msg = '━' * 20 + '\n'  # TODO: maybe remove is ugly
        msg += f'<b>{title}</b>\n{url}\n{r.human_ts}\n'
        if r.info is not None and show_desc:
            info = info[:125].replace('\n', '')
            msg += f'<pre>{info + "..."}</pre>'

        update.message.reply_text(text=msg, parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=False)


def showpreview(update: Update, context: CallbackContext) -> None:  # TODO
    rs = bm.stime(start=time.time() - 60 * 60 * 24 * 14)
    return None if not rs else msg_records(update, rs)


def handle_invalid_button(update: Update, context: CallbackContext) -> None:
    """Informs the user that the button is no longer available."""
    update.callback_query.answer()
    update.effective_message.edit_text(
        'Sorry, I could not process this button click'
    )


def is_search(s):
    return s.lower[0] == 's'


def main() -> None:
    """Run bot."""
    updater = Updater("5010426285:AAE4oP-k9dB1eeR2nyBHBgiEHnXi-8Wn8FM", arbitrary_callback_data=True)
    updater.bot.set_my_commands([
        ('/p', 'preview'),  # TODO
    ])

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))  # TODO
    dispatcher.add_handler(CommandHandler("p", showpreview))

    # Callback with menu
    dispatcher.add_handler(MessageHandler(Filters.text, handle_msg))
    dispatcher.add_handler(CallbackQueryHandler(handle_invalid_button,
                                                pattern=InvalidCallbackData))
    dispatcher.add_handler(CallbackQueryHandler(add_callback))

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
