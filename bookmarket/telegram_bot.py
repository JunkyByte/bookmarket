import logging
import time
import favicon
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
    update.message.reply_text('Hi! visit github to understand how I work')


def find_name(url):
    try:
        req = urllib.Request(url, headers=hdr)
        o = urllib.urlopen(req)
    except (URLError, socket.timeout):
        return None

    try:
        title = str(BeautifulSoup(o, features='lxml').title.string)
    except AttributeError:
        return None

    max_size = 40
    if len(title) > max_size:
        title = title[:max_size] + '...'
    return title


# def add(update: Update, context: CallbackContext) -> None: # TODO
def show_search(update: Update, context: CallbackContext) -> None:
    msg = update['message']['text'].split()
    if len(msg) == 0:  # Just an url
        update.message.reply_text('Something went wrong')
        return None

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

    title = find_name(url)
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
    return f'Does this look good?\n<b>Title: {r.title}</b>\nurl: {r.url}\ninfo: <pre>{r.info}</pre>\nts: {r.human_ts()}'


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


def showpreview(update: Update, context: CallbackContext) -> None:
    # search = context.args[0]
    # records = bm.all()
    records = bm.stime(start=time.time() - 60 * 60 * 24 * 14)
    for r in sorted(records):
        url = r.url
        if url.endswith('.pdf'):
            url = url[:url.rfind('.pdf')]
            if 'arxiv.org' in url:
                url = url.replace('pdf', 'abs')

        title = r.title or find_name(url)
        if r.title is None and title is not None:
            r_up = replace(r, title=title)
            bm.update(r_up)

        msg = '━' * 20 + '\n'
        msg += f'<b>{title}</b>\n{url}\n{r.human_ts()}\n'
        if r.info is not None:
            msg += f'\n<pre>{r.info}</pre>'

        update.message.reply_text(text=msg, parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=False)


def handle_invalid_button(update: Update, context: CallbackContext) -> None:
    """Informs the user that the button is no longer available."""
    update.callback_query.answer()
    update.effective_message.edit_text(
        'Sorry, I could not process this button click'
    )


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
    dispatcher.add_handler(MessageHandler(Filters.text, show_search))
    dispatcher.add_handler(CallbackQueryHandler(handle_invalid_button, pattern=InvalidCallbackData))
    dispatcher.add_handler(CallbackQueryHandler(add_callback))

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
