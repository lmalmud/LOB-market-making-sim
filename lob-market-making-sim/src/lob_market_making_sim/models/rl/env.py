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
    MDP for a day of trading.
    '''
    def __init__(self, events: Iterable[OrderEvent], inventory_limit: int = 1000):

        self.ob = OrderBookL1() # orderbook for internal use
        self.events = events # list of events that will be processed throught the simulation

        # inventory limiti is the maximum amount of security a market maker is willing
        # to hold in their account (in order to control risk)
        self.inventory_limit = inventory_limit

        self.observation_space = spaces.Box()
        self.action_space = spaces.Discrete()

    def reset(self):
        pass
        #return obs
    
    def step(self, action):
        pass
        #return obs, reward, done, info