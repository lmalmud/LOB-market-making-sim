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
from lob_market_making_sim.io.schema import EventType, Direction

NORMALIZED = True

class LOBMarketMakerEnv(gym.Env):
    '''
    Market-Making environment for a day of trading.
    '''
    def __init__(self, event_sequence: Iterable[OrderEvent],
                 inventory_limit: int = 1000,
                 lambda_ = 1e-3, alpha_ = 1e-4):

        super().__init__()

        self.lambda_ = lambda_
        self.alpha_ = alpha_

        self.event_sequence = event_sequence
        self.inventory_limit = inventory_limit

        self.t = 0
        self.order_book = OrderBookL1()
        self.engine = ReplayEngine(self.order_book)

        # Used when returning observations
        self.last_bid_price = 0
        self.last_ask_price = 0

        # Define action and observation spaces
        # 7x7 discrete gird = 49 actions
        # Each action is a pair (bid_offset, ask_offset) \in [-3, 3] \times [-3, 3]
        # Will allow the agent to select from 7 discrete offsets
        self.action_space = spaces.Discrete(49)

        # Observation = [best_bid, best_ask, agent_bid, agent_ask, inventory, time]
        self.observation_space = spaces.Box(
            low = np.array([0, 0, 0, 0, -inventory_limit, 0]),
            high = np.array([1e6, 1e6, 1e6, 1e6, inventory_limit, 1.0]),
            dtype = np.float32
        )

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        # Reset internal markers
        self.t = 0 # Index for each event

        self.order_book.reset()
        self.engine.reset(self.order_book)

        # May not need to preload the first event
        self.current_event = self.event_sequence[0]

        # return obs
        return self._get_obs(), {}
    
    def step(self, action):
        # 0: Decode action to quote deltas
        bid_tick, ask_tick = self._decode_action(action) # returns integer *ticks*

        # 1: process current market event
        event = self.event_sequence[self.t]
        self.engine.apply_event(event)

        # 2. compute clean mid AFTER tape event
        clean_mid = self.order_book.mid_external()
        if clean_mid is None:
            # skip quoting this step
            self.t += 1
            return self._get_obs(), 0.0, self.t >= len(self.event_sequence), False, {}
        bid_px = clean_mid + bid_tick * 0.01                # convert ticks → $
        ask_px = clean_mid + ask_tick * 0.01
        if self.engine.inv >= self.inventory_limit:
            bid_px = None
        if self.engine.inv <= -self.inventory_limit:
            ask_px = None
        
        # 3. post / cancel our quotes
        self.engine._update_quotes(bid_px, ask_px, event.ts)

        # 4. reward (use engine states)
        pnl = self.engine.cash + self.engine.inv * clean_mid
        reward = pnl - self.lambda_ * abs(self.engine.inv) - self.alpha_ * self.engine.inv**2

        # 5: Step forward in time
        self.t += 1
        done = self.t >= len(self.event_sequence)

        # inventory liquidation - so agent learns to finish flat
        if done:
            reward -= abs(self.engine.inv) * 0.02     # cost to unwind
        return self._get_obs(), reward, done, False, {}

    def _get_obs(self):
        best_bid = self.order_book.best_bid.price
        best_ask = self.order_book.best_ask.price
        mid = self.order_book.midprice()

        # Compute agent's current quotes (use last action or store them as attributes)
        agent_bid = getattr(self, "last_bid_price", best_bid)
        agent_ask = getattr(self, "last_ask_price", best_ask)

        if not NORMALIZED:
            return np.array([
                best_bid,
                best_ask,
                agent_bid,
                agent_ask,
                self.engine.inv / self.inventory_limit, # normalized inventory limit
                self.t / len(self.event_sequence) # normalized time
            ], dtype=np.float32)
        
        # Since we are trading across multiple tickers, it makes sense to normalize.
        else:
            return np.array([
                0 if mid == 0 else (best_bid - mid) / mid,
                0 if mid == 0 else (best_ask - mid) / mid,
                0 if mid == 0 else (agent_bid - mid) / mid,
                0 if mid == 0 else (agent_ask - mid) / mid,
                self.engine.inv / self.inventory_limit,
                self.t / len(self.event_sequence)
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