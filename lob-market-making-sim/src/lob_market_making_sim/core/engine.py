'''
engine.py
Allows for execution of orders in the orderbook.
'''

from lob_market_making_sim.core.order_book import OrderBookL1
from lob_market_making_sim.models.base import MarketMaker # generic strategy abstract class
from lob_market_making_sim.io.schema import EventType, Direction, OrderEvent

class ReplayEngine:
    def __init__(self, ob: OrderBookL1, strategy: MarketMaker = None):
        self.ob = ob
        self.strategy = strategy # Default strategy is None
        self.quote_log = [] # Track every quote: (timestamp, bid, ask, midprice, inventory)
        self.midprices = [] # Track every midprice after each event
        self.inv = 0 # inventory, net position in shares
        self.cash = 0 # track P&L

        # the IDs of orders placed by the agent 
        self.bid_oid = None
        self.ask_oid = None

        # number of events were able to execute
        self.num_events_executed = 0

        # Default quote size for agent order- can later update
        self.QUOTE_SIZE = 10

    def reset(self, ob = None) -> None:
        '''
        Clears all replay knowledge by calling the initializer.
        '''

        # Allow option to reset with an order book, otherwise uses what already have
        if ob == None:
            ob = self.ob
        self.__init__(ob)

    def _update_quotes(self, bid: float, ask: float, ts: float) -> None:
        '''
        Replace existing quotes with new ones.
        '''

        # Cancel old bids and asks, if they exist
        if self.bid_oid is not None:
            self.ob.cancel_agent_quote(self.bid_oid)
        if self.ask_oid is not None:
            self.ob.cancel_agent_quote(self.ask_oid)

        self.bid_oid = self.ob.place_agent_quote(Direction.BUY, bid, self.QUOTE_SIZE)
        self.ask_oid = self.ob.place_agent_quote(Direction.SELL, ask, self.QUOTE_SIZE)

        # time-stamp for logging
        self.log_quote(ts, bid, ask)

    def apply_event(self, event: OrderEvent):
        '''
        Apply a single order book event and see if it
        traded with our resting quotes
        Parameters:
        event (OrderEvent): the event to be processed
        Returns:
        num_events_processed, executed_buy_size, executed_sell_size
        '''
        num_events = self.ob.apply(event)

        filled_buy = filled_sell = 0

        # if the event is a trade, see if one of the agent oids were hit
        if event.etype in {EventType.EXECUTE_VISIBLE, EventType.CROSS}:
            # Market BUY hits our ask
            if event.oid == self.ask_oid and event.direction is Direction.BUY:
                filled_sell = event.size
                self.cash += filled_sell * event.price
                self.inv -= filled_sell
                self.ask_oid = None # was removed in apply()

            # Market SELL hits our bid
            elif event.oid == self.bid_oid and event.direction is Direction.SELL:
                filled_buy = event.size
                self.cash -= filled_buy * event.price
                self.inv += filled_buy
                self.bid_oid = None
        return num_events, filled_buy, filled_sell


    def run(self, events):
        '''
        Runs the simulation with the events in events
        Parameters
        events (Iterable[OrderEvent]): list of events to handle
        '''

        if self.strategy is None:
            raise ValueError("replayEngine.run() requires self.strategy to be set")

        # closing time, which is 6.5 hours after midnight (in seconds)
        T = 6.5*60*60
        for event in events:
            # convert event.ts in nanoseconds to seconds
            tau = max(T - event.ts * 1e-9, 0) # ending timestep - closing time = time till closing (s)

            # Apply the current market event
            self.ob.apply(event)
 
            # Gets the bid and ask from the strategy that is being implemented
            bid, ask = self.strategy.quote(self.ob.midprice(),
                                            self.inv,
                                            tau)
            
            # cancel old order, place new
            self._update_quotes(bid, ask, ts=event.ts)

            # apply market event placed by the agent and capture filles
            # FIXME: the event that is being applied here is not correct- it needs
            # to be the event that is placed by the strategy
            num_events, buy_fill, sell_fill = self.apply_event(event)
            self.num_events_executed += num_events

            # store the midprice
            self.midprices.append(self.ob.midprice())


    def log_quote(self, timestamp, bid_price, ask_price):
        '''
        Adds a quote to the log of all quotes.
        Parameters:
        timestamp (float): nanoseconds since midnight trade executed
        bid_price (float): offered price to buy
        ask_price (float): desired price to sell
        '''
        self.quote_log.append((timestamp, bid_price, ask_price, self.ob.midprice(), self.inv))
