import binance
import os
import ujson as json
import time
import requests

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
            #assets = ('ETH', 'BUSD', 'USDT')
            assets = ('USDT')
            if symbol['quoteAsset'] in assets:
                print(symbol['symbol'])


    except KeyboardInterrupt:
        print("control-c")
        for p in workers:
            p.terminate()
            p.join()

if __name__ == "__main__":
   main()