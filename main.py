import binance
import os
import ujson as json
from binance import Client
import modin.pandas as pd
import asyncio
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
    timestamp = client._get_earliest_valid_timestamp('BTCUSDT', '1d')
    bars = client.get_historical_klines('BTCUSDT', '1d', timestamp, limit=50)
    btc_df = pd.DataFrame(bars, columns=['date', 'open', 'high', 'low', 'close'])
    btc_df.set_index('date', inplace=True)
    print(btc_df.head())

if __name__ == "__main__":
   main()
