'''
order_book.py
'''

class OrderBookL1:
    def __init__(self):
        self.best_bid_price = 0
        self.best_bid_size = 0
        self.best_ask_price = 0
        self.best_ask_size = 0
        self.orders = {}

    def apply(self, ev : OrderEvent):
        pass

    def snapshot(self) -> dict:
        pass

    def midprice(self) -> float:
        '''
        Returns the midprice (the average of the best bid and ask prices).
        Parameters:
        None
        Returns:
        float: the current midprice
        '''
        return (self.best_bid_price + self.best_ask_price) / 2