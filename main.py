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
# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.
import time

from binance import ThreadedWebsocketManager

def timeframeToSeconds(tf):
    if tf == '1m':
        return 60
    elif tf == '3m':
        return 60 * 3
    elif tf == '5m':
        return 60 * 5
    elif tf == '15m':
        return 60 * 15
    elif tf == '30m':
        return 60 * 30
    elif tf == '1h':
        return 60 * 60
    elif tf == '2h':
        return 60 * 60 * 2
    elif tf == '4h':
        return 60 * 60 * 4
    elif tf == '6h':
        return 60 * 60 * 6
    elif tf == '8h':
        return 60 * 60 * 8
    elif tf == '12h':
        return 60 * 60 * 12
    elif tf == '1d':
        return 60 * 60 * 24
    elif tf == '3d':
        return 60 * 60 * 24 * 3
    elif tf == '1w':
        return 60 * 60 * 24 * 7
    else:
        return 60 * 60


cwd = os.getcwd()
configfile = open(cwd + "/cfg.json", 'r')
config = json.loads(configfile.read())
configfile.close()
api_key = config['binance_key']
api_secret = config['binance_secret']
client = Client(api_key, api_secret)
timeframes = config['timeframes']

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

def check_coin(args):
    symbol = args['symbol']
    timeframe = args['timeframe']
    secondsTf = timeframeToSeconds(timeframe)
    print("Start %s %s" % (symbol,timeframe,))
    while True:
        #bars = client.get_historical_klines('BTCUSDT', '4h', timestamp, limit=50)
        response = requests.get(
            url="https://api.binance.com/api/v3/klines",
            params={
                "symbol": symbol,
                "interval": timeframe,
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

        last_ticks = df[-1:-1]
        wait_next = time.time()+secondsTf
        for tick in last_ticks.iterrows():
            timestamp = float(tick['date'])/1000
            wait_next = timestamp + secondsTf

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
            if check_tick['open'] < check_tick['close'] and check_tick['low'] > check_tick['EMA_4'] and check_tick['low'] > check_tick['EMA_9'] and check_tick['low'] > check_tick['EMA_40'] and c_t > 5:
                take_profit = check_tick['close']-check_tick['open']+check_tick['close']
                stop_loss = check_tick['low'] - (check_tick['high']-check_tick['low'])
                response = requests.get(
                    url="https://api.binance.com/api/v3/depth",
                    params={
                        "symbol": symbol,
                        "limit": 5
                    },
                    headers={
                        "Content-Type": "application/json",
                    },
                )
                price_ask_bid = json.loads(response.content)
                if len(price_ask_bid['bids']) == 0:
                    print(symbol + " break")
                    break
                price_bid = float(price_ask_bid['bids'][0][0])
                price_ask = float(price_ask_bid['asks'][0][0])
                price_avg = (price_bid+price_ask)/2
                price = float(price_avg)
                price = price + price*0.0001

                current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                file_currency = open(cwd + "/" + symbol + "_" + timeframe + ".log", 'a')
                file_currency.write(
                    "Date %s - Price ask: %f - Price bid: %f - Diff: %f\n" % (
                    str(current_time), price_ask, price_bid, (price_ask-price_bid),))
                file_currency.close()

                if price < take_profit:
                    est_perc = take_profit/price
                    current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                    file_currency = open(cwd + "/" + symbol + "_" + timeframe + ".log", 'a')
                    file_currency.write("Date %s - Price: %f - Take profit: %f - Stop loss: %f - Gain: %f - T = %d - L = %d - CT = %d\n" % (str(current_time), price, take_profit, stop_loss, est_perc,c_t,c_l, c_ct,))
                    file_currency.close()

        while time.time() < wait_next:
            time.sleep(1)

def main():
    workers = list()
    try:
        response = requests.get(
            url="https://api.binance.com/api/v3/exchangeInfo",
            params={
            },
            headers={
                "Content-Type": "application/json",
            },
        )
        coins = json.loads(response.content)
        for symbol in coins['symbols']:
            if symbol['quoteAsset'] == 'USDT':
                for timeframe in timeframes:
                    arg = {"symbol": symbol['symbol'], "timeframe": timeframe}
                    p = Process(target=check_coin, args=(arg,))
                    p.start()
                    workers.append(p)
                    time.sleep(0.001)
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("control-c")
        for p in workers:
            p.terminate()
            p.join()

if __name__ == "__main__":
   main()
