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
import logging
from binance import ThreadedWebsocketManager

cwd = os.getcwd()
configfile = open(cwd + "/cfg.json", 'r')
config = json.loads(configfile.read())
configfile.close()
timeframes = config['timeframes']
logging.basicConfig(level=logging.INFO)

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
    print(str(start_datetime) + " - Start check price "+symbol+" tf "+timeframe)

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

            base_price = 1
            gain = 0

            if out:
                if symbol[-3:] in ("ETH", "eth") :
                    searchPrice = True
                    while searchPrice:
                        try:
                            response = requests.get(
                                url="https://api.binance.com/api/v3/depth",
                                params={
                                    "symbol": "ETHUSDT",
                                    "limit": 5
                                },
                                headers={
                                    "Content-Type": "application/json",
                                },
                            )
                            base_price_ask_bid = json.loads(response.content)

                            if len(base_price_ask_bid['bids']) == 0:
                                #print(symbol + " break")
                                time.sleep(1)
                            else:
                                base_price_bid = float(base_price_ask_bid['bids'][0][0])
                                base_price_ask = float(base_price_ask_bid['asks'][0][0])
                                base_price_avg = (base_price_bid + base_price_ask) / 2
                                base_price = base_price_avg
                                searchPrice = False

                        except Exception as e:
                            logging.critical(symbol)
                            logging.critical(response.content)
                            logging.critical(e, exc_info=True)
                elif symbol[-3:] in ("BNB", "bnb"):
                    searchPrice = True
                    while searchPrice:
                        try:
                            response = requests.get(
                                url="https://api.binance.com/api/v3/depth",
                                params={
                                    "symbol": "BNBUSDT",
                                    "limit": 5
                                },
                                headers={
                                    "Content-Type": "application/json",
                                },
                            )
                            base_price_ask_bid = json.loads(response.content)
                            if len(base_price_ask_bid['bids']) == 0:
                                #print(symbol + " break")
                                time.sleep(1)
                            else:
                                base_price_bid = float(base_price_ask_bid['bids'][0][0])
                                base_price_ask = float(base_price_ask_bid['asks'][0][0])
                                base_price_avg = (base_price_bid + base_price_ask) / 2
                                base_price = base_price_avg
                                searchPrice = False

                        except Exception as e:
                            logging.critical(symbol)
                            logging.critical(response.content)
                            logging.critical(e, exc_info=True)
                elif symbol[-3:] in ("BTC", "btc"):
                    searchPrice = True
                    while searchPrice:
                        try:
                            response = requests.get(
                                url="https://api.binance.com/api/v3/depth",
                                params={
                                    "symbol": "BTCUSDT",
                                    "limit": 5
                                },
                                headers={
                                    "Content-Type": "application/json",
                                },
                            )
                            base_price_ask_bid = json.loads(response.content)
                            if len(base_price_ask_bid['bids']) == 0:
                                #print(symbol + " break")
                                time.sleep(1)
                            else:
                                base_price_bid = float(base_price_ask_bid['bids'][0][0])
                                base_price_ask = float(base_price_ask_bid['asks'][0][0])
                                base_price_avg = (base_price_bid + base_price_ask) / 2
                                base_price = base_price_avg
                                searchPrice = False
                        except Exception as e:
                            logging.critical(e, exc_info=True)
                else:
                    base_price = 1

                twm.stop()
                current_time = (datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                file_currency = open(cwd + "/csv/logs.csv", 'a')
                file_currency.write(
                    "{0},{1},{2},{3},{4},{5:.8f},{6},{7},{8},{9:.8f},{10:.8f},{11},{12:.8f},{13:.8f},{14:.8f},{15:.8f},{16:.8f},{17:.8f}\n".format(
                        strategy, str(current_time), str(start_datetime), timeframe, symbol, price, str(c_t), str(c_l), str(c_ct),
                        stop_loss, take_profit, out, gain, base_price, open_price, close_price, high_price, low_price))
                file_currency.close()
                print(str(start_datetime) + " - End check price "+symbol+" tf "+timeframe)

        except Exception as e:
            logging.critical(symbol)
            logging.critical(e, exc_info=True)


    streams = [str(symbol).lower() + '@trade']
    twm.start_multiplex_socket(callback=check_price, streams=streams)
    twm.join()


if __name__ == "__main__":
   #args = {
   #    "symbol": "ethbtc",
   #    "c_t": 3,
   #    "c_l": 0,
   #    "c_ct": 2,
   #    "price": 0.061512,
   #    "stop_loss": 0.061500,
   #    "take_profit": 0.061580,
   #    "timeframe": "15m",
   #    "strategy": "prova",
   #    "open": 1,
   #    "close": 2,
   #    "high": 3,
   #    "low": 0.9
   #}
   #orderbook(args)

    api_key = config['binance_key']
    api_secret = config['binance_secret']
    client = Client(api_key=api_key, api_secret=api_secret)
    order = client.order_market_buy(
        symbol='BTCUSDT',
        quoteOrderQty=11)
    print(order)