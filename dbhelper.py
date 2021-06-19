import sqlite3


class DBHelper:
    def __init__(self, dbname="data.sqlite"):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname)

    def setup(self):
        stmt = ('''CREATE TABLE IF NOT EXISTS user
       (user_id INT PRIMARY KEY     NOT NULL,
        last_try INT    NULL,
        blacklist  INT     NOT NULL);''')
        self.conn.execute(stmt)
        self.conn.commit()

    def get_user_status(self, user_id):
        stmt = "SELECT blacklist FROM user WHERE user_id == (?)"
        cur = self.conn.cursor()
        cur.execute(stmt, (user_id,))
        result = cur.fetchone()
        if result is None:
            pass
        else:
            return result[0]

    def get_last_try(self, user_id):
        stmt = "SELECT last_try FROM user WHERE user_id == (?)"
        cur = self.conn.cursor()
        cur.execute(stmt, (user_id,))
        result = cur.fetchone()
        if result is None:
            pass
        else:
            return result[0]


    def update_last_try(self, time, user_id):
        stmt = "UPDATE user SET last_try = (?) WHERE user_id == (?)"
        cur = self.conn.cursor()
        args = (time, user_id)
        cur.execute(stmt, args)
        self.conn.commit()

    def new_blacklist(self, user_id):
        stmt = "INSERT OR REPLACE INTO user (user_id, blacklist, last_try) VALUES (?,?,?)"
        args = (user_id, 1, 0)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def new_whitelist(self, user_id):
        stmt = "INSERT OR REPLACE INTO user (user_id, blacklist, last_try) VALUES (?,?,?)"
        args = (user_id, 0, 0)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def blacklist(self, user_id):
        stmt = "UPDATE user SET blacklist = 1 where user_id == (?)"
        args = user_id
        self.conn.execute(stmt, (args,))
        self.conn.commit()

    def whitelist(self, user_id):
        stmt = "UPDATE user SET blacklist = 0 where user_id == (?)"
        args = user_id
        self.conn.execute(stmt, (args,))
        self.conn.commit()
