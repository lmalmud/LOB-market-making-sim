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

class LOBMarketMakerEnv(gym.Env):
    '''
    MDP for a day of trading.
    '''
    def __init__(self):
        self.observation_space = spaces.Box()
        self.action_space = spaces.Discrete()

    def reset(self):
        pass
        #return obs
    
    def step(self, action):
        pass
        #return obs, reward, done, info