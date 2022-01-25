from tinydb import TinyDB, Query, where
from dataclasses import dataclass, field, asdict, replace
from datetime import datetime
from enforce_typing import enforce_types  # type: ignore
from typing import Optional, Sequence, Union, List
from datetime import datetime
from bs4 import BeautifulSoup
from tinyrecord import transaction
import requests
import socket
import time
Q = Query()
session = requests.Session()
session.max_redirects = 3


# @enforce_types  # TODO: Wrap manually before writing if you want
@dataclass(frozen=True, order=True)
class Record:
    url: Optional[str] = field(default=None, compare=False)
    title: Optional[str] = field(default=None, compare=False)
    info: Optional[str] = field(default=None, compare=False)
    ts: Optional[float] = field(default=None, compare=True)

    def query_dict(self):
        return {x: k for x, k in asdict(self).items() if k is not None}

    @property
    def human_ts(self):
        try:
            return datetime.fromtimestamp(self.ts).strftime('%Y-%m-%d %H:%M:%S')
        except TypeError:
            return None


# typing utility objects
Records = Union[Record, Sequence[Record]]
OptTimeType = Optional[Union[float, datetime]]


def find_infos(url):
    try:
        req = session.get(url, timeout=3, headers={'User-Agent': 'Magic Browser'})
    except (requests.Timeout, requests.HTTPError, requests.ConnectionError):
        return None, None

    soup = BeautifulSoup(req.content.decode('utf-8', 'ignore'), features='lxml')
    try:  # Try to get a title
        title = str(soup.title.string)
    except AttributeError:
        return None, None

    try:  # Try to get a description
        info = soup.find('meta', property='og:description')['content']
    except TypeError:
        info = None

    return title, info

def sanitize_url(url):
    if url.endswith('.pdf'):
        url = url[:url.rfind('.pdf')]
        if 'arxiv.org' in url:
            url = url.replace('pdf', 'abs')
    return url


class Bookmarket:
    """
    Main class, holds a reference to the database containing the bookmarks.
    Manages the methods that allow to write / read / view the database.
    Telegram etc will communicate with an instance of Bookmarket.
    """
    def __init__(self, db_path):
        self.db = TinyDB(db_path)

    def __len__(self):
        return len(self.db)

    def write(self, record: Records) -> List:
        """
        Add records to database.
        Raise error if there's a duplicate
        """

        if isinstance(record, Record):
            record = [record]

        res = []
        for r in record:
            if self.db.get(Q.url == r.url):
                raise FileExistsError(f'The entry {r.url!r} already exists')
            if r.ts is None:  # We do not allow entries without timestamp
                r = replace(r, ts=time.time())
            elif isinstance(r.ts, datetime):
                r = replace(r, ts=datetime.timestamp(r.ts))

            with transaction(self.db) as tr:
                res.append(tr.insert(asdict(r)))
        return res

    def update_all(self) -> None:
        """
        Update all records title and infos to the one you get from webscraping the site source
        """
        total = len(self)
        total_size = len(str(total))
        for ith, r in enumerate(self.all()):  # This is inefficient but it's fine
            url = sanitize_url(r.url)
            print(f'{ith:{total_size}}/{total} {url}')
            title, info = find_infos(url)
            r_up = replace(r, url=url, title=title, info=info)
            if url != r.url:
                self.delete(r)
                self.write(r_up)
            else:
                self.update(r_up)
        return None

    def search(self, q) -> Optional[List[Record]]:
        """
        Utility function to have search queries return Record objects
        """
        results = self.db.search(q)
        return [Record(**r) for r in results]

    def get(self, q) -> Optional[Record]:
        """
        Utility function to have get queries return Record objects
        Returns None if the query does not match anything
        """
        result = self.db.get(q)
        if result is None:
            return None
        return Record(**result)
    
    def delete(self, record: Record) -> None:
        """
        Delete a record
        """
        with transaction(self.db) as tr:
            return tr.remove(Q.url == record.url)

    def smatch(self, record: Record) -> Optional[List[Record]]:
        """
        Search for any entry that match a Record, only intialized (not None) fields are used
        """
        return self.search(Q.fragment(record.query_dict()))

    def stime(self, start: OptTimeType = None, end: OptTimeType = None) -> Optional[List]:
        """
        Search in the interval of time provided.
        Use datetime objects or timestamps,
        if start not provided it is the epoch
        if end not provided it is current timestamp
        """
        if isinstance(start, datetime):
            start = datetime.timestamp(start)
        elif start is None:
            start = 0

        if isinstance(end, datetime):
            end = datetime.timestamp(end)
        elif end is None:
            end = time.time()

        return self.search((Q.ts >= start) & (Q.ts < end))

    def update(self, record: Record) -> bool:
        """
        Update entry that matches the record url passed.
        Will only update record initialized fields.
        """
        with transaction(self.db) as tr:
            return bool(tr.update(record.query_dict(), Q.url == record.url))

    def all(self) -> List[Record]:
        return [Record(**r) for r in self.db.all()]

    def truncate(self):
        with transaction(self.db) as tr:
            tr.truncate()

    def close(self):
        self.db.close()
