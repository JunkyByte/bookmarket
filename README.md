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
Simply share a link and the bot will prompt you a confirm checkbox.
You can search by keywords using any of the following `[search, s, a] <keywords>`
Or search by time using `[seachtime, st, at] <time>` the time is parsed using `timestring` library which neatly parses *informal*
timestamps (e.g. `searchtime since last week`)
To delete a url just use `[delete, d] url`
