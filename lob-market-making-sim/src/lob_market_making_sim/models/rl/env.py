'''
env.py
Creates a custom gymnasium environment to represent a market making strategy.

A gymnasium environment is "a high-level python class representing a Markov Decision process."
https://gymnasium.farama.org/introduction/basic_usage/

Creating a custom gymnasium environment.
https://gymnasium.farama.org/introduction/create_custom_env/
'''

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from typing import Iterable
from lob_market_making_sim.core.engine import ReplayEngine
from lob_market_making_sim.core.order_book import OrderBookL1
from lob_market_making_sim.io.schema import OrderEvent
from lob_market_making_sim.io.schema import TICK_SIZE, EventType, Direction

class LOBMarketMakerEnv(gym.Env):
    '''
    Market-Making environment for a day of trading.
    '''
    def __init__(self, event_sequence: Iterable[OrderEvent],
                 inventory_limit: int = 1000,
                 lambda_=1e-3,
                 alpha_=1e-4):

        super().__init__()

        self.event_sequence = event_sequence
        self.inventory_limit = inventory_limit
        self.lambda_ = lambda_
        self.alpha_ = alpha_

        self.t = 0
        self.inventory = 0
        self.cash = 0
        self.order_book = OrderBookL1()
        self.engine = ReplayEngine()

        # Define action and observation spaces
        # 7x7 discrete gird = 49 actions
        # Each action is a pair (bid_offset, ask_offset) \in [-3, 3] \times [-3, 3]
        # Will allow the agent to select from 7 discrete offsets
        self.action_space = spaces.Discrete(49)

        # Observation = [best_bid, best_ask, agent_bid, agent_ask, inventory, time]
        self.observation_space = spaces.Box(
            low = np.array([0, 0, 0, 0, -inventory_limit, 0]),
            high = np.array([1e6, 1e6, 1e6, inventory_limit, 1.0]),
            dtype = np.float32
        )

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        # Reset internal markers
        self.t = 0 # Index for each event
        self.inventory = 0
        self.cash = 0

        self.order_book.reset()
        self.engine.reset(self.order_book)

        # May not need to preload the first event
        self.current_event = self.event_sequence[0]

        # return obs
        return self._get_obs(), {}
    
    def step(self, action):
        # Decode action to quote deltas
        bid_offset, ask_offset = self._decode_action(action)

        # Get midprice and compute bid/ask quotes
        mid = self.order_book.midprice()
        bid_price = int(mid / TICK_SIZE) + bid_offset
        ask_price = int(mid / TICK_SIZE) + ask_offset

        # Get next market event
        event = self.event_sequence[self.t]

        # Apply market event
        self.engine.apply_event(event)

        # Simulate agent quote being filled by this event
        filled_bid = False
        filled_ask = False

        if event.etype in {EventType.EXECUTE_VISIBLE, EventType.CROSS}:
            if event.direction is Direction.BUY and event.price >= ask_price:
                # We sell to incoming market buy because they are willing to buy
                # for more than what we are offering
                self.inventory -= event.size
                self.cash += event.size * ask_price * TICK_SIZE
                filled_ask = True

            elif event.direction is Direction.SELL and event.price <= bid_price:
                # We buy from incoming market sell because they are willing to sell
                # for less than or equal to what we are willing to pay
                self.inventory += event.size
                self.cash -= event.size * bid_price * TICK_SIZE
                filled_bid = True
            
        # Reward = mark-to-market PnL - inventory penalty
        new_mid = self.order_book.midprice()
        pnl = self.cash + self.inventory * new_mid
        reward = pnl - self.lambda_ * abs(self.inventory) - self.alpha_  * (self.inventory ** 2)

        # Step forward in time
        self.t += 1
        done = self.t >= len(self.event_sequence)
        
        # Log agent quote
        self.engine.log_quote(event.ts, bid_price, ask_price)
        
        return set._get_obs(), reward, done, False, {}

    def _get_obs(self):
        best_bid = self.order_book.best_bid.price
        best_ask = self.order_book.best_ask.price
        mid = self.order_book.midprice()

        return np.array([
            best_bid,
            best_ask,
            self.inventory,
            self.t / len(self.event_sequence) # normalized time
        ], dtype=np.float32)

    def _decode_action(self, action):
        bid_offset = action // 7 - 3
        ask_offset = action % 7 - 3
        return bid_offset, ask_offset

    def simulate_fills(self, event, bid_offset, ask_offset):
        '''
        Simulate whether agent's bid or ask is filled
        '''
        return None, None