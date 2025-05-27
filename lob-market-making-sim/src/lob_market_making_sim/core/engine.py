'''
engine.py
Allows for execution of orders in the orderbook.
'''

from order_book import OrderBookL1

class ReplayEngine:
    def __init__(self, ob: OrderBookL1, callbacks=None):
        self.ob = ob
    
    def run(self, events):
        '''
        Runs the simulation with the events in events
        Parameters
        events (Iterable[OrderEvent]): list of events to handle
        '''
        for event in events:
            self.ob.apply(event)