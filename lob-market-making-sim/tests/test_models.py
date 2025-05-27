
"""
Unit-tests for the base MarketMaker interface and ASParams container.
Run with:  poetry run pytest tests/test_models.py::test_interface_implemented
"""

import pytest

from lob_market_making_sim.models.base import MarketMaker
from lob_market_making_sim.models.avellaneda import ASParams, AvellanedaStoikov
import dataclasses

def test_interface_implemented():
    '''
    AvellanedaStoikov should derive from the abstract MarketMaker class
    and return a sensible (bid, ask) tuple when called.
    '''
    assert issubclass(AvellanedaStoikov, MarketMaker)

    params = ASParams(gamma=0.1, kappa=1.0, sigma=0.002, qmax=1_000)
    strat  = AvellanedaStoikov(params)

    mid = 100.0
    bid, ask = strat.quote(mid=mid, inv=0, t=0.0)

    # Basic sanity checks
    assert bid < mid < ask
    assert round(ask - bid, 10) > 0          # non-zero spread
    assert isinstance(bid, float) and isinstance(ask, float)

def test_params_defaults():
    '''
    ASParams should be an immutable (frozen) dataclass
    with value-based equality.
    '''
    p1 = ASParams(gamma=0.1, kappa=1.0, sigma=0.001, qmax=500)
    p2 = ASParams(gamma=0.1, kappa=1.0, sigma=0.001, qmax=500)

    # equality by value, not identity
    assert p1 == p2 and id(p1) != id(p2)

    # immutability enforced
    with pytest.raises(dataclasses.FrozenInstanceError):
        p1.gamma = 0.2