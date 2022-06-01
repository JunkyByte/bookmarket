import logging
import sys
import os
import time
import socket
import telegram
import timestring
from bs4 import BeautifulSoup
from telegram.ext import (
        Updater, CommandHandler, CallbackContext, MessageHandler, Filters,
        CallbackQueryHandler, InvalidCallbackData
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup
from datetime import datetime, timedelta
from bookmarket import Bookmarket, Record, find_infos, sanitize_url
from dataclasses import replace
import requests
from requests.exceptions import InvalidURL, MissingSchema, InvalidSchema
from tinydb import Query
user_id = None
Q = Query()
bm = Bookmarket('./data/db.json')
session = requests.Session()
session.max_redirects = 3


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id != user_id:
        return

    update.message.reply_text('Hi! I am the bookmarket bot')


def handle_msg(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id != user_id:
        return

    msg = update['message']['text']
    if not len(msg):
        update.message.reply_text('Something went wrong')
        return None
    cmd = msg.lower().split()[0]

    if cmd in ['st', 'at', 'searchtime']:
        search_time(update, context)
        return None

    if cmd in ['s', 'a', 'search']:
        search(update, context)
        return None

    add_or_delete(update, context)
    return None


def any_in(field, *patterns):
    if field is None:
        return False
    return all(p.lower() in field.lower() for p in patterns)

def search_time(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id != user_id:
        return

    msg = ' '.join(update['message']['text'].split()[1:])
    try:
        rg = timestring.Range(msg)
    except timestring.TimestringInvalid:
        update.message.reply_text('Could not parse the time!')
        return None

    rs = bm.stime(rg.start.to_unixtime(), rg.end.to_unixtime())
    if rs:
        msg_records(update, rs)
    else:
        update.message.reply_text('Did not find a single thing!')
    return None


def search(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id != user_id:
        return

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


def search(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id != user_id:
        return

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


def add_or_delete(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id != user_id:
        return

    msg = update['message']['text'].split()
    url = msg.pop(0)
    url = sanitize_url(url)
    title, info = None, None

    # First decide if we want to add or delete
    action_name = 'Delete'
    premsg = 'This url already exists, do you want to delete it? 🤔\n'
    action = 'delete'
    r = bm.get(Q.url == url)
    if r is None:
        action_name = 'Add'
        action = 'add'
        premsg = 'This url does not exist, want to add it? 🤔\n'
        try:  # I mean this is slow, 2 full reqs for no reason TODO
            req = session.get(url, headers={'User-Agent': 'Magic Browser'})
        except (InvalidURL, MissingSchema, InvalidSchema, requests.Timeout,
                requests.HTTPError, requests.ConnectionError):
            update.message.reply_text('Could not open the link you passed')
            return None, None

        if msg:
            title = msg.pop(0)
            info = ' '.join(msg)

        if title is None or info is None:
            stitle, sinfo = find_infos(url)
            title = stitle if title is None else title
            info = sinfo if info is None else info

        r = Record(url=url, title=title, info=info or None)

    keyboard = [
        InlineKeyboardButton(action_name, callback_data=(action, r)),
        InlineKeyboardButton("Cancel", callback_data='cancel'),
    ]

    reply_markup = InlineKeyboardMarkup.from_column(keyboard)
    msg = premsg + preview_record(r)
    update.message.reply_text(msg, reply_markup=reply_markup,
                              parse_mode=telegram.ParseMode.HTML,
                              disable_web_page_preview=True)
    return None


def preview_record(r):
    title = r.title[:80] if r.title is not None else None
    info = r.info[:125].replace('\n', ' ') if r.info is not None else None
    return f'<b>Title: {title}</b>\nurl: {r.url}\ninfo: <pre>{info}</pre>\nts: {r.human_ts}'


def handle_callback(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id != user_id:
        return

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
    if cmd == 'update':
        update_callback(update, context)

    return None


def delete_callback(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id != user_id:
        return

    query = update.callback_query
    try:
        bm.delete(query.data)
        query.edit_message_text(text=f"Deleted the record for a current total of {len(bm)} bookmarks")
    except FileNotFoundError:
        query.edit_message_text(text='The url does not exists! 🙃')
    return None


def add_callback(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id != user_id:
        return

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
    if update.message.chat_id != user_id:
        return

    rs = bm.stime(start=time.time() - 60 * 60 * 24 * 14)
    return None if not rs else msg_records(update, rs)


def show_stats(update: Update, context: CallbackContext) -> None:
    # Show total bookmarks, added today / week / month / year
    msg = '<b>Bookmarket stats</b> 📊\n'
    msg += f'Total bookmarks: <b>{len(bm)}</b>\n'
    today = datetime.now() - timedelta(days=1)
    msg += f'Added today: <b>{len(bm.stime(start=today))}</b>\n'
    week = datetime.now() - timedelta(weeks=1)
    msg += f'Added this week: <b>{len(bm.stime(start=week))}</b>\n'
    month = datetime.now() - timedelta(days=30)
    msg += f'Added this month: <b>{len(bm.stime(start=month))}</b>\n'
    year = datetime.now() - timedelta(days=365)
    msg += f'Added this year: <b>{len(bm.stime(start=year))}</b>\n'
    update.message.reply_text(text=msg, parse_mode=telegram.ParseMode.HTML,
                              disable_web_page_preview=False)


def update_confirm(update: Update, context: CallbackContext) -> None:
    keyboard = [
        InlineKeyboardButton("You sure?", callback_data=('update', None)),
        InlineKeyboardButton("Cancel", callback_data='cancel'),
    ]

    reply_markup = InlineKeyboardMarkup.from_column(keyboard)
    update.message.reply_text('Are you sure you want to update all entries? Will take a while',
                              reply_markup=reply_markup, parse_mode=telegram.ParseMode.HTML,
                              disable_web_page_preview=True)
    return None

def update_callback(update: Update, context: CallbackContext):
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



def main() -> None:
    global user_id

    # Check key file
    key_file = 'bookmarket/bot.key'
    if not os.path.isfile(key_file):
        print('telegram bot key file does not exist and will be created as ./bookmarket/bot.key')
        print('Please paste your telegram token in it')
        open(key_file, 'a').close()
        sys.exit()

    # Start the bot
    with open(key_file, 'r') as f:
        key, user_id, *_ = f.read().split('\n')
        user_id = int(user_id)
    updater = Updater(key, arbitrary_callback_data=True)
    updater.bot.set_my_commands([
        ('/p', 'preview last few added bookmarks'),  # TODO
        ('/stats', 'show stats'),
        ('/updateall', 'update all entries')
    ])

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))  # TODO
    dispatcher.add_handler(CommandHandler("p", show_preview))
    dispatcher.add_handler(CommandHandler("stats", show_stats))
    dispatcher.add_handler(CommandHandler("updateall", update_confirm))

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
