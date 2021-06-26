import sqlite3
import ujson as json


class Position:

    def __init__(self):
        pass

    def create_table(self):
        con = sqlite3.connect('positions.db')
        cur = con.cursor()
        # Create table
        cur.execute('''CREATE TABLE IF NOT EXISTS positions (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         orderDetail TEXT,
                         Timeframe TEXT,
                         Symbol TEXT,
                         Status TEXT,
                         PID TEXT)''')
        # cur.execute('''CREATE TABLE IF NOT EXISTS positions (
        #                     id INTEGER PRIMARY KEY AUTOINCREMENT,
        #                     Type TEXT,
        #                     Strategy TEXT,
        #                     CurrentTime TEXT,
        #                     StartTime TEXT,
        #                     Timeframe TEXT,
        #                     Symbol TEXT,
        #                     Price REAL,
        #                     Trend NUMERIC,
        #                     Lateral NUMERIC,
        #                     Controtrend NUMERIC,
        #                     Stoploss REAL,
        #                     Takeprofit REAL,
        #                     Exit TEXT,
        #                     Gain REAL,
        #                     Baseprice REAL,
        #                     Open REAL,
        #                     Close REAL,
        #                     High REAL,
        #                     Low REAL,
        #                     QT REAL,
        #                     USDGain REAL,
        #                     Demo TEXT,
        #                     PID TEXT)''')
        con.commit()
        con.close()

    def open(self, order_detail, timeframe, symbol):
        con = sqlite3.connect('positions.db')
        cur = con.cursor()
        cur.execute("insert into positions (orderDetail, Timeframe, Symbol, Status) values ('" + json.dumps(order_detail) + "', '" + timeframe + "', '" + symbol + "', 'PENDING')")
        con.commit()
        con.close()