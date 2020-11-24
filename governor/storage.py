from datetime import timedelta
import sqlite3
import pickle


class GovernorStorage:
    """
    Governor Storage

    Class for shared Storage between Governor Charm (Governor Event Handler) and
    Governor Broker.
    """

    DB_LOCK_TIMEOUT = timedelta(hours=1)

    def __init__(self, filename):
        # The isolation_level argument is set to None such that the implicit
        # transaction management behavior of the sqlite3 module is disabled.
        self._db = sqlite3.connect(
            str(filename),
            isolation_level=None,
            timeout=self.DB_LOCK_TIMEOUT.total_seconds(),
        )
        self._setup()

    def _setup(self):
        """ Setup sqlite database. """
        # Make sure that the database is locked until the connection is closed,
        # not until the transaction ends.
        self._db.execute("PRAGMA locking_mode=EXCLUSIVE")
        cursor = self._db.execute("BEGIN")
        cursor.execute(
            "SELECT count(name) FROM sqlite_master WHERE type='table' AND name='governor'"
        )
        if cursor.fetchone()[0] == 0:
            # Keep in mind what might happen if the process dies somewhere below.
            # The system must not be rendered permanently broken by that.
            self._db.execute(
                "CREATE TABLE governor (timestamp TEXT PRIMARY KEY, data BLOB)"
            )
            self._db.commit()

    def write_event_data(self, data):
        """ Write event data with timestamp. """
        raw_data = pickle.dumps(data)
        self._db.execute(
            "REPLACE INTO governor VALUES (datetime('now'), ?)", (raw_data,)
        )
        self._db.commit()

    def read_all_event_data(self):
        """ Read all events ordered by timestamp and delete from storage. """
        cursor = self._db.cursor()
        cursor.execute("SELECT data FROM governor ORDER BY timestamp ASC")
        raw_rows = cursor.fetchall()

        rows = []

        for raw_row in raw_rows:
            rows.append(pickle.loads(raw_row[0]))

        self._db.execute("DELETE FROM governor")

        self._db.commit()
        return rows

    def close(self):
        """ Close Database. """
        self._db.close()
