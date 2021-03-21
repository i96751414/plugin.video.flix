import os
import sqlite3

from lib.api.flix.kodi import ADDON_DATA


class Storage(object):
    def __init__(self, database):
        self.conn = sqlite3.connect(database)
        self.cursor = self.conn.cursor()

    def execute_and_commit(self, *args, **kwargs):
        self.execute(*args, **kwargs)
        self.commit()

    def execute(self, *args, **kwargs):
        return self.cursor.execute(*args, **kwargs)

    def commit(self):
        self.conn.commit()

    def select_page(self, query, size, page_number, *args, **kwargs):
        return self.cursor.execute(query + " LIMIT {:d} OFFSET {:d}".format(size, size * (page_number - 1)),
                                   *args, **kwargs)

    def pages_count(self, table_name, page_size, **kwargs):
        return (self.count(table_name, **kwargs) + page_size - 1) // page_size

    def delete(self, table_name, **kwargs):
        where, values = self._where(kwargs)
        self.execute_and_commit("DELETE FROM `{}`{}".format(table_name, where), values)

    def count(self, table_name, **kwargs):
        where, values = self._where(kwargs)
        return self.cursor.execute("SELECT COUNT(*) FROM `{}`{}".format(table_name, where), values).fetchone()[0]

    def fetch_batches(self, size, *args, **kwargs):
        result = self.execute(*args, **kwargs)
        while True:
            rows = result.fetchmany(size)
            if not rows:
                break
            yield rows

    def fetch_items(self, *args, **kwargs):
        batch_size = kwargs.pop("batch_size", 20)
        for rows in self.fetch_batches(batch_size, *args, **kwargs):
            for row in rows:
                yield row

    def close(self):
        self.cursor.close()
        self.conn.close()

    @staticmethod
    def _where(kwargs):
        keys = tuple(kwargs)
        if keys:
            where = " WHERE " + " AND ".join(["{} = ?".format(k) for k in keys])
            values = tuple(kwargs[k] for k in keys)
        else:
            where = ""
            values = ()
        return where, values

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SearchHistory(object):
    def __init__(self):
        self._storage = Storage(os.path.join(ADDON_DATA, "search_history.sqlite"))
        self._table_name = "search_history"
        self._storage.execute_and_commit(
            "CREATE TABLE IF NOT EXISTS `{}` ("
            "id INTEGER PRIMARY KEY, "
            "last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "type INTEGER NOT NULL, "
            "search TEXT CHECK(search <> '') NOT NULL, "
            "UNIQUE(type, search)"
            ")".format(self._table_name))
        self._page_size = 20

    def get_page(self, search_type, page_number):
        return self._storage.select_page(
            "SELECT id, search FROM `{}` WHERE type = ? ORDER BY last_modified DESC".format(self._table_name),
            self._page_size, page_number, (search_type,)).fetchall()

    def add_entry(self, search_type, search):
        # ON CONFLICT(search) DO UPDATE SET last_modified = CURRENT_TIMESTAMP
        self._storage.execute_and_commit(
            "INSERT INTO `{}` (type, search) VALUES(?, ?);".format(self._table_name), (search_type, search))

    def update_entry(self, search_type, old_search, new_search):
        self._storage.execute_and_commit(
            "UPDATE `{}` SET search = ?, last_modified = CURRENT_TIMESTAMP "
            "WHERE type = ? AND search = ?;".format(self._table_name), (new_search, search_type, old_search))

    def delete_entry_by_id(self, search_id):
        self._storage.delete(self._table_name, id=search_id)

    def delete_entry(self, search_type, search):
        self._storage.delete(self._table_name, type=search_type, search=search)

    def pages_count(self, search_type):
        return self._storage.pages_count(self._table_name, self._page_size, type=search_type)

    def clear_entries(self):
        self._storage.delete(self._table_name)

    def close(self):
        self._storage.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
