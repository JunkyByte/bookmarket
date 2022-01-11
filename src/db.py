from tinydb import TinyDB, Query, where
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enforce_typing import enforce_types
from typing import Optional, Sequence, Union
from datetime import datetime
import time
Q = Query()


@enforce_types
@dataclass
class Record:
    url: Optional[str] = None
    title: Optional[str] = None
    info: Optional[str] = None
    ts: Optional[float] = None

    def __eq__(self, other):
        if not isinstance(other, Record):
            raise TypeError('a Record can only be compared to a Record')
        return self.url == other.url

    def query_dict(self):
        return {x: k for x, k in asdict(self).items() if k is not None}


class Bookmarket:
    """
    Main class, holds a reference to the database containing the bookmarks.
    Manages the methods that allow to write / read / view the database.
    Telegram etc will communicate with an instance of Bookmarket.
    """
    def __init__(self, db_path):
        self.db = TinyDB(db_path)

    def write(self, record: Union[Record, Sequence[Record]]):
        """
        Add records to database.
        Raise error if there's a duplicate
        """

        if isinstance(record, Record):
            record = [record]

        for r in record:
            if self.db.get(Q.url == r.url):
                # TODO:
                # Here we could use db.upsert to update fields if it already exists, removing timestamp
                # might be a good solution to keep original creation date but be able to update infos using write
                # on the otherhand maybe search -> manual change fields -> update method (TODO) could be cleaner.
                raise FileExistsError(f'The entry {r.url!r} already exists')
            if r.ts is None:  # We do not allow entries without timestamp
                r.ts = time.time()
            self.db.insert(asdict(r))

    def smatch(self, record: Record):
        """
        Search for any entry that match a Record, only intialized (not None) fields are used
        """
        results = self.db.search(Q.fragment(record.query_dict()))
        return [Record(**r) for r in results]

    def stime(self, start: Union[float, datetime] = 0., end: Optional[Union[float, datetime]] = None):
        """
        Search in the interval of time provided.
        Use datetime objects or timestamps,
        if start not provided it is the epoch
        if end not provided it is current timestamp
        """
        if isinstance(start, datetime):
            start = datetime.timestamp(start)
        if isinstance(end, datetime):
            end = datetime.timestamp(end)
        if end is None:
            end = time.time()
        results = self.db.search((Q.ts >= start) & (Q.ts < end))
        return results

    def all(self):
        return self.db.all()


if __name__ == '__main__':
    db = Bookmarket('/tmp/test_db.json')
    db.db.truncate()

    r = Record(url='https://www.google.com', title='just google', info='A bookmark', ts=time.time())
    print(r)
    print(db.all())

    db.write(r)
    print(db.all())

    print(db.smatch(r))
    r = Record(title='just google')
    print(r, db.smatch(r))

    t1 = datetime(2019, 1, 1)
    t2 = None

    r_old = Record(url='https://www.google2.com', title='just google2', info='A bookmark',
                   ts=datetime.timestamp(datetime(2010, 1, 1)))

    db.write(r_old)
    print(db.stime(start=t1))
    print(db.stime(end=t1))
