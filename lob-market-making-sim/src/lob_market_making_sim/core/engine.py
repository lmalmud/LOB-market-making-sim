'''
engine.py
Allows for execution of orders in the orderbook.
'''

from lob_market_making_sim.core.order_book import OrderBookL1
from lob_market_making_sim.models.base import MarketMaker # generic strategy abstract class
from lob_market_making_sim.io.schema import EventType, Direction, TICK_SIZE

class ReplayEngine:
    def __init__(self, ob: OrderBookL1, strategy: MarketMaker = None):
        self.ob = ob
        self.strategy = strategy # Default strategy is None
        self.quote_log = [] # Track every quote: (timestamp, bid, ask, midprice, inventory)
        self.midprices = [] # Track every midprice after each event
        self.inv = 0 # inventory, net position in shares
        self.cash = 0 # track P&L
    
    def run(self, events):
        '''
        Runs the simulation with the events in events
        Parameters
        events (Iterable[OrderEvent]): list of events to handle
        '''

        # closing time, which is 6.5 hours after midnight (in nanoseconds)
        T = 6.5*60*60 *1e+9
        for event in events:
            self.ob.apply(event)

            if self.strategy is not None:
                tau = T - event.ts # ending timestep - closing time = time till closing
                bid, ask = self.strategy.quote(self.ob.midprice(),
                                               self.inv,
                                               tau)
            
                # Decide if the current event will fill one of the quotes
                # The only two allowable events that would cause a transaction are
                # visible orders and cross trades (since they will include executing a buy
                # and sell order)
                if event.etype in {EventType.EXECUTE_VISIBLE, EventType.CROSS}:

                    if event.direction is Direction.BUY and event.price >= ask:
                        # We sell because someone is willing to buy for the same or more
                        self.inv += event.size
                        self.cash += event.size * ask * TICK_SIZE

                    elif event.direction is Direction.SELL and event.price <= bid:
                        # We buy because someone is willing to sell for the same or less
                        self.inv -= event.size
                        self.cash -= event.size * bid * TICK_SIZE

                # Note that this is an approximation: we are assuming that the quote sits
                # at the front and is filled entirely if the incoming event has a trade through that price

                self.log_quote(event.ts, bid, ask)


    def log_quote(self, timestamp, bid_price, ask_price):
        '''
        Adds a quote to the log of all quotes.
        Parameters:
        timestamp (float): nanoseconds since midnight trade executed
        bid_price (float): offered price to buy
        ask_price (float): desired price to sell
        '''
        self.quote_log.append((timestamp, bid_price, ask_price, self.ob.midprice(), self.inv))
