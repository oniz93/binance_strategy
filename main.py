import binance
import os
import ujson as json
from binance import Client
import pandas as pd
import pandas_ta as ta
import asyncio
import time
import requests
# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.
import time

from binance import ThreadedWebsocketManager

cwd = os.getcwd()
configfile = open(cwd + "/cfg.json", 'r')
config = json.loads(configfile.read())
configfile.close()
api_key = config['binance_key']
api_secret = config['binance_secret']

def signToTick():
    try:
        symbol = 'BNBBTC'

        twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
        # start is required to initialise its internal loop
        twm.start()

        def handle_socket_message(msg):
            print(msg)

        streams = ['btcusdt@kline_1m']
        twm.start_multiplex_socket(callback=handle_socket_message, streams=streams)

        twm.join()
    except KeyboardInterrupt:
        print("control-c")
        twm.stop()

def main():
    client = Client(api_key, api_secret)
    timestamp = client._get_earliest_valid_timestamp('BTCUSDT', '4h')
    #bars = client.get_historical_klines('BTCUSDT', '4h', timestamp, limit=50)
    response = requests.get(
        url="https://api.binance.com/api/v3/klines",
        params={
            "symbol": "BTCUSDT",
            "interval": "4h",
            "limit": "50",
        },
        headers={
            "Content-Type": "application/json",
        },
    )
    bars = json.loads(response.content)
    df = pd.DataFrame(bars, columns=['date', 'open', 'high', 'low', 'close','volume','close_time','quote_volume','n_trades','taker_buy_quote','taker_buy_asset','ignore'])
    df[['open','high','low','close']] = df[['open','high','low','close']].apply(pd.to_numeric)
    df.set_index('date', inplace=True)

    df.ta.ema(close='close', length=4, append=True)
    df.ta.ema(close='close', length=9, append=True)
    df.ta.ema(close='close', length=40, append=True)
    df.ta.ema(close='low', length=40, append=True, suffix='low')
    df.ta.ema(close='high', length=40, append=True, suffix='high')

    check_ticks = df[-2:-1]
    c_t = 0
    c_l = 0
    c_ct = 0
    control_ticks = df[-21:-1]
    for index, tick in control_ticks.iterrows():
        if tick['EMA_40_high'] > tick['EMA_9'] and tick['EMA_9'] > tick['EMA_40_low']:
            c_l = c_l +1
        if tick['EMA_9'] > tick['EMA_40_high']:
            c_t = c_t +1
        if tick['EMA_9'] < tick['EMA_40_low']:
            c_ct = c_ct +1

    for index, check_tick in check_ticks.iterrows():
        if check_tick['low'] < check_tick['EMA_4'] and check_tick['low'] < check_tick['EMA_9'] and check_tick['low'] < check_tick['EMA_40']:
            print("trovato")

    print("T = %d - L = %d - CT = %d" % (c_t,c_l, c_ct))

if __name__ == "__main__":
   main()
