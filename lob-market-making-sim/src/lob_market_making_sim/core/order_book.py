'''
order_book.py
Defines a class to represent a level one order book, allowing for execution
of event orders and tracks relevent trade information.
'''

from lob_market_making_sim.io.schema import OrderEvent, Direction, EventType
from typing import Optional, Dict # Allows for gradual typing of basic objects
from dataclasses import dataclass
import warnings # For warning messages
from collections import defaultdict # Container for regular dictionary

@dataclass
class TopLevel:
    '''
    Record of top level of book which only requires price
    and quantity information.
    '''
    price: int = 0
    quantity: int = 0

@dataclass
class OrderRec:
    '''
    Record of an order, only tracking relevant information
    to use when promoting next-best-orders.
    '''
    direction: Direction = None
    price: int = 0
    quantity: int = 0

class OrderBookL1:
    '''
    A level one order book only shows the best bid and ask prices,
    with their aggregate sizes.
    '''

    def __init__(self):
        # Note that OrderRec also stores the direction of trade, which is unecessary for
        # the best bid and ask
        self.best_bid = TopLevel()
        self.best_ask = TopLevel()

        # Require tracking price and quantity for *all* orders in case
        # the top order is deleted (key: price, value: quantity)
        self._bid_depth: Dict[int, int] = defaultdict(int)
        self._ask_depth: Dict[int, int] = defaultdict(int)

        # Key is the ID of the each event, necessary for tracking orders
        # Note that when an event that refers to an already made order occurs,
        # the oid will be that of the original order
        self._orders: Dict[int, OrderRec] = {}

        # Negative oid is reserved for our own quotes
        self._next_agent_oid = -1

    def place_agent_quote(self, direction: Direction, price: float, size: int = 1) -> int:
        '''
        Insert (or replace) the agent quote at price. Returns the oid.
        Parameters:
        direction (Direction): whether the quote is buy or sell
        price (float): desired price to buy/sell at
        size (int): number of shares requested
        Returns:
        int: oid
        '''
        oid = self._next_agent_oid
        self._next_agent_oid -= 1
        ev = OrderEvent(
            ts = 0.0, # not relevant for matching
            etype = EventType.ADD,
            oid = oid,
            direction = direction,
            price = price,
            size = size
        )
        self.apply(ev)
        return oid
    
    def cancel_agent_quote(self, oid: int) -> None:
        '''
        Delete's the agent's outstanding quote (if any)
        '''

        if oid in self._orders:
            rec = self._orders[oid] # record desired to delete
            ev = OrderEvent(
                ts = 0.0,
                etype = EventType.DELETE,
                oid = oid,
                direction = rec.direction,
                price = rec.price,
                size = rec.quantity
            )
            self.apply(ev)

    def reset(self):
        '''
        Resets the book by calling initialization again, erasing
        all stored information.
        '''
        self.__init__()

    def apply(self, ev : OrderEvent):
        '''
        Update the top top of the book given a single event, as would
        be described from the LOBSTER messages.
        Parameters:
        ev (schema.OrderEvent): the desired event to execute
        Returns:
        the number of events processed
        '''

        # print(f'TYPE {ev.direction} - OID {ev.oid} - PRICE {ev.price}')

        # If the event is a new offer, update only if this offer best better
        # than the best current buy or sell offer
        if ev.etype is EventType.ADD:

            if ev.oid in self._orders: # If this is adding to an existing order
                self._orders[ev.oid].quantity += ev.size
            else: # Otherwise, create a new entry
                self._orders[ev.oid] = OrderRec(direction = ev.direction, price = ev.price, quantity = ev.size)

            if ev.direction is Direction.BUY:

                self._bid_depth[ev.price] += ev.size # Add price and size to list of bids

                if ev.price == self.best_bid.price:
                    # If this is an addition to what is already at the top of the book
                    # Top of the book is updated to be consistent with the new number of shares
                    self.best_bid = TopLevel(price = ev.price, quantity = self._bid_depth[ev.price])
                elif ev.price > self.best_bid.price: # New top of the book
                    self._refresh_top(ev.direction)
                    
            elif ev.direction is Direction.SELL:

                self._ask_depth[ev.price] += ev.size

                if ev.price == self.best_ask.price:
                    self.best_ask = TopLevel(price = ev.price, quantity = self._ask_depth[ev.price])
                # Need to update the top of the book if it is the first entry as well
                elif ev.price < self.best_ask.price or self.best_ask.price == 0:
                    self._refresh_top(ev.direction)

        # Change the number of shares in one of the orders (partial deletion)
        # is the same as executing either a visible trade
        elif ev.etype is EventType.CANCEL or ev.etype is EventType.EXECUTE_VISIBLE:
            if ev.oid not in self._orders:
                warnings.warn(f'Unknown order ID {ev.oid} - cannot execute EXECUTE_VISIBLE or CANCEL, skipping execution')
                return 0
            self._orders[ev.oid].quantity -= ev.size

            # If selling this amount would consume all of the current shares
            if self._orders[ev.oid].quantity <= 0:
                if self._orders[ev.oid].quantity < 0:
                    warnings.warn("Attempt to execute order resulting in negative quantity.")
                del self._orders[ev.oid]

            # Update the appropriate depth
            self._update_depth(ev.direction, ev.price, -ev.size)

            # Handle the top of the book, if needed
            if ev.direction is Direction.BUY:    
                           
                if ev.price == self.best_bid.price: # Update top of book if relevent
                    self.best_bid = TopLevel(price = ev.price, quantity = self.best_bid.quantity - ev.size)
                    if self.best_bid.quantity <= 0:
                        self._refresh_top(Direction.BUY)

            elif ev.direction is Direction.SELL:
                # The price should never be less than best ask, because best ask is always the minimum ask
                if ev.price == self.best_ask.price:
                    self.best_ask = TopLevel(price = ev.price, quantity = self.best_ask.quantity - ev.size)
                    if self.best_ask.quantity <= 0:
                        self._refresh_top(Direction.SELL)

        # An order is pulled
        elif ev.etype is EventType.DELETE:

            if ev.oid not in self._orders:
                warnings.warn(f'Unknown order ID {ev.oid} - cannot execute DELETE, skipping execution')
                return 0

            record = self._orders.pop(ev.oid)
            # Updating by the -quantity will cause the item to be removed since 0 shares remaining
            self._update_depth(ev.direction, record.price, -record.quantity)
            self._refresh_top(ev.direction) # May cause a new top of book


        # Other event type is a cross trade/auction trade (when a buy and
        # sell order are executed at the same time), which will not effect
        # the top of the book

        # A hidden order will also not effect the order book (as it is an
        # order where size and quantity are concealed)

        # Halt does nothing
        return 1


    def _refresh_top(self, direction):
        '''
        Sets the top of the book to be the best, which may be
        triggered by a better price being added or the best
        price being fully deleted.
        Parameters
        direction (Direction): the side of the book to update
        '''
        if direction is Direction.BUY:
            if self._bid_depth: # Need to ensure there is a next price.
                next_price = max(self._bid_depth)
                next_quantity = self._bid_depth[next_price]
                self.best_bid = TopLevel(price = next_price, quantity = next_quantity)
            else: # If there are no possible next prices, then the top is zero
                self.best_bid = TopLevel()

        elif direction is Direction.SELL:
            if self._ask_depth:
                next_price = min(self._ask_depth)
                next_quantity = self._ask_depth[next_price]
                self.best_ask = TopLevel(price = next_price, quantity = next_quantity)
            else:
                self.best_ask = TopLevel()

    def _update_depth(self, direction : Direction, price, delta):
        '''
        Increments the quantity of shares at price of the specified price
        by delta.
        Parameters
        direction (Direction): to indicate whether the update is on buy or sell side
        price: price of share to be udpated
        delta: change in quantity
        '''
        if direction is Direction.BUY:
            self._bid_depth[price] += delta
            if self._bid_depth[price] <= 0:
                del self._bid_depth[price]

        elif direction is Direction.SELL:
            self._ask_depth[price] += delta
            if self._ask_depth[price] <= 0:
                del self._ask_depth[price]

    def snapshot(self) -> dict:
        '''
        Returns the current relevant information in the book.
        '''
        return dict(
            ts   = None,   # fill in engine loop
            bid  = self.best_bid.price,
            bsz  = self.best_bid.quantity,
            ask  = self.best_ask.price,
            asz  = self.best_ask.quantity,
            mid  = self.midprice()
        )

    def midprice(self) -> float:
        '''
        Returns the midprice (the average of the best bid and ask prices).
        Parameters:
        None
        Returns:
        float: the current midprice in dollars
        '''
        return (self.best_bid.price + self.best_ask.price) / 2