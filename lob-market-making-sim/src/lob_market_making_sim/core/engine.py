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
        self.filled_buy = 0
        self.filled_sell = 0

        # the IDs of orders placed by the agent 
        self.bid_oid = None
        self.ask_oid = None

        # number of events were able to execute
        self.num_events_executed = 0

        # Default quote size for agent order- can later update
        self.QUOTE_SIZE = 10

    def ticks(self, p): return round(p * 100)      # $ -> rounded cents

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

        # bid side
        if bid is None:
            if self.bid_oid is not None:
                self.ob.cancel_agent_quote(self.bid_oid)
                self.bid_oid = None
        else:
            if self.bid_oid is None:
                self.bid_oid = self.ob.place_agent_quote(Direction.BUY, bid,
                                                        self.QUOTE_SIZE)
            else:
                cur = self.ob._orders[self.bid_oid].price
                if cur != bid:
                    self.ob.cancel_agent_quote(self.bid_oid)
                    self.bid_oid = self.ob.place_agent_quote(Direction.BUY, bid,
                                                            self.QUOTE_SIZE)

        # ask side
        if ask is None:
            if self.ask_oid is not None:
                self.ob.cancel_agent_quote(self.ask_oid)
                self.ask_oid = None
        else:
            if self.ask_oid is None:
                self.ask_oid = self.ob.place_agent_quote(Direction.SELL, ask,
                                                        self.QUOTE_SIZE)
            else:
                cur = self.ob._orders[self.ask_oid].price
                if cur != ask:
                    self.ob.cancel_agent_quote(self.ask_oid)
                    self.ask_oid = self.ob.place_agent_quote(Direction.SELL, ask,
                                                            self.QUOTE_SIZE)

        self.log_quote(ts, bid if bid is not None else float('nan'),
                        ask if ask is not None else float('nan'))

    def apply_event(self, market_event: OrderEvent):
        '''
        Apply the historical event to the book and (if it trades
        against our resting quote) update cash, inventory, and book
        via a *synthetic* EXECUTE_VISIBLE event on the agent's OID.
        Parameters:
        market_event (OrderEvent): the event to be processed
        Returns:
        num_events_processed, buy_fill, sell_fill
        '''
        
        num_events = self.ob.apply(market_event) # external event
        synthetic_events = 0
        buy_fill = sell_fill = 0

        # helper that executes (part of) an agent order
        def _hit_agent(oid, rec, hit_size):
            nonlocal synthetic_events, buy_fill, sell_fill

            # 1. inject synthetic execution so OrderBookL1 updates depth
            exec_ev = OrderEvent(
                ts = market_event.ts,
                etype = EventType.EXECUTE_VISIBLE,
                oid = oid,
                direction = rec.direction,
                price = rec.price,
                size = hit_size
            )
            synthetic_events += self.ob.apply(exec_ev)

            # 2. cash & inventory from our point of view
            if rec.direction is Direction.BUY: # we bought first
                self.cash -= hit_size * rec.price
                self.inv += hit_size
                self.filled_buy += hit_size
                buy_fill += hit_size
            else: # we sold first
                self.cash += hit_size * rec.price
                self.inv -= hit_size
                self.filled_sell += hit_size
                sell_fill += hit_size

            # 3. if the order is now gone, clear
            if oid not in self.ob._orders:
                if rec.direction is Direction.BUY:
                    self.bid_oid = None
                else:
                    self.ask_oid = None

        # only trade-type events can hit us
        if market_event.etype in {EventType.EXECUTE_VISIBLE, EventType.CROSS}:
            # market BUY might hit our ASK
            if self.ask_oid is not None and market_event.direction is Direction.SELL:
                ask_rec = self.ob._orders.get(self.ask_oid) # our placed ask, if any

                # round to ticks in cents for consistency
                if ask_rec and self.ticks(market_event.price) >= self.ticks(ask_rec.price):
                    hit_qty = min(ask_rec.quantity, market_event.size)
                    _hit_agent(self.ask_oid, ask_rec, hit_qty)
            
            # market SELL might hit our BID
            if self.bid_oid is not None and market_event.direction is Direction.BUY:
                bid_rec = self.ob._orders.get(self.bid_oid)
                if bid_rec and self.ticks(market_event.price) <= self.ticks(bid_rec.price):
                    hit_qty = min(bid_rec.quantity, market_event.size)
                    _hit_agent(self.bid_oid, bid_rec, hit_qty)

        return num_events + synthetic_events, buy_fill, sell_fill


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

            # let market event hit the tape & maybe us
            num_ev, _, _ = self.apply_event(event)

            # update metrics
            self.num_events_executed += num_ev

            # only calculate midprice with non-agent quotes
            clean_mid = self.ob.mid_external()
            if clean_mid is None:
                # keep existing quotes, but don't adjust reservation price
                self.midprices.append(self.ob.midprice())
                continue

            # get our bid and ask
            bid, ask = self.strategy.quote(clean_mid, self.inv, tau)

            # cancel-and-replace our quotes
            self._update_quotes(bid, ask, ts=event.ts)

            # For debugging: only compare if there's a previous midprice
            '''
            if self.midprices and abs(clean_mid - self.midprices[-1]) > 0.05:
                bb, ba = self.ob.best_bid.price, self.ob.best_ask.price
                bbe, bae = (self.ob.mid_external() * 2 - ba, ba)  # crude invert
                print(f"JUMP @ ts={event.ts}  best_bid={bb} best_ask={ba}  "
                      f"agent_bid={self.ob._orders.get(self.bid_oid)} "
                      f"agent_ask={self.ob._orders.get(self.ask_oid)}")
            '''

            # store the post-event midprice
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
