"""
Integration test for OrderBookL1 + ReplayEngine.

Scenario
========
External book is seeded with
    • 100 @ 99  (BUY   oid=1)
    • 100 @ 101 (SELL  oid=2)

Our (dummy) market-maker always quotes  99 bid / 101 ask  for 10 shares.

Market events fed to the engine:

 ts 3 : EXECUTE_VISIBLE BUY  99 × 5   (hits nothing – we have no quotes yet)
 ts 4 : EXECUTE_VISIBLE BUY  99 × 5   (hits *our* bid for 5)
 ts 5 : EXECUTE_VISIBLE SELL 101 × 5   (hits *our* ask for 5)
 ts 6 : EXECUTE_VISIBLE SELL 101 × 5   (finishes our ask)

Expected results
----------------
• quote_log has four rows (ts 3-6) – inventory path 0, +5, 0, –5
• final cash  = +515   (profit: bought 10 @ 99, sold 10 @ 101)
• final inv   = –5     (short 5 after the last sale)
• agent's bid is gone; agent's ask is gone.

If any assertion fails, the test pinpoints the step.
"""

from lob_market_making_sim.io.schema import EventType, Direction, OrderEvent
from lob_market_making_sim.core.order_book import OrderBookL1
from lob_market_making_sim.core.engine import ReplayEngine
from lob_market_making_sim.models.base import MarketMaker


# ---------- constant-spread dummy strategy ---------------------------
class StaticMM(MarketMaker):
    def quote(self, mid: float, inv: int, t: float):
        return 99, 101          # always the same prices
    def reset(self):            # nothing to reset
        pass


# ---------- pretty-printer ------------------------------------------
def show_top(label, ob):
    print(f"{label:>6} | bid {ob.best_bid.price:>3}×{ob.best_bid.quantity:<3} "
          f"| ask {ob.best_ask.price:>3}×{ob.best_ask.quantity:<3}")


# ---------- seed the external book ----------------------------------
ob = OrderBookL1()
seed = [
    OrderEvent(ts=1, etype=EventType.ADD, oid=1,
               direction=Direction.BUY,  price=99,  size=100),
    OrderEvent(ts=2, etype=EventType.ADD, oid=2,
               direction=Direction.SELL, price=101, size=100),
]
for ev in seed:
    ob.apply(ev)

show_top("seed", ob)
assert ob.best_bid.price == 99 and ob.best_ask.price == 101

# ---------- build engine --------------------------------------------
engine = ReplayEngine(ob, StaticMM())
engine.QUOTE_SIZE = 10           # agent posts 10×10 shares

# ---------- tape events that will hit us ----------------------------
events = [
    # 1) first trade happens *before* we have quotes – no fill
    OrderEvent(ts=3, etype=EventType.EXECUTE_VISIBLE, oid=1,
               direction=Direction.BUY, price=99, size=5),
    # 2) partial hit on our bid
    OrderEvent(ts=4, etype=EventType.EXECUTE_VISIBLE, oid=1,
               direction=Direction.BUY, price=99, size=5),
    # 3) partial hit on our ask
    OrderEvent(ts=5, etype=EventType.EXECUTE_VISIBLE, oid=2,
               direction=Direction.SELL, price=101, size=5),
    # 4) final hit on our ask
    OrderEvent(ts=6, etype=EventType.EXECUTE_VISIBLE, oid=2,
               direction=Direction.SELL, price=101, size=5),
]

engine.run(events)

# ---------- expected quote log --------------------------------------
expected_inv = [0, 5, 0, -5]
expected_ts  = [3, 4, 5, 6]

assert len(engine.quote_log) == 4, "quote_log should have 4 rows"

for (row, exp_ts, exp_inv) in zip(engine.quote_log, expected_ts, expected_inv):
    ts, bid, ask, mid, inv = row
    assert ts == exp_ts,          f'ts mismatch: got {ts}, expected {exp_ts}'
    assert bid == 99 and ask == 101, "bid/ask should stay constant"
    assert inv == exp_inv,        f'inventory path wrong at ts={ts}'
    print(f'ts = {ts} OK ✔')
print("\nQuote-log OK ✔")

# ---------- book & P&L assertions -----------------------------------
print(f"Final cash      : {engine.cash}")
print(f"Final inventory : {engine.inv}")
show_top("final", ob)

# --- P&L and inventory checks---------------------------
assert engine.cash == 515,  "cash P&L should be +515"
assert engine.inv  == -5,   "inventory should be –5"

# --- Order-book residuals -------------------------------------------
# Bid should still have 5 shares left from the earlier partial fill
bid_rec = ob._orders.get(engine.bid_oid)
assert bid_rec is not None,        "bid should still exist (5 shares left)"
assert bid_rec.quantity == 5,      "bid residual size should be 5"
assert bid_rec.price == 99,        "bid price should be 99"

# Ask was fully filled and then immediately refreshed to 10 shares
ask_rec = ob._orders.get(engine.ask_oid)
assert ask_rec is not None,        "ask should have been re-quoted"
assert ask_rec.quantity == 10,     "new ask size should be 10"
assert ask_rec.price == 101,       "ask price should be 101"

print("\n✅  All assertions passed – engine & book behave as expected.")


