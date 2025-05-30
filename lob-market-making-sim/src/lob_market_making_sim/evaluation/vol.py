'''
vol.py
Estimate mid-price volatility with an EWMA = Exponentially Weighted Moving Average.

https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/exponentially-weighted-moving-average-ewma/
EWMA: quantantive measure used to model/describe a time series
EWMA_t = \alpha * r_t * (1-\alpha) * EWMA_{t-1}
r_t: value of series in current period
\alpha: weight decided by user
Older observations are given lower weights.
Weights fall exponentially as data points get lower.
'''

from typing import Sequence
import numpy as np

def ewma_sigma(prices: Sequence[float], 
               *, 
               alpha: float=.94, 
               seconds_per_year:  float = 252*6.5*60*60):
    '''
    Return the annualized EWMA volatility of a price series.
    Parameters
    prices (Sequence[float]): midprices in dollars, taken at uniform intervals
    alpha (float): decay factor, which is .8 above for volatility modeling
    seconds_per_year (float): used to annualize
        6.5 trading hours * 252 days is default
    Returns
        float: annualized standard deviation in dollars (same unit as prices)
    Raises
        ValueError: if not enough price points
    '''

    prices = np.asarray(prices, dtype=float) # Convert given prices to float
    if prices.size < 2:
        raise ValueError("Need at least two price points")
    
    log_returns = np.diff(np.log(prices))
    var = 0.0
    for ret in log_returns:
        var = alpha *var + (1-alpha)* (ret**2)
    return np.sqrt(var*seconds_per_year) # Annualize