import sqlite3
import ujson as json
import os

class Position:

    def __init__(self):
        cwd = os.getcwd()
        self.filename = cwd+"/positions.db"

    def create_table(self):
        con = sqlite3.connect(self.filename)
        con.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
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

    def open(self, order_detail, timeframe, symbol, pid):
        con = sqlite3.connect(self.filename)
        con.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = con.cursor()
        cur.execute("insert into positions (orderDetail, Timeframe, Symbol, Status, PID) values ('" + json.dumps(order_detail) + "', '" + timeframe + "', '" + symbol + "', 'PENDING', '"+str(pid)+"')")
        con.commit()
        con.close()

        return cur.lastrowid

    def close(self, rowid):
        con = sqlite3.connect(self.filename)
        con.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = con.cursor()
        cur.execute("update positions set Status = 'FILLED' WHERE id = "+str(rowid))
        con.commit()

    def closePid(self, pid):
        con = sqlite3.connect(self.filename)
        con.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = con.cursor()
        cur.execute("update positions set Status = 'FILLED' WHERE PID = "+str(pid))
        con.commit()

    def getAllPending(self):
        con = sqlite3.connect(self.filename)
        con.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = con.cursor()
        cur.execute("SELECT * FROM positions WHERE Status='PENDING'")
        rows = cur.fetchall()
        return rows

    def updatePid(self, oldPid, newPid):
        con = sqlite3.connect(self.filename)
        con.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = con.cursor()
        cur.execute("update positions set PID = '"+str(newPid)+"' WHERE PID = '"+str(oldPid)+"'")
        con.commit()