import datetime as dt
import sqlite3 as sql


class DB:
    def __init__(self, name):
        self.name = name
        with sql.connect(self.name) as self.conn:
            self.cursor = self.conn.cursor()

    def create_table(self, text):
        self.cursor.execute('''DROP TABLE IF EXISTS breads''')
        self.cursor.execute('''CREATE TABLE breads (
                            name TEXT NOT NULL
                            )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS results (
                            user_id INTEGER NOT NULL,
                            get_points INTEGER NOT NULL,
                            all_points INTEGER NOT NULL,
                            datetime DATETIME NOT NULL
                            )''')
        self.conn.commit()
        self.write_all_breads(text)

    def write_all_breads(self, text):
        self.cursor.executemany(f'INSERT INTO breads (name) VALUES (?)', text)
        self.conn.commit()

    def get_breads(self, k):
        self.cursor.execute('''SELECT * FROM breads
                            ORDER BY RANDOM()
                            LIMIT ?''', (k,))
        return list(map(lambda x: x[0], self.cursor.fetchall()))

    def write_result(self, user_id, get_points, all_points):
        self.cursor.execute('INSERT INTO results VALUES (?, ?, ?, ?)',
                            (user_id, get_points, all_points, dt.datetime.now()))
        self.conn.commit()

    def get_results(self, user_id, all):
        self.cursor.execute(f'''SELECT get_points, all_points, datetime FROM results
                            WHERE user_id = {user_id}
                            ORDER BY datetime DESC
                            {'LIMIT 3' if not all else ''}''')
        return self.cursor.fetchall()
