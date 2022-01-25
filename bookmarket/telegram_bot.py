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
from bookmarket import Bookmarket, Record, find_infos, sanitize_url
from dataclasses import replace
import requests
from requests.exceptions import InvalidURL, MissingSchema, InvalidSchema
from tinydb import Query
Q = Query()
bm = Bookmarket('./data/test_db.json')
session = requests.Session()
session.max_redirects = 3


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hi! I am the bookmarket bot')


def handle_msg(update: Update, context: CallbackContext) -> None:
    msg = update['message']['text']
    if not len(msg):
        update.message.reply_text('Something went wrong')
        return None
    cmd = msg.lower().split()[0]
    if cmd in ['s', 'a', 'search']:
        search(update, context)
        return None
    elif cmd in ['d', 'delete']:
        delete(update, context)
        return None

    add(update, context)
    return None


def any_in(field, *patterns):
    if field is None:
        return False
    return all(p.lower() in field.lower() for p in patterns)


def delete(update: Update, context: CallbackContext) -> None:
    msg = set(update['message']['text'].split()[1:])
    for m in msg:
        r = bm.get(Q.url == m)
        if r is None:
            update.message.reply_text('The url does not exists! 🙃')
            continue

        keyboard = [
            InlineKeyboardButton("Delete", callback_data=('delete', r)),
            InlineKeyboardButton("Cancel", callback_data='cancel'),
        ]

        reply_markup = InlineKeyboardMarkup.from_column(keyboard)
        update.message.reply_text(preview_record(r), reply_markup=reply_markup,
                                  parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=True)
    return None


def search(update: Update, context: CallbackContext) -> None:
    msg = set(update['message']['text'].split()[1:])
    msg = [m for m in msg if m != ' ']

    rs = set(bm.search(Q.title.test(any_in, *msg)))
    rs.update(bm.search(Q.url.test(any_in, *msg)))
    rs.update(bm.search(Q.info.test(any_in, *msg)))

    if rs:
        msg_records(update, rs)
    else:
        update.message.reply_text('Did not find a single thing!')
    return None

def add(update: Update, context: CallbackContext) -> None:
    msg = update['message']['text'].split()
    url = msg.pop(0)

    try:  # I mean this is slow, 2 full reqs for no reason TODO
        req = session.get(url, headers={'User-Agent': 'Magic Browser'})
    except (InvalidURL, MissingSchema, InvalidSchema, requests.Timeout,
            requests.HTTPError, requests.ConnectionError):
        update.message.reply_text('Could not open the link you passed')
        return None, None

    info = ' '.join(msg) if msg else ''
    title, info2 = find_infos(url)
    if info2 is not None:
        info += ' ' + info2

    r = Record(url=url, title=title, info=info or None)

    keyboard = [
        InlineKeyboardButton("Confirm", callback_data=('add', r)),
        InlineKeyboardButton("Cancel", callback_data='cancel'),
    ]

    reply_markup = InlineKeyboardMarkup.from_column(keyboard)
    update.message.reply_text(preview_record(r), reply_markup=reply_markup,
                              parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=True)
    return None


def preview_record(r):
    title = r.title[:80] if r.title is not None else None
    info = r.info[:125].replace('\n', ' ') if r.info is not None else None
    return f'How does it look?\n<b>Title: {title}</b>\nurl: {r.url}\ninfo: <pre>{info}</pre>\nts: {r.human_ts}'


def handle_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'cancel':
        query.edit_message_text(text='Okay whatever 🤨')
        return None
    
    cmd, data = query.data
    query.data = data

    if cmd == 'add':
        add_callback(update, context)
    if cmd == 'delete':
        delete_callback(update, context)
    
    return None


def delete_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    try:
        bm.delete(query.data)
        query.edit_message_text(text=f"Deleted the record for a current total of {len(bm)} bookmarks")
    except FileNotFoundError:
        query.edit_message_text(text='The url does not exists! 🙃')
    return None


def add_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    try:
        bm.write(query.data)
        query.edit_message_text(text=f"Added the new record for a total of {len(bm)} bookmarks 👍")
    except FileExistsError:
        query.edit_message_text(text='The url already exists! 🙃')
    return None


def msg_records(update, rs, show_desc=True):
    for r in sorted(rs):
        url = sanitize_url(r.url)
        title = r.title
        info = r.info

        # TODO probably this part can be removed or differently managed?
        # They should be already populate on add right?
        if r.title is None or r.info is None:
            title, info = find_infos(url)  # TODO

        if r.title is None and title is not None:
            r_up = replace(r, title=title)
            bm.update(r_up)
        if r.info is None and info is not None:
            r_up = replace(r, info=info)
            bm.update(r_up)

        if title is not None and len(title) > 80:
            title = title[:80] + '...'

        msg = f'<b>{title}</b>\n{url}\n{r.human_ts}\n'
        if r.info is not None and show_desc:
            info = info[:125].replace('\n', ' ')
            msg += f'<pre>{info + "..."}</pre>'

        update.message.reply_text(text=msg, parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=False)


def show_preview(update: Update, context: CallbackContext) -> None:  # TODO
    rs = bm.stime(start=time.time() - 60 * 60 * 24 * 14)
    return None if not rs else msg_records(update, rs)


def update_all(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(text='Updating all entries 👍 give me some slack')
    bm.update_all()
    update.message.reply_text(text='Finished updating the entries 👍')
    return None


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
        ('/updateall', 'update all entries')
    ])

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))  # TODO
    dispatcher.add_handler(CommandHandler("p", show_preview))
    dispatcher.add_handler(CommandHandler("updateall", update_all))

    # Callback with menu
    dispatcher.add_handler(MessageHandler(Filters.text, handle_msg))
    dispatcher.add_handler(CallbackQueryHandler(handle_invalid_button,
                                                pattern=InvalidCallbackData))
    dispatcher.add_handler(CallbackQueryHandler(handle_callback))

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
