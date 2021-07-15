from exchangeInterface import ExchangeInterface
from binance import Client
from binance import ThreadedWebsocketManager
import ujson as json
import requests
class BinanceInterface(ExchangeInterface):
    api_key = ""
    api_secret = ""
    api_limit_requests_per_min = 0
    client = None
    api_endpoint = "https://api.binance.com/"

    def __init__(self, api_key, api_secret, api_limit_requests_per_min):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_limit_requests_per_min

    def initializeClient(self):
        self.client = Client(api_key=api_key, api_secret=api_secret)

    def getCoinList(self):
        pass

    def getCoinBalance(self, coin):
        pass

    def getAcceptedTimeframes(self):
        pass

    def getCoinLastKlines(self, symbol):
        pass

    def getCoinLastPrice(self, symbol):
        searchPrice = True
        limit = 10
        c = 0
        while searchPrice and c < 6:
            c += 1
            try:
                response = requests.get(
                    url=self.api_endpoint+"api/v3/ticker/price?symbol=" + symbol,
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
                # logging.critical(symbol)
                # logging.critical(e, exc_info=True)
        # logging.critical("No trades found for symbol %s " % (symbol,))
        exit("KILL Process - No trades found for symbol %s " % (symbol,))

    def getCoin24hVolume(self, symbol):
        pass

    def makeMarketBuyOrder(self, symbol, baseQty, assetQty):
        pass

    def makeMarketSellOrder(self, symbol, baseQty, assetQty):
        pass

    def startWsCheckPrice(self, symbol, callback):
        pass

    def stopWsCheckPrice(self):
        pass