'''
avellaneda.py


https://medium.com/hummingbot/a-comprehensive-guide-to-avellaneda-stoikovs-market-making-strategy-102d64bf5df6

Unit sanity check:
σ in Avellaneda–Stoikov should be the mid-price σ in $ per √second.

If you estimated volatility in ticks per √second and then converted prices
to dollars, multiply by TICK_SIZE once when you create the ASParams.
'''
from dataclasses import dataclass
from lob_market_making_sim.models.base import MarketMaker
import math

@dataclass(frozen=True)
class ASParams:
    gamma: float # risk aversion
    kappa: float # LOB depth parameters
    sigma: float # daily volatility (tick units/sqrt(sec))
    qmax: int # inventory limit (sym)

def optimal_spread(q: int, params: ASParams, tau: float) -> float:
    '''
    Returns spread \delta(q) given current inventory.
    Returns
    float: optimal distance to place each quote away from the reservation price
    '''
    return (2 / params.gamma) * math.log(1 + params.gamma / params.kappa) + (params.gamma * (params.sigma ** 2) * tau)

def reservation_price(mid: float, q: int, params: ASParams, tau : float) -> float:
    '''
    Calculates the reservation price, as defined in the paper.
    Parameters
    mid (int): current midprice
    q (int): inventory
    params (ASParams): simulation parameters
    '''
    return mid - (q * params.gamma * (params.sigma **2 )* tau)

class AvellanedaStoikov(MarketMaker):
    '''
    Stateless implementation of the Avellaneda & Stoikov (2008)
    market-making model.
    '''

    def __init__(self, params: ASParams, horizon_sec: int = 6*60*60):
        self.params = params
        self._T = horizon_sec # automatically a 6 hour trading day

    def quote(self, mid : float, inv : int, t: float) -> tuple[float, float]:
        '''
        Retuns the quoted bid and ask price, as calculated by paper formulas.
        Parameters
        mid (float): current midprice, in dollars
        inv (int): number of shares
        t (float): current time
        Returns
        tuple[float, float]: final bid, final ask in dollars
        '''
        tau = max(self._T - t, 0)
        delta = optimal_spread(inv, self.params, tau)
        r = reservation_price(mid, inv, self.params, tau)

        # final bid, final ask
        return r - (delta/2), r + (delta/2)

    def reset():
        pass

