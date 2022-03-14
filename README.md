# bookmarket

Bookmarket is a tiny project written completely in python to self host a bookmark manager that's browser and device agnostic.
The `Bookmarket` class manages the interactions with a `TinyDB` database to store your bookmarks, you can interact with the database
through telegram with the already implemented bot or write your own communication system.
Each bookmark is internally represented by a `Record` object with the attributes `url, title, info, timestamp`.

The `Bookmarket` features are:
- it (*should*) be thread-safe
- it allows you to add, update, remove and search your bookmarks.
- on add the site is scraped and a title and description is automatically added if found
- you can search timewise, by Query (see `TinyDB` queries) or by fragment of a Record

In its current state the telegram bot allows you to add and delete bookmarks by link and to search by keywords or time.
Simply share a link and the bot will prompt you a confirmation checkbox.

```
Commands: (each value in the square bracket is equivalent)
Search by keywords: [search, s, a] <keywords>
Search by time with: [seachtime, st, at] <time>
note: the time is parsed using the `timestring` python library which neatly parses "informal"
timestamps (e.g. 'searchtime since last week' works just fine)
Delete a url with `[delete, d] url`
```

## Setup

An informal list of requirements can be found in `requirements.txt`.

To install and serve through telegram first create a new bot using `@BotFather` then clone and run with:
```
git clone git@github.com:JunkyByte/bookmarket.git
cd bookmarket
python bookmarket/telegram_bot.py
```
It will create a key file where you can paste your access token.

----

`Bookmarket` is a personal project, no complete coverage nor thorough unit testing has been done, use it at your own risk, we do not take any responsability for its behaviour.
