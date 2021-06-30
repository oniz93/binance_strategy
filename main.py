# import
import binance
import os
import sys
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
import resource
import psutil
from position import Position

# resolt error too many files open
resource.setrlimit(resource.RLIMIT_NOFILE, (999999, 999999))
logging.basicConfig(filename='logs/error_new.log', level=logging.INFO)

# crea il file con l'header
def createLogHeaders(path):
    if not os.path.exists(path):
        file_currency = open(path, 'a')
        file_currency.write(
            '"Strategy","Current Time","Start Time","Timeframe","Symbol","Price","Trend","Lateral","Controtrend","Stop loss","Take profit","Exit","Gain","Base price","Open","Close","High","Low", "QT", "USD Gain", "Demo"\n')
        file_currency.close()


# converte i TF dei settings in secondi
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
        return False


# legge il config e istanza le varibili globali
cwd = os.getcwd()
configfile = open(cwd + "/cfg.json", 'r')
config = json.loads(configfile.read())
configfile.close()
timeframes = config['timeframes']
workers = list()
positions = list()
take_profit = 0
stop_loss = 0
positionDB = Position()
positionDB.create_table()

# recupera la media tra ask e bid di una moneta
def getCurrentCoinPrice(symbol):
    searchPrice = True
    limit = 10
    c = 0
    while searchPrice and c < 6:
        c += 1
        try:
            response = requests.get(
                url="https://api.binance.com/api/v3/ticker/price?symbol="+symbol,
                headers={
                    "Content-Type": "application/json",
                },
            )
            response = json.loads(response.content)
            if 'price' in response.keys():
                searchPrice = False
                return float(response['price'])
            else:
                time.sleep(0.5)

        except Exception as e:
            pass
            #logging.critical(symbol)
            #logging.critical(e, exc_info=True)
    #logging.critical("No trades found for symbol %s " % (symbol,))
    exit("KILL Process - No trades found for symbol %s " % (symbol,))

def getCoinVolume(symbol):
    searchPrice = True
    limit = 10
    c = 0
    while searchPrice and c < 6:
        c += 1
        try:
            response = requests.get(
                url="https://api.binance.com/api/v3/ticker/24hr?symbol="+symbol,
                headers={
                    "Content-Type": "application/json",
                },
            )
            response = json.loads(response.content)
            if 'quoteVolume' in response.keys():
                searchPrice = False
                return float(response['quoteVolume'])
            else:
                time.sleep(0.5)

        except Exception as e:
            pass
            #logging.critical(symbol)
            #logging.critical(e, exc_info=True)
    #logging.critical("No trades found for symbol %s " % (symbol,))
    exit("KILL Process - No volume found for symbol %s " % (symbol,))

# crea l'ordine e monitora il prezzo per vendere
def orderbook(args):
    try:
        global take_profit
        global stop_loss
        global positions
        # recupero di tutti i parametri
        start_datetime = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
        api_key = config['binance_key']
        api_secret = config['binance_secret']
        symbol = args['symbol']
        c_t = args['c_t']
        c_l = args['c_l']
        c_ct = args['c_ct']
        price = float(args['price'])
        take_profit = float(args['take_profit'])
        stop_loss = float(args['stop_loss'])
        timeframe = args['timeframe']
        strategy = args['strategy']
        open_price = float(args['open'])
        close_price = float(args['close'])
        high_price = float(args['high'])
        low_price = float(args['low'])
        quote_asset = args['quote_asset']
        quote_precision = args['quote_precision']
        min_qty = float(args['min_qty'])
        pid = False
        exec_qty = False
        if 'exec_qty' in args:
            exec_qty = args['exec_qty']
        if 'pid' in args:
            pid = args['pid']

        current_pid = os.getpid()

        logging.info("Found " + symbol + " tf " + timeframe)
        print("Found " + symbol + " tf " + timeframe)
        if exec_qty == False:
            current_price = getCurrentCoinPrice(symbol)
            if current_price > take_profit:
                print("STOP " + symbol + " tf " + timeframe + ": price already too high")
                logging.info("STOP " + symbol + " tf " + timeframe + ": price already too high")
                exit("STOP " + symbol + " tf " + timeframe + ": price already too high")

            delta = price / current_price * 10

            if 90 <= delta or delta >= 110:
                print("STOP " + symbol + " tf " + timeframe + ": price changed too much")
                logging.info("STOP " + symbol + " tf " + timeframe + ": price changed too much")
                exit("STOP " + symbol + " tf " + timeframe + ": price changed too much")

            percent_tp = take_profit / current_price * 100
            if percent_tp <= 101:
                print("STOP " + symbol + " tf " + timeframe + ": not enough margin")
                logging.info("STOP " + symbol + " tf " + timeframe + ": not enough margin")
                exit("STOP " + symbol + " tf " + timeframe + ": not enough margin")

            volume = getCoinVolume(symbol)
            normalized_volume = ((volume - 45000)/(900000000-45000))*100
            if normalized_volume > 100:
                normalized_volume = 100

            client = Client(api_key=api_key, api_secret=api_secret)
            balance = client.get_asset_balance(asset=quote_asset)
            qty_asset = float(balance['free'])
            logging.info("Quote asset: " + quote_asset + " Balance: " + str(qty_asset))

            # quando non ci sono abbastanza soldi per la quantità minima della coppia
            if qty_asset < min_qty:
                print("Buying " + symbol + " tf " + timeframe + ": not enough wallet")
                logging.info("Buying " + symbol + " tf " + timeframe + ": not enough wallet")
                exit("Buying " + symbol + " tf " + timeframe + ": not enough wallet")

            # calcolo della quantità di acquisto, al massimo acquista un totale di balance X perc rischio
            max_buy_qty = min_qty + ((qty_asset - min_qty) * float(config['perc_rischio'])/100)
            max_buy_cap = qty_asset * float(config['max_cap']) / 100
            #buy_qty = min_qty + (((qty_asset - min_qty) * float(config['perc_rischio']) / 100) / ((close_price - open_price) * 100) / price * 100) * 10
            buy_qty = min_qty + (((qty_asset - min_qty) * float(config['perc_rischio'])/100) * ((close_price - open_price) / price) * 10)
            buy_qty = min_qty + ((buy_qty-min_qty) * normalized_volume)
            if buy_qty > max_buy_cap:
                buy_qty = max_buy_cap
            if min_qty > buy_qty:
                buy_qty = min_qty*1.05

            logging.info("Buying " + symbol + " avail " + str(qty_asset) + " qty buy " + str(buy_qty) + " value " + str(buy_qty * price))
            print("Buying " + symbol + " avail " + str(qty_asset) + " qty buy " + str(buy_qty) + " value " + str(buy_qty * price))
            if not config['demo']:
                order = client.order_market_buy(symbol=symbol, quoteOrderQty=round(buy_qty, quote_precision))
                exec_qty = float(order['executedQty'])
                price = float(order['fills'][0]['price'])
                positions.append(timeframe + "_" + symbol)
            else:
                #order = client.create_test_order( symbol=symbol, side='BUY', type='MARKET', quoteOrderQty=round(buy_qty, quote_precision))
                exec_qty = buy_qty/current_price
                positions.append(timeframe + "_" + symbol)
            args['exec_qty'] = exec_qty
            positionDB.open(order_detail=args, symbol=symbol, timeframe=timeframe, pid=current_pid)

            logging.info(str(start_datetime) + " - BUY " + symbol + " - QTY: " + str(exec_qty) + " Exec QTY: " + str(exec_qty))
            print(str(start_datetime) + " - BUY " + symbol + " - QTY: " + str(exec_qty) + " Exec QTY: " + str(exec_qty))
        else:

            client = Client(api_key=api_key, api_secret=api_secret)
            logging.info(str(start_datetime) + " - RESTART " + symbol + " - QTY: " + str(exec_qty) + " Exec QTY: " + str(exec_qty))
            print(str(start_datetime) + " - RESTART " + symbol + " - QTY: " + str(exec_qty) + " Exec QTY: " + str(exec_qty))
            positionDB.updatePid(str(pid), str(current_pid))


    except Exception as e:
        logging.critical(e, exc_info=True)
        return

    # twm process variable
    twm = ThreadedWebsocketManager()
    time_start_ws = int(time.time())
    ws_error = False

    # callback ws
    def check_price(trade):
        global take_profit
        global stop_loss
        global positions
        try:
            ws_error = trade['e']
        except Exception as e:
            ws_error = 'error'

        if time_start_ws % (60 * 60 * 2) == 0 or ws_error == 'error' or trade['e'] == 'error':
            twm_start = False
            tentative = 0
            while not twm_start or tentative < 20:
                try:
                    twm.stop()
                    twm.start()
                    twm.start_trade_socket(callback=check_price, symbol=symbol)
                    twm_start = True
                    logging.info("START WS " + timeframe + " - " + symbol)
                except Exception as e:
                    time.sleep(2)
                    tentative += 1
                    twm_start = False
                    logging.critical(e, exc_info=True)
            if tentative >= 20:
                # chiude l'ordine
                if not config['demo']:
                    current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                    order = client.order_market_sell(symbol=symbol, quantity=round(exec_qty, quote_precision))
                    logging.info(str(current_time) + " - SELL " + symbol + " - QTY: " + str(exec_qty) + " Exec QTY: " + str(order['executedQty']))
                    print(str(current_time) + " - SELL " + symbol + " - QTY: " + str(exec_qty) + " Exec QTY: " + str(order['executedQty']))
                positions.remove(timeframe + "_" + symbol)
                positionDB.closePid(current_pid)
                exit("ERROR WS AUTO SELL")

        else:
            try:
                # calcolo del gain e valuta se uscire
                act_price = float(trade['p'])
                out = False
                if act_price >= take_profit:
                    out = 'tp'
                elif act_price <= stop_loss:
                    out = 'sl'

                if out:
                    current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                    try:
                        logging.info(str(current_time) + " - SELLING " + symbol + " - QTY: " + str(exec_qty))
                        print(str(current_time) + " - SELLING " + symbol + " - QTY: " + str(exec_qty))

                        if not config['demo']:
                            # setta l'ordine di vendita
                            order = client.order_market_sell(symbol=symbol,quantity=round(exec_qty, quote_precision))
                            executedQty = order['executedQty']
                            if out == 'tp':
                                take_profit = float(order['fills'][0]['price'])
                                gain = take_profit - price
                            else:
                                stop_loss = float(order['fills'][0]['price'])
                                gain = stop_loss - price
                        else:
                            #order = client.create_test_order(symbol=symbol,quantity=round(exec_qty, quote_precision), side="SELL", type="MARKET")
                            executedQty = exec_qty
                            if out == 'tp':
                                gain = take_profit - price
                            else:
                                gain = stop_loss - price
                        if timeframe + "_" + symbol in positions:
                            positions.remove(timeframe + "_" + symbol)
                        current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                        logging.info(str(current_time) + " - SELL " + symbol + " - QTY: " + str(exec_qty) + " Exec QTY: " + str(executedQty))
                        print(str(current_time) + " - SELL " + symbol + " - QTY: " + str(exec_qty) + " Exec QTY: " + str(executedQty))
                        positionDB.closePid(current_pid)
                        # calcoli per file csv
                        base_price = 1
                        usdt_gain = gain * exec_qty
                        log_path = cwd + "/csv/" + strategy + ".csv"
                        createLogHeaders(log_path)
                        file_currency = open(log_path, 'a')
                        file_currency.write(
                            "{0},{1},{2},{3},{4},{5:.8f},{6},{7},{8},{9:.8f},{10:.8f},{11},{12:.8f},{13:.8f},{14:.8f},{15:.8f},{16:.8f},{17:.8f},{18:.8f},{19:.8f}\n".format(strategy, str(current_time), str(start_datetime), timeframe, symbol, price, str(c_t), str(c_l), str(c_ct), stop_loss, take_profit, out, gain, base_price, open_price, close_price, high_price, low_price, exec_qty, usdt_gain, str(config['demo'])))
                        file_currency.close()
                        twm.stop()
                        exit()
                    except Exception as e:
                        logging.critical(e, exc_info=True)

            except Exception as e:
                logging.critical(symbol)
                logging.critical(e, exc_info=True)

    twm.start()
    twm.start_trade_socket(callback=check_price, symbol=symbol)

def check_coin(args):
    try:
        symbol = args['symbol']
        timeframe = args['timeframe']
        quote_asset = args['quote_asset']
        quote_precision = args['quote_precision']
        min_qty = args['minQty']

        # se risulta aperta gia una posizione per stesso mercato e timeframe ignora i controlli
        if timeframe + "_" + symbol in positions:
            return True

        # recupera le candele
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
            df = pd.DataFrame(bars,columns=['date', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'n_trades', 'taker_buy_quote', 'taker_buy_asset', 'ignore'])
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
            #logging.critical(symbol + "not enough candles")
            return True

        check_ticks = df[-2:-1]
        c_t = 0
        c_l = 0
        c_ct = 0
        control_ticks = df[-21:-1]
        for index, tick in control_ticks.iterrows():
            if tick['EMA_40_high'] > tick['EMA_9_OHLC4'] and tick['EMA_9_OHLC4'] > tick['EMA_40_low']:
                c_l = c_l + 1
            if tick['EMA_9_OHLC4'] > tick['EMA_40_high']:
                c_t = c_t + 1
            if tick['EMA_9_OHLC4'] < tick['EMA_40_low']:
                c_ct = c_ct + 1

        for index, check_tick in check_ticks.iterrows():
            if (check_tick['open'] < check_tick['close'] and check_tick['low'] > check_tick['EMA_4_OHLC4'] and check_tick['low'] > check_tick['EMA_9_OHLC4'] and check_tick['low'] > check_tick['EMA_40_OHLC4']):
                take_profit = (check_tick['close'] - check_tick['open'] + check_tick['close'])
                stop_loss = check_tick['low'] - (check_tick['high'] - check_tick['low'])
                price = getCurrentCoinPrice(symbol)
                current_hour = (datetime.utcfromtimestamp(time.time()).strftime('%H'))
                perc_price = (check_tick['close'] - check_tick['open']) * 100 / price

                if (price < take_profit and price > stop_loss and perc_price >= 0.9 and ((c_t == 8 and c_l == 2 and c_ct == 0) or (c_t == 5 and c_l == 4 and c_ct == 1) or (c_t == 5 and c_l == 5 and c_ct == 0) or (c_t == 3 and c_l == 7 and c_ct == 0) or (c_t == 0 and c_l == 3 and c_ct == 7)) and current_hour != '2' and current_hour != '23'):
                    multiplier = 1
                    args = {
                        "symbol": symbol,
                        "c_t": c_t,
                        "c_l": c_l,
                        "c_ct": c_ct,
                        "price": price,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit * multiplier,
                        "timeframe": timeframe,
                        "strategy": "ema4-ema9-ema40-tp" + str(multiplier),
                        "open": check_tick['open'],
                        "close": check_tick["close"],
                        "low": check_tick["low"],
                        "high": check_tick["high"],
                        "quote_asset": quote_asset,
                        "quote_precision": quote_precision,
                        "min_qty": min_qty
                    }
                    print("Apro posizione " + symbol + " TF " + timeframe)
                    # richiama orderbok per gestire la posizione
                    orderbook(args)

    except Exception as e:
        logging.critical(e, exc_info=True)

# avvia i watcher per ogni mercato
def check_markets(markets):
    c = 0
    for market in markets:
        p = Process(target=check_coin, args=(market,))
        p.start()
        workers.append(p)
        c += 2
        if c % 900 == 0:
            print("SLEEP CHECK MARKETS")
            time.sleep(60)
        if c >= 14000:
            print("IGNORE MARKETS")
            return
    print("CHECK ALL MARKETS")

def main():
    print("START MAIN PROCESS")
    logging.info('START MAIN PROCESS')
    try:
        response = requests.get(
            url="https://api.binance.com/api/v3/exchangeInfo",
            params={},
            headers={"Content-Type": "application/json"}
        )
        coins = json.loads(response.content)
        forceStart = config['force_start']
        while True:
            c = 0
            curr_time = int(time.time())
            candidate_markets = list()
            candidate_timeframes = list()
            for timeframe in timeframes:
                current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                if curr_time % timeframeToSeconds(timeframe) == 0 or forceStart:
                    print(timeframe)
                    candidate_timeframes.append(timeframe)

            for timeframe in candidate_timeframes:
                print(str(current_time) + " - START TF: " + timeframe)
                for symbol in coins['symbols']:
                    assets = config['assets']
                    for filt in symbol['filters']:
                        if filt['filterType'] == 'LOT_SIZE':
                            precision = int(round(-math.log(float(filt['stepSize']), 10), 0))
                            minQty2 = filt['minQty']
                        if filt['filterType'] == 'MIN_NOTIONAL':
                            minQty = filt['minNotional']
                    if minQty2 > minQty:
                        minQty = minQty2
                    if symbol['quoteAsset'] in assets and 'SPOT' in symbol['permissions']:
                        arg = {"symbol": symbol['symbol'], "timeframe": timeframe, "quote_asset": symbol['quoteAsset'], "quote_precision": precision, "minQty": minQty}
                        candidate_markets.append(arg)
            forceStart = False

            # avvia un processo che avvia i processi!!
            if len(candidate_markets) > 0:
                p = Process(target=check_markets, args=(candidate_markets,))
                p.start()
                workers.append(p)
            time.sleep(1)

    except KeyboardInterrupt:
        print("STOP PROCESS")
        for p in workers:
            try:
                p.terminate()
                p.join()
            except Exception as e:
                pass

    except Exception as e:
        logging.critical(e, exc_info=True)

def check_pid_and_restart():
    while True:
        pids = psutil.pids()
        DB = Position()
        orders = DB.getAllPending()
        for order in orders:
            if int(order['PID']) not in pids:
                args = json.loads(order['orderDetail'])
                args['pid'] = order['PID']
                p = Process(target=orderbook, args=(args,))
                p.start()
        time.sleep(30)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'watcher':
            check_pid_and_restart()
    else:
        main()