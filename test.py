import binance
import os
import ujson as json
from binance import Client
import pandas as pd
import pandas_ta as ta
import asyncio
import time
import requests
from datetime import datetime
from multiprocessing import Process
import random
import time

from binance import ThreadedWebsocketManager

cwd = os.getcwd()
configfile = open(cwd + "/cfg.json", 'r')
config = json.loads(configfile.read())
configfile.close()
timeframes = config['timeframes']

def orderbook(args):
    api_key = config['binance_key']
    api_secret = config['binance_secret']
    twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
    twm.start()
    symbol = args['symbol']
    c_t = args['c_t']
    c_l = args['c_l']
    c_cl = args['c_cl']
    price = args['price']
    take_profit = args['take_profit']
    stop_loss = args['stop_loss']
    def check_price(trade):

        print(trade['data']['p'])
        act_price = float(trade['data']['p'])
        out = False
        if act_price >= take_profit:
            out = 'tp'
        elif act_price <= stop_loss:
            out = 'sl'

        if out:
            twm.stop()
            current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
            file_currency = open(cwd + "/csv/logs.log", 'a')
            file_currency.write(
                "%s,%s,%f,%f,%f,%f,%f,%f,%s\n" % (
                str(current_time), symbol, price, c_t, c_l, c_cl, stop_loss, take_profit, out,))
            file_currency.close()
    print("Start stream "+symbol)
    streams = [str(symbol).lower()+'@trade']
    asd = twm.start_multiplex_socket(callback=check_price, streams=streams)

    twm.join()


if __name__ == "__main__":
   args = {
       "symbol": "shibusdt",
       "c_t": 3,
       "c_l": 0,
       "c_cl": 2,
       "price": 0.00000609,
       "stop_loss": 0.00000607,
       "take_profit": 0.00000610,
   }
   orderbook(args)
