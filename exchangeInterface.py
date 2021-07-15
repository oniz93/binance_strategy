class ExchangeInterface:

    api_object = None
    def __init__(self, exchangeObject):
        self.api_object = exchangeObject

    def getCoinList(self):
        return self.api_object.getCoinList()

    def getAcceptedTimeframes(self):
        return self.api_object.timeFrames

    def getCoinLastKlines(self, symbol):
        return self.api_object.getCoinLastKlines(symbol)

    def getCoinLastPrice(self, symbol):
        return self.api_object.getCoinLastPrice(symbol)

    def getCoin24hVolume(self, symbol):
        return self.api_object.getCoin24hVolume(symbol)

    def makeMarketBuyOrder(self, symbol, baseQty, assetQty):
        return self.api_object.makeMarketBuyOrder(symbol, baseQty, assetQty)

    def makeMarketSellOrder(self, symbol, baseQty, assetQty):
        return self.api_object.makeMarketSellOrder(symbol, baseQty, assetQty)

    def startWsCheckPrice(self, symbol, callback):
        self.api_object.startWsCheckPrice(symbol, callback)

    def stopWsCheckPrice(self):
        self.api_object.stopWsCheckPrice()

    def getCoinBalance(self, coin):
        return self.api_object.getCoinBalance(coin)