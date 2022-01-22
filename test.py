import unittest
import time
from dataclasses import asdict
from datetime import datetime
from bookmarket.bookmarket import Bookmarket, Record


class TestDB(unittest.TestCase):
    def setUp(self):
        self.bm = Bookmarket('/tmp/bookmarket_db_test.py')

    def tearDown(self):
        self.bm.truncate()
        self.bm.close()

    def test_write(self):
        r = Record(url='https://www.google.com', title='just google', info='A bookmark', ts=time.time())
        r_id = self.bm.write(r)
        self.assertEqual(self.bm.db.get(doc_id=r_id[0]), asdict(r))

        try:  # TODO This might not be the correct place to check this works correctly.
            r2 = Record(url='https://www.new.com', title='just google', info='A bookmark', ts=None)
            r2_id = self.bm.write(r2)
        except dataclasses.FrozenInstanceError:
            self.fail('Writing a record with no timestamp raised an error')

        with self.assertRaises(FileExistsError):
            self.bm.write(r)
    
    def test_smatch(self):
        t0 = time.time()
        r_og = Record(url='https://www.google.com', title='just google', info='A bookmark', ts=t0)
        r_og2 = Record(url='https://www.facebook.com', title='just facebook', info='happy sad', ts=time.time())
        self.bm.write(r_og)
        self.bm.write(r_og2)

        qs = []
        qs.append(Record(title='just google'))
        qs.append(Record(title='just title not found'))
        qs.append(Record(url='https://www.facebook.com'))
        qs.append(Record(url='https://notfound.org'))
        qs.append(Record(info='happy sad'))
        qs.append(Record(info='not found infos'))
        qs.append(Record(ts=t0))  # Found is r_og
        qs.append(Record(ts=time.time()))  # Not found
        exp_res = [r_og, [], r_og2, [], r_og2, [], r_og, []]

        for i, q in enumerate(qs):
            res = self.bm.smatch(q)
            if exp_res[i]:
                res = res[0]
            self.assertEqual(res, exp_res[i])

    def test_stime(self):
        # Add entries with different timestamps
        t2012 = datetime.timestamp(datetime(2012, 1, 1))
        r2012 = Record(url='https://www.google.com', title='just google', info='A bookmark', ts=t2012)

        t2015 = datetime.timestamp(datetime(2015, 1, 1))
        r2015 = Record(url='https://www.facebook.com', title='just facebook', info='sad', ts=t2015)

        t2018 = datetime.timestamp(datetime(2018, 1, 1))
        r2018 = Record(url='https://www.apple.com', title='just apple', info='whew', ts=t2018)
        self.bm.write(r2012)
        self.bm.write(r2015)
        self.bm.write(r2018)

        qs = []
        qs.append([datetime(2010, 1, 1), datetime(2014, 1, 1)])
        qs.append([datetime(2016, 1, 1), None])
        qs.append([None, datetime(2016, 1, 1)])
        qs.append([datetime(2014, 1, 1), datetime(2020, 1, 1)])
        qs.append([datetime(2020, 1, 1), None])
        qs.append([None, datetime(2010, 1, 1)])
        exp_res = [[r2012], [r2018], [r2012, r2015], [r2015, r2018], [], []]

        for i, (t0, t1) in enumerate(qs):
            res = self.bm.stime(t0, t1)
            if exp_res[i] is None:
                self.assertEqual(res, None)
            else:
                self.assertEqual(set(res), set(exp_res[i]))

    def test_update(self):
        ts0 = datetime.timestamp(datetime(2010, 1, 1))
        title0 = 'just google2'
        info0 = 'a bookmark'

        ts1 = datetime.timestamp(datetime(2020, 1, 1))
        title1 = 'just updated title'
        info1 = 'just updated info'

        from tinydb import Query
        Q = Query()

        # Check changing different number of params with valid update Query
        r = Record(url='https://www.google.com', title=title0, info=info0, ts=ts0)
        self.bm.write(r)
        r_up = Record(url='https://www.google.com', title=title1)
        self.assertTrue(self.bm.update(r_up))
        res = self.bm.get(Q.url == r_up.url)
        self.assertEqual(r.ts, res.ts)
        self.assertEqual(r.info, res.info)
        self.assertEqual(r_up.title, res.title)
        self.bm.truncate()

        r = Record(url='https://www.google.com', title=title0, info=info0, ts=ts0)
        self.bm.write(r)
        r_up = Record(url='https://www.google.com', info=info1)
        self.assertTrue(self.bm.update(r_up))
        res = self.bm.get(Q.url == r_up.url)
        self.assertEqual(r.ts, res.ts)
        self.assertEqual(r.title, res.title)
        self.assertEqual(r_up.info, res.info)
        self.bm.truncate()

        r = Record(url='https://www.google.com', title=title0, info=info0, ts=ts0)
        self.bm.write(r)
        r_up = Record(url='https://www.google.com', title=title1, info=info1)
        self.assertTrue(self.bm.update(r_up))
        res = self.bm.get(Q.url == r_up.url)
        self.assertEqual(r.ts, res.ts)
        self.assertEqual(r_up.title, res.title)
        self.assertEqual(r_up.info, res.info)
        self.bm.truncate()

        r = Record(url='https://www.google.com', title=title0, info=info0, ts=ts0)
        self.bm.write(r)
        r_up = Record(url='https://www.google.com', title=title1, info=info1, ts=ts1)
        self.assertTrue(self.bm.update(r_up))
        res = self.bm.get(Q.url == r_up.url)
        self.assertEqual(r_up.ts, res.ts)
        self.assertEqual(r_up.title, res.title)
        self.assertEqual(r_up.info, res.info)
        self.bm.truncate()

        # Update with non existent query (False on return of Update function)
        r = Record(url='https://www.google.com', title=title0, info=info0, ts=ts0)
        self.bm.write(r)
        r_up = Record(url='https://www.notexist.com', info='fake')
        self.assertFalse(self.bm.update(r_up))


if __name__ == '__main__':
    unittest.main()
