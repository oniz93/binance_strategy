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
timeframes = config['timeframes']
workers = list()

def orderbook(args):
    start_datetime = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
    api_key = config['binance_key']
    api_secret = config['binance_secret']
    twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
    twm.start()
    symbol = args['symbol']
    c_t = args['c_t']
    c_l = args['c_l']
    c_ct = args['c_ct']
    price = args['price']
    take_profit = args['take_profit']
    stop_loss = args['stop_loss']
    timeframe = args['timeframe']
    def check_price(trade):
        act_price = float(trade['data']['p'])
        out = False
        if act_price >= take_profit:
            out = 'tp'
        elif act_price <= stop_loss:
            out = 'sl'

        if out:
            twm.stop()
            current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
            file_currency = open(cwd + "/csv/logs.csv", 'a')
            file_currency.write(
                "{0},{1},{2},{3},{4:.8f},{5},{6},{7},{8:.8f},{9:.8f},{10}\n".format(
                str(current_time), str(start_datetime), timeframe, symbol, price, str(c_t), str(c_l), str(c_ct), stop_loss, take_profit, out,))
            file_currency.close()
    streams = [str(symbol).lower()+'@trade']
    asd = twm.start_multiplex_socket(callback=check_price, streams=streams)

    twm.join()

def check_coin(args):
    symbol = args['symbol']
    timeframe = args['timeframe']
    secondsTf = timeframeToSeconds(timeframe)
    print("Start %s %s" % (symbol,timeframe,))
    current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
    print("%s - Get tick %s timeframe %s" % (str(current_time), symbol, timeframe))
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
        if check_tick['open'] < check_tick['close'] and check_tick['low'] > check_tick['EMA_4'] and check_tick['low'] > check_tick['EMA_9'] and check_tick['low'] > check_tick['EMA_40']:
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
            file_currency = open(cwd + "/log/" + symbol + "_" + timeframe + ".log", 'a')
            file_currency.write(
                "Date %s - Price ask: %f - Price bid: %f - Diff: %f\n" % (
                str(current_time), price_ask, price_bid, (price_ask-price_bid),))
            file_currency.close()

            if price < take_profit:
                est_perc = take_profit/price
                args = {
                    "symbol": symbol,
                    "c_t": c_t,
                    "c_l": c_l,
                    "c_ct": c_ct,
                    "price": price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "timeframe": timeframe
                }
                current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                file_currency = open(cwd + "/log/" + symbol + "_" + timeframe + ".log", 'a')
                file_currency.write("Date %s - Price: %f - Take profit: %f - Stop loss: %f - Gain: %f - T = %d - L = %d - CT = %d\n" % (str(current_time), price, take_profit, stop_loss, est_perc,c_t,c_l, c_ct,))
                file_currency.close()
                p = Process(target=orderbook, args=(args,))
                p.start()
                workers.append(p)


def main():
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
        first_start = True
        while True:
            c = 0
            curr_time = int(time.time())
            for timeframe in timeframes:
                if curr_time%timeframeToSeconds(timeframe) == 0 or first_start:
                    for symbol in coins['symbols']:
                        assets = ('ETH', 'BUSD', 'USDT')
                        assets = ('USDT')
                        if symbol['quoteAsset'] in assets:
                            print("Starting %s %s" % (symbol['symbol'], timeframe))
                            arg = {"symbol": symbol['symbol'], "timeframe": timeframe}
                            p = Process(target=check_coin, args=(arg,))
                            p.start()
                            workers.append(p)
                            c = c + 2
                            if c%1100 == 0:
                                time.sleep(60)
            time.sleep(1)


    except KeyboardInterrupt:
        print("control-c")
        for p in workers:
            p.terminate()
            p.join()

if __name__ == "__main__":
   main()
