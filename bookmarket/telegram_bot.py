import logging
import time
import favicon
import socket
import telegram
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from bookmarket import Bookmarket, Record
from dataclasses import replace
import requests
from lxml.html import fromstring
import eventlet

bm = Bookmarket('./data/test_db.json')
# bm = Bookmarket('/tmp/bookmarket_db_test.py')
# bm.truncate()
# r = Record(url='https://www.google.com', title='Google', info='A bookmark with a slightly longer des', ts=time.time())
# bm.write(r)
# r = Record(url='https://asselin.engineer/stylus', ts=time.time())
# bm.write(r)
# r = Record(url='https://github.com/yenchenlin/nerf-pytorch', ts=time.time())
# bm.write(r)


"""
To add
https://stackoverflow.com/questions/21965484/timeout-for-python-requests-get-entire-response
https://creiser.github.io/kilonerf/
https://myminifactory.github.io/Fast-Quadric-Mesh-Simplification/
https://www.toptal.com/algorithms/shazam-it-music-processing-fingerprinting-and-recognition
https://math.stackexchange.com/questions/598934/projection-into-a-subspace
https://stackoverflow.com/questions/61215439/robustly-finding-the-local-maximum-of-an-image-patch-with-sub-pixel-accuracy
https://github.com/BlueHatbRit/mdpdf
"""


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> None:
    """Sends explanation on how to use the bot."""
    update.message.reply_text('Hi! Use /set <seconds> to set a timer')


def find_name(url):
    try:
        print(url)
        with eventlet.Timeout(1):
            o = requests.get(url)
        print(o)
    except (URLError, socket.timeout):
        return None
    print(o)
    title = BeautifulSoup(o, features='lxml').title.string
    max_size = 40
    if len(title) > max_size:
        title = title[:max_size] + '...'
    return title


# def add(update: Update, context: CallbackContext) -> None: # TODO

def showpreview(update: Update, context: CallbackContext) -> None:
    # search = context.args[0]
    # records = bm.all()
    records = bm.stime(start=time.time() - 60 * 60 * 24 * 14)
    for r in records:
        # title = r.title or find_name(r.url)
        # if r.title is None and title is not None:
        #     r_up = replace(r, title=title)
        #     bm.update(r_up)
        title = r.title or ''
        msg = f'\n<b>{title}</b>\n{r.url}\n{r.human_ts()}'
        if r.info is not None:
            msg += f'\n<pre>{r.info}</pre>'
        update.message.reply_text(
                text=msg,
                parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=False)


def main() -> None:
    """Run bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater("5010426285:AAE4oP-k9dB1eeR2nyBHBgiEHnXi-8Wn8FM")

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))  # TODO
    dispatcher.add_handler(CommandHandler("p", showpreview))

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
