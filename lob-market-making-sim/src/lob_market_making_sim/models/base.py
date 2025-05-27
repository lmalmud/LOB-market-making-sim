'''
base.py
A single parent class to swap A-S with RL later.
'''

from abc import ABC, abstractmethod # To create abstract base classes

class MarketMaker(ABC):
    @abstractmethod
    def quote(self, mid: float, inv: int, t: float) -> tuple[float, float]:
        '''
        Return (bid_price, ask_price) for current step.
        Parameters

        Returns
        '''
        pass

    @abstractmethod
    def reset(self):
        '''
        Clear internal state before a new replay run.
        '''
        pass