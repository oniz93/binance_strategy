# import
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
import logging
import math

# create logger with 'spam_application'
logging.basicConfig(filename='logs/error_new.log',level=logging.INFO)

def createLogHeaders(path):
    if not os.path.exists(path):
        file_currency = open(path, 'a')
        file_currency.write(
            '"Strategy","Current Time","Start Time","Timeframe","Symbol","Price","Trend","Lateral","Controtrend","Stop loss","Take profit","Exit","Gain","Base price","Open","Close","High","Low"\n')
        file_currency.close()

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
positions = []

def getCurrentCoinPrice(symbol):
    searchPrice = True
    while searchPrice:
        try:
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
            base_price_ask_bid = json.loads(response.content)
            if len(base_price_ask_bid['bids']) == 0:
                # print(symbol + " break")
                time.sleep(1)
            else:
                base_price_bid = float(base_price_ask_bid['bids'][0][0])
                base_price_ask = float(base_price_ask_bid['asks'][0][0])
                base_price_avg = (base_price_bid + base_price_ask) / 2
                base_price = base_price_avg
                searchPrice = False
                return base_price

        except Exception as e:
            logging.critical(symbol)
            logging.critical(response.content)
            logging.critical(e, exc_info=True)

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
    strategy = args['strategy']
    open_price = args['open']
    close_price = args['close']
    high_price = args['high']
    low_price = args['low']
    quoteAsset = args['quoteAsset']
    quotePrecision = args['quotePrecision']
    assetPrecision = args['assetPrecision']
    assetMin = float(args['assetMin'])

    logging.info("Found " + symbol + " tf " + timeframe)
    print("Found " + symbol + " tf " + timeframe)

    client = Client(api_key=api_key, api_secret=api_secret)
    if quoteAsset == 'BUSD':
        balance = client.get_asset_balance(asset='BUSD')
    else:
        balance = client.get_asset_balance(asset='USDT')

    qty_asset = float(balance['free'])
    if(qty_asset == 0):
        return
    if quoteAsset != 'USDT' and quoteAsset != 'BUSD':

        logging.info("Buying " + quoteAsset + " for trade " + symbol + "precision" + assetPrecision)
        print("Buying " + quoteAsset + " for trade " + symbol + "precision" + assetPrecision)
        assetPrice = float(getCurrentCoinPrice(quoteAsset+'USDT'))
        quotePrice = float(getCurrentCoinPrice(symbol))
        qty_asset = qty_asset * assetPrice
        if quoteAsset != 'BNB':
            qty_buy = ((12 + (qty_asset * (high_price - low_price))) / assetPrice)
            qty_min = ((12 + qty_asset)/assetPrice)
        else:
            qty_buy = ((2 + (qty_asset * (high_price - low_price))) / assetPrice)
            qty_min = ((2 + qty_asset) / assetPrice)
        if qty_asset >= qty_buy:
            buy_qty = qty_buy
        elif qty_asset >= qty_min and qty_asset < qty_buy:
            buy_qty = qty_min
        else:
            buy_qty = 0
        minAsset = assetMin * 1.1
        if buy_qty < minAsset:
            buy_qty = minAsset
        buy_qty = round(buy_qty / assetPrice, assetPrecision)

        logging.info("Making order " + quoteAsset+'USDT' + " qty " + str(buy_qty))
        print("Making order " + quoteAsset+'USDT' + " qty " + str(buy_qty))

        order = client.order_market_buy(
            symbol=quoteAsset+'USDT',
            quantity=buy_qty)

        buy_qty = order['executedQty']


        logging.info("Bought " + quoteAsset + " qty " + str(buy_qty))
        print("Bought " + quoteAsset + " qty " + str(buy_qty))

    else:
        # Calcolo direttamente le quantità se è USDT o BUSD
        assetPrice = 1
        quotePrice = float(getCurrentCoinPrice(symbol))
        qty_buy = ((12 + (assetPrice*(high_price-low_price)))/assetPrice/quotePrice)
        qty_min = ((12 + assetPrice)/assetPrice/ quotePrice)
        if qty_asset >= qty_buy:
            buy_qty = qty_buy
        elif qty_asset >= qty_min and qty_asset < qty_buy:
            buy_qty = qty_min
        else:
            return
    logging.info("Buying " + symbol + " avail " + str(qty_asset) + " qty buy " + str(buy_qty) + "value " + str(
        buy_qty * quotePrice))
    print("Buying " + symbol + " avail " + str(qty_asset) + " qty buy " + str(buy_qty) + "value " + str(
        buy_qty * quotePrice))
    order = client.order_market_buy(
        symbol=symbol,
        quantity=round(buy_qty, quotePrecision))
    exec_qty = float(order['executedQty'])
    logging.info(str(start_datetime) + " - BUY " + symbol + " - QTY: " + str(buy_qty) + " Exec QTY: " + str(exec_qty))
    print(str(start_datetime) + " - BUY " + symbol + " - QTY: " + str(buy_qty) + " Exec QTY: " + str(exec_qty))


    def check_price(trade):
        try:
            act_price = float(trade['data']['p'])
            out = False
            if act_price >= take_profit:
                out = 'tp'
                gain = take_profit - price
            elif act_price <= stop_loss:
                out = 'sl'
                gain = stop_loss - price

            if out:
                twm.stop()
                current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                order = client.order_market_sell(
                    symbol=symbol,
                    quantity=round(exec_qty,quotePrecision))
                logging.info(str(current_time) + " - SELL " + symbol + " - QTY: "+ str(exec_qty) + " Exec QTY: "+ str(order['executedQty']))
                print(str(current_time) + " - SELL " + symbol + " - QTY: "+ str(exec_qty) + " Exec QTY: "+ str(order['executedQty']))

                if quoteAsset not in ('USDT', 'BUSD'):
                    balance = client.get_asset_balance(asset=quoteAsset)
                    balance = balance['free']
                    if quoteAsset == 'BNB':
                        balance = balance - 0.05
                    if balance > 0:
                        order = client.order_market_sell(
                            symbol=quoteAsset + 'USDT',
                            quantity=round(balance, assetPrecision))
                        logging.info(
                            str(current_time) + " - SELL " + quoteAsset + " - QTY: " + str(balance) + " Exec QTY: " + str(
                                order['executedQty']))
                        print(
                            str(current_time) + " - SELL " + quoteAsset + " - QTY: " + str(balance) + " Exec QTY: " + str(
                                order['executedQty']))

        except Exception as e:
            logging.critical(symbol)
            logging.critical(e, exc_info=True)
    streams = [str(symbol).lower() + '@trade']
    twm.start_multiplex_socket(callback=check_price, streams=streams)
    twm.join()


def check_coin(args):
    try:
        symbol = args['symbol']
        timeframe = args['timeframe']
        quoteAsset = args['quoteAsset']
        quotePrecision = args['quotePrecision']
        assetPrecision = args['assetPrecision']
        assetMin = args['assetMin']

        # se risulta aperta gia una posizione per stesso mercato e timeframe ignora i controlli
        if timeframe + "_" + symbol in positions:
            return

        current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
        #print("%s - Get tick %s timeframe %s" % (str(current_time), symbol, timeframe))
        # bars = client.get_historical_klines('BTCUSDT', '4h', timestamp, limit=50)
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
        try:
            df = pd.DataFrame(bars, columns=['date', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume',
                                             'n_trades', 'taker_buy_quote', 'taker_buy_asset', 'ignore'])
            df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].apply(pd.to_numeric)
            df.set_index('date', inplace=True)

            df.ta.ema(close='close', length=4, append=True)
            df.ta.ema(close='close', length=9, append=True)
            df.ta.ema(close='close', length=40, append=True)
            df.ta.ema(close='low', length=40, append=True, suffix='low')
            df.ta.ema(close='high', length=40, append=True, suffix='high')
            df.ta.ema(close=df.ta.ohlc4(ta.ohlc4(df["open"], df["high"], df["low"], df["close"])), length=4, suffix="OHLC4", append=True)
            df.ta.ema(close=df.ta.ohlc4(ta.ohlc4(df["open"], df["high"], df["low"], df["close"])), length=9, suffix="OHLC4", append=True)
            df.ta.ema(close=df.ta.ohlc4(ta.ohlc4(df["open"], df["high"], df["low"], df["close"])), length=40, suffix="OHLC4", append=True)
        except Exception as e:
            logging.critical(symbol)
            logging.critical(e, exc_info=True)
            return

        check_ticks = df[-2:-1]

        c_t = 0
        c_l = 0
        c_ct = 0
        control_ticks = df[-21:-1]
        for index, tick in control_ticks.iterrows():
            if tick['EMA_40_high'] > tick['EMA_9'] and tick['EMA_9'] > tick['EMA_40_low']:
                c_l = c_l + 1
            if tick['EMA_9'] > tick['EMA_40_high']:
                c_t = c_t + 1
            if tick['EMA_9'] < tick['EMA_40_low']:
                c_ct = c_ct + 1

        for index, check_tick in check_ticks.iterrows():
            if check_tick['open'] < check_tick['close'] and check_tick['low'] > check_tick['EMA_4'] and check_tick['low'] > \
                    check_tick['EMA_9'] and check_tick['low'] > check_tick['EMA_40']:
                take_profit = (check_tick['close'] - check_tick['open'] + check_tick['close'])
                stop_loss = check_tick['low'] - (check_tick['high'] - check_tick['low'])*1.2
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
                    #print(symbol + " break")
                    break
                price_bid = float(price_ask_bid['bids'][0][0])
                price_ask = float(price_ask_bid['asks'][0][0])
                price_avg = (price_bid + price_ask) / 2
                price = float(price_avg)
                price = price + price * 0.0001

                current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                file_currency = open(cwd + "/log/" + symbol + "_" + timeframe + ".log", 'a')
                file_currency.write(
                    "Date %s - Price ask: %f - Price bid: %f - Diff: %f\n" % (
                        str(current_time), price_ask, price_bid, (price_ask - price_bid),))
                file_currency.close()
                current_hour = (datetime.utcfromtimestamp(time.time()).strftime('%H'))
                if price < take_profit and price > stop_loss and (
                        (c_t == 8 and c_l == 2 and c_ct == 0) or (
                        c_t == 5 and c_l == 4 and c_ct == 1) or (c_t == 5 and c_l == 5 and c_ct == 0) or (
                                c_t == 3 and c_l == 7 and c_ct == 0) or (
                                c_t == 0 and c_l == 3 and c_ct == 7)) and current_hour != '2' and current_hour != '23':
                    est_perc = take_profit / price
                    multiplier = 1
                    args = {
                        "symbol": symbol,
                        "c_t": c_t,
                        "c_l": c_l,
                        "c_ct": c_ct,
                        "price": price,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit*multiplier,
                        "timeframe": timeframe,
                        "strategy": "ema4-ema9-ema40-tp"+str(multiplier),
                        "open": check_tick['open'],
                        "close": check_tick["close"],
                        "low": check_tick["low"],
                        "high": check_tick["high"],
                        "quoteAsset": quoteAsset,
                        "quotePrecision": quotePrecision,
                        "assetPrecision": assetPrecision,
                        "assetMin": assetMin
                    }
                    current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                    file_currency = open(cwd + "/log/" + symbol + "_" + timeframe + ".log", 'a')
                    file_currency.write(
                        "Date %s - Price: %f - Take profit: %f - Stop loss: %f - Gain: %f - T = %d - L = %d - CT = %d\n" % (
                        str(current_time), price, take_profit, stop_loss, est_perc, c_t, c_l, c_ct,))
                    file_currency.close()
                    positions.append(timeframe + "_" + symbol)
                    p = Process(target=orderbook, args=(args,))
                    p.start()
                    workers.append(p)

    except Exception as e:
        logging.critical(e, exc_info=True)

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
        for symbol in coins['symbols']:
            if symbol['symbol'] == 'BTCUSDT':
                for filt in symbol['filters']:
                    if filt['filterType'] == 'LOT_SIZE':
                        btcusdt_precision = int(round(-math.log(float(filt['stepSize']), 10), 0))
                    if filt['filterType'] == 'MIN_NOTIONAL':
                        btcusdt_minQty = filt['minNotional']
            if symbol['symbol'] == 'ETHUSDT':
                for filt in symbol['filters']:
                    if filt['filterType'] == 'LOT_SIZE':
                        ethusdt_precision = int(round(-math.log(float(filt['stepSize']), 10), 0))
                    if filt['filterType'] == 'MIN_NOTIONAL':
                        ethusdt_minQty = filt['minNotional']
            if symbol['symbol'] == 'BNBUSDT':
                for filt in symbol['filters']:
                    if filt['filterType'] == 'LOT_SIZE':
                        bnbusdt_precision = int(round(-math.log(float(filt['stepSize']), 10), 0))
                    if filt['filterType'] == 'MIN_NOTIONAL':
                        bnbusdt_minQty = filt['minNotional']
        first_start = True
        while True:
            c = 0
            curr_time = int(time.time())
            for timeframe in timeframes:
                current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                if curr_time % timeframeToSeconds(timeframe) == 0 or first_start:
                    print(str(current_time) + " - Start TF: " + timeframe)
                    time.sleep(10)
                    for symbol in coins['symbols']:
                        assets = ('ETH', 'USDT', 'BUSD', 'BTC', 'BNB')
                        for filt in symbol['filters']:
                            if filt['filterType'] == 'LOT_SIZE':
                                precision = int(round(-math.log(float(filt['stepSize']), 10), 0))
                                minQty = filt['minQty']
                        # assets = ('USDT')
                        if symbol['quoteAsset'] in assets:
                            quotename = str(symbol['quoteAsset']).lower()+"usdt"
                            if symbol['quoteAsset'] in ('USDT', 'BUSD'):
                                assetPrecision = 8
                                assetMin = 10
                            else:
                                assetPrecision = locals()[quotename+"_precision"]
                                assetMin = locals()[quotename+"_minQty"]
                            arg = {"symbol": symbol['symbol'], "timeframe": timeframe, "quoteAsset": symbol['quoteAsset'], "quotePrecision": precision, "minQty": minQty, "assetPrecision": assetPrecision, "assetMin": assetMin }
                            p = Process(target=check_coin, args=(arg,))
                            p.start()
                            workers.append(p)
                            c = c + 2
                            if c % 1100 == 0:
                                time.sleep(60)
            first_start = False
            time.sleep(1)


    except KeyboardInterrupt:
        print("control-c")
        for p in workers:
            p.terminate()
            p.join()
    except Exception as e:
        logging.critical(e, exc_info=True)


if __name__ == "__main__":
    logging.info('Start main process')
    main()
