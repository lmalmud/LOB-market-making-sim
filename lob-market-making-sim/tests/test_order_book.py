"""
test_order_book.py
Unit-tests for OrderBookL1 using a small, hand-crafted AMZN message file.

time,type,oid,qty,px,direction
0.001000,1,100,100,1832400,1        Add 100 buy at price 1832400    
0.002000,1,101,120,1833000,-1       Add 120 sell at price 1833000
0.003000,1,102, 50,1832200,1        Add 50 buy at price 1832200 (leaves top unchanged)     
0.004000,2,100, 30,1832400,1        Partial cancel at price 1832400, 70 shares remaining 
0.005000,3,101,  0,1833000,-1       Delete all of the best sell
0.006000,1,103, 90,1833200,-1       Add more shares at ask price (only ask)    
0.007000,3,100,  0,1832400,1     
0.008000,5,9999,25,     0,1 

The sequence checks:
1.  Adding first bid / ask sets the top of book.
2.  Adding a lower bid leaves best-bid unchanged.
3.  Partial CANCEL updates size in place.
4.  DELETE on best-ask clears it.
5.  New ask at higher price becomes best-ask.
6.  DELETE on best-bid promotes next-highest bid price.
7.  Hidden EXECUTE leaves the book unchanged.

To run: poetry run pytest tests/test_order_book.py
"""
from pathlib import Path
from lob_market_making_sim.io.schema import OrderEvent
import pyarrow as pa
import pytest

from lob_market_making_sim.io.loader import lobster_to_arrow, arrow_to_events
from lob_market_making_sim.core.order_book import OrderBookL1, TopLevel
from lob_market_making_sim.io.schema import EventType, Direction

# Get the path to the sample data
FIXTURE = Path(__file__).parent / "data" / "sample_messages_AMZN.csv"

def _run_events(book, events):
    '''
    Apply each OrderEvent to the book and collect snapshots.
    events (Iterable[OrderEvent]): the events to execute
    '''
    snapshots = []
    for ev in events:
        book.apply(ev)
        snapshots.append((ev, book.best_bid, book.best_ask))
    return snapshots

def test_top_of_book_transitions():
    # Load fixture
    tbl: pa.Table = lobster_to_arrow(FIXTURE)       # CSV -> Arrow
    events = arrow_to_events(tbl)                   # Arrow -> OrderEvent iterator

    # Replay through OrderBookL1
    ob = OrderBookL1()
    snaps = _run_events(ob, events)

    # 1) After first two ADDs, top of book is 183.24/183.30 (sizes 100/120)
    ev, bid, ask = snaps[1]
    assert bid.price == 183.24 and bid.quantity == 100
    assert ask.price == 183.30 and ask.quantity == 120

    # 2) After adding lower-priced bid (event idx 1), best-bid unchanged
    _, bid, _ = snaps[2]
    assert bid.price == 183.24

    # 3) After partial CANCEL (idx 2), size shrinks from 100 -> 70
    _, bid, _ = snaps[3]
    assert bid.quantity == 70

    # 4) DELETE best-ask (idx 4) ⇒ ask disappears (qty == 0) …
    _, _, ask = snaps[4]
    assert ask.quantity == 0

    # 5) New ask @ 183.32 becomes best-ask (idx 5)
    _, _, ask = snaps[5]
    assert (round(ask.price, 2), ask.quantity) == (183.32, 90)

    # 6) DELETE best-bid (idx 6) promotes 183.22 bid (size 50)
    _, bid, _ = snaps[6]
    assert (bid.price, bid.quantity) == (183.22, 50)

    # 7) Hidden EXECUTE does *not* alter the book (idx 7 vs idx 6)
    _, bid_after, ask_after = snaps[7]
    assert bid_after == bid and ask_after == ask

def test_partial_execution_does_not_promote():
    ob = OrderBookL1()

    ob.apply(OrderEvent(
        ts=0, etype=EventType.ADD, oid=10, size=80,
        price=183.25, direction=Direction.SELL
    ))
    ob.apply(OrderEvent(
        ts=1, etype=EventType.EXECUTE_VISIBLE, oid=10, size=30,
        price=183.25, direction=Direction.SELL
    ))

    assert ob.best_ask.price == 183.25
    assert ob.best_ask.quantity == 50

def test_execute_visible_trade_updates_top():
    '''
    EXECUTE_VISIBLE should reduce top-level size,
    and promote next-best if depleted.
    '''
    ob = OrderBookL1()

    # Add two buy orders
    ob.apply(OrderEvent(
        ts=0, etype=EventType.ADD, oid=1, size=100,
        price=183.24, direction=Direction.BUY
    ))
    ob.apply(OrderEvent(
        ts=1, etype=EventType.ADD, oid=2, size=50,
        price=183.22, direction=Direction.BUY
    ))

    # Execute 100 shares from oid=1 (top level)
    ob.apply(OrderEvent(
        ts=2, etype=EventType.EXECUTE_VISIBLE, oid=1, size=100,
        price=183.24, direction=Direction.BUY
    ))

    # Check that top of book is now 1832200
    assert ob.best_bid.price == 183.22
    assert ob.best_bid.quantity == 50

