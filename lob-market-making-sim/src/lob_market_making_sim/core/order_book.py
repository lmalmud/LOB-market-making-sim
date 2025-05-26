'''
order_book.py
Defines a class to represent a level one order book, allowing for execution
of event orders and tracks relevent trade information.
'''

from lob_market_making_sim.io.schema import OrderEvent, Direction, EventType
from typing import Optional, Dict # Allows for gradual typing of basic objects
from dataclasses import dataclass
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

        # Key is the ID of the each event, necessary for
        self._orders: Dict[int, OrderRec] = {}

    def apply(self, ev : OrderEvent):
        '''
        Update the top top of the book given a single event, as would
        be described from the LOBSTER messages.
        Parameters:
        ev (schema.OrderEvent): the desired event to execute
        '''

        # If the event is a new offer, update only if this offer best better
        # than the best current buy or sell offer
        if ev.etype is EventType.ADD:

            # Add to the list of all orders
            if ev.oid in self._orders:
                self._orders[ev.oid].quantity += ev.size # Increase to an existing order
            else: # An entirely new order is added
                self._orders[ev.oid] = OrderRec(direction=ev.direction, price=ev.price, quantity=ev.quantity)

            if ev.direction is Direction.BUY:

                self._bid_depth[ev.price] += ev.size # Add price and size to list of bids

                # Note that if this is the first event, this block will always run
                # since bid prices are positive
                if ev.price >= self.best_bid.price:
                    # If this is an addition to what is already at the top of the book,
                    # then the new quantity will be updated and stored in bid_depth
                    self.best_bid = OrderRec(price=ev.price, quantity=self._bid_depth[ev.price])
                    

            elif ev.direction is Direction.SELL:
                # Executes if the new price is lower than the best offer to sell, or if no
                # entry has been made yet
                if ev.price < self.best_ask_price or self.best_ask_price == 0:
                    self.best_ask = OrderRec(price = ev.price, quantity = ev.size, direction = Direction.SELL)
                    self._top_order_oids[ev.oid] = Direction.SELL
                else:
                    self._ask_depth[ev.price] = ev.size

        # Change the number of shares in one of the orders (partial deletion)
        # is the same as executing either a visible or hidden trade
        elif ev.etype is {EventType.CANCEL, EventType.EXECUTE_VISIBLE, EventType.EXECUTE_HIDDEN}:
            # Only need to change the quantity if the relevant offer is a top one
            if ev.oid in self._top_order_oids: 
                pass

        # An order is pulled
        elif ev.etype is EventType.DELETE:
            if ev.oid in self._top_order_oids:
                if self._top_order_oids[ev.oid] is Direction.BUY:
                    self.best_bid = TopLevel()
                else:
                    self.best_ask = TopLevel()
                
                # No longer track orders that are not present
                del self._top_order_oids[ev.oid]

        # Only other event type is a cross trade/auction trade (when a buy and
        # sell order are executed at the same time), which will not effect
        # the top of the book

    def _promote_next_best(direction: Direction):
        '''
        If the top of the book order is deleted/fully sold,
        need to promote the next best one.
        Parameters
        direction (Direction): side of trade (bid/ask) to be modified
        '''
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