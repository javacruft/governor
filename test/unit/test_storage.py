from unittest.mock import patch
from unittest import TestCase
import pickle

from governor.storage import GovernorStorage


class GovernorStorageTestCase(TestCase):
    def setUp(self):
        self.storage = GovernorStorage("test_storage")

    def test_setup(self):
        with patch("governor.storage.sqlite3") as mocksql:
            mocksql.connect().execute().fetchone.return_value = [0]
            GovernorStorage("test_storage")
            mocksql.connect.assert_called_with(
                "test_storage",
                isolation_level=None,
                timeout=3600,
            )
            mocksql.connect().execute.assert_called()
            mocksql.connect().execute().execute.assert_called()
            mocksql.connect().execute().fetchone.assert_called()
            mocksql.connect().commit.assert_called()

    def test_write_event_data(self):
        with patch("governor.storage.sqlite3"):
            data = {"data_key": "data"}
            raw_data = pickle.dumps(data)
            self.storage.write_event_data(data)
            self.storage._db.execute.assert_called_with(
                "REPLACE INTO governor VALUES (datetime('now'), ?)", (raw_data,)
            )
            self.storage._db.commit.assert_called()

    def test_read_all_event_data(self):
        with patch("governor.storage.sqlite3"):
            data1 = {"data_key1": "data"}
            data2 = {"data_key2": "data"}
            all_data = [[pickle.dumps(data1)], [pickle.dumps(data2)]]
            self.storage._db.cursor().fetchall.return_value = all_data
            event_data = self.storage.read_all_event_data()
            assert event_data == [data1, data2]
            self.storage._db.cursor().fetchall.assert_called()
            self.storage._db.commit.assert_called()
            self.storage._db.execute.assert_called()

    def test_close(self):
        with patch("governor.storage.sqlite3"):
            self.storage.close()
            self.storage._db.close.assert_called()
