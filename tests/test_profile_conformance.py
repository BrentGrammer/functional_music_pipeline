import pytest

from transforms.profiles import (
    CellularAutomataProfile,
    RidgedMultifractalProfile,
    StochasticProfile,
    TerracedBrownianProfile,
    WeierstrassProfile,
)


@pytest.mark.parametrize(
    "profile_instance",
    [
        WeierstrassProfile(),
        TerracedBrownianProfile(),
        CellularAutomataProfile(),
        RidgedMultifractalProfile(),
    ],
)
def test_profile_conforms_to_stochastic_profile(profile_instance):
    assert isinstance(profile_instance, StochasticProfile)
