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

        # Apply next market event
        event = self.event_sequence[self.t]
        self.engine.
        #return obs, reward, done, info

    def _get_obs(self):
        pass

    def _decode_action(self, action):
        bid_offset = action // 7 - 3
        ask_offset = action % 7 - 3
        return bid_offset, ask_offset

    def simulate_fills(self, event, bid_offset, ask_offset):
        pass