'''
test_vol.py
'''

import numpy as np
import pytest
from lob_market_making_sim.evaluation.vol import ewma_sigma

def test_vol_constant_series():
    '''
    For a constant series, the volatility is zero.
    '''
    prices = np.full(100, 100.0) # list of 100 values, each of value 100.0
    assert ewma_sigma(prices) == pytest.approx(0.0, abs=1e-12) # asserts the values are equal, within a tolerance

def test_vol_unknown_series():
    '''
    Ensures EWMA is the same as standard deviation when there is no decay.
    '''
    prices = np.array([100.0, 101.0, 100]) # up one tick, down one tick
    sigma = ewma_sigma(prices, alpha=0, seconds_per_year = 1) # no annualization or decay
    expected = np.std(np.diff(np.log(prices)), ddof=0) # true standard deviation
    assert sigma == pytest.approx(expected)