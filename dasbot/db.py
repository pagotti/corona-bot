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
