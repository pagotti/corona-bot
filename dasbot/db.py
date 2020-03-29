"""
Postgres Driver External Dependencies:
- psycopg2: (c) Federico Di Gregorio, Daniele Varrazzo, Jason Erickson - LGPL License (https://github.com/psycopg/psycopg2)

"""

import os
import psycopg2 as postgres
import psycopg2.extras as postres_extras


class PostgreBatchCursor:
    """Proxy that bypass executemany and run execute_batch on psycopg2 """

    def __init__(self, cursor):
        self._cursor = cursor

    def executemany(self, statement, parameters, **kwargs):
        return postres_extras.execute_batch(self._cursor, statement, parameters, **kwargs)

    def __getattr__(self, item):
        return getattr(self._cursor, item)


class PostgreSQLDriver(object):
    """Driver for PostgreSQL connections"""

    def __init__(self, config):
        self.config = config

    def get_db(self):
        conn = self.config
        db = postgres.connect(conn["url"])

        if "initializing" in conn:
            for sql in conn["initializing"]:
                db.cursor().execute(sql)
        return db

    def cursor(self, db):
        return PostgreBatchCursor(db.cursor())


_connection = {"url": os.environ.get("POSTGRESQL_URL")}


def _get_connection():
    conn = PostgreSQLDriver(_connection)
    db = conn.get_db()
    cur = conn.cursor(db)
    return db, cur


class BaseRepo(object):
    def __init__(self):
        self._rows = []
        self._fields = []
        self._map = {}
        self._table = ""

    def field_list(self):
        fields = [f for f in self._fields if f in self._map]
        return ", ".join(fields)

    def props_list(self):
        props = ["%({})s".format(self._map.get(f)) for f in self._fields if f in self._map]
        return ", ".join(props)

    @property
    def rows(self):
        return self._rows

    def add(self, row):
        self._rows.append(row)

    def insert_sql(self):
        return "INSERT INTO {} ({}) VALUES ({});".format(self._table, self.field_list(), self.props_list())

    def select_sql(self, where="1=1"):
        return "SELECT {} FROM {} WHERE {};".format(self.field_list(), self._table, where)

    def delete_sql(self, where):
        return "DELETE FROM {} WHERE {};".format(self._table, where)

    def insert(self, delete_clause=None):
        db, cur = _get_connection()
        if delete_clause:
            cur.execute(delete_clause)
        if self._rows:
            cur.executemany(self.insert_sql(), self._rows)
        db.commit()
        db.close()

    def load(self, where="1=1"):
        self._rows.clear()
        db, cur = _get_connection()
        cur.execute(self.select_sql(where))
        for row in cur.fetchall():
            data = dict()
            for i, field in enumerate(self._fields):
                data[self._map.get(field)] = row[i]
            self._rows.append(data)
        db.close()


class JobCacheRepo(BaseRepo):
    def __init__(self):
        super().__init__()
        self._table = "public.jobcache"
        self._fields = ["job_id", "interval", "repeat", "region", "chat_id",
                        "only_new", "last_cases", "last_deaths", "last_recovery"]
        self._map = {
            "job_id": "job_id",
            "interval": "interval",
            "repeat": "repeat",
            "region": "region",
            "chat_id": "chat_id",
            "only_new": "new",
            "last_cases": "cases",
            "last_deaths": "deaths",
            "last_recovery": "recovery"
        }

    def save(self):
        self.insert(self.delete_sql("1=1"))


class BotLogRepo(BaseRepo):
    def __init__(self):
        super().__init__()
        self._table = "public.botlog"
        self._fields = ["chat_id", "user_name", "command", "args"]
        self._map = {
            "chat_id": "chat_id",
            "user_name": "username",
            "command": "command",
            "args": "args"
        }

    def save(self):
        self.insert()


class CasesRepo(BaseRepo):
    def __init__(self):
        super().__init__()
        self._table = "public.cases"
        self._fields = ["data_source", "region", "cases", "deaths", "recovery", "source_date"]
        self._map = {
            "data_source": "source",
            "region": "region",
            "cases": "cases",
            "deaths": "deaths",
            "recovery": "recovery",
            "source_date": "date"
        }

    def save(self):
        self.insert()
