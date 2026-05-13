from typing import Type

from transforms.profiles import (
    CellularAutomataProfile,
    RandomDropProfile,
    RidgedMultifractalProfile,
    StochasticProfile,
    TerracedBrownianProfile,
    WeierstrassProfile,
)

WEIERSTRASS = "weierstrass"
TERRACED = "terraced"
CELLULAR_AUTOMATA = "cellular_automata"
RIDGED_MULTIFRACTAL = "ridged_multifractal"
RANDOM_DROP = "random_drop"


PROFILE_TYPES: dict[str, Type[StochasticProfile]] = {
    WEIERSTRASS: WeierstrassProfile,
    TERRACED: TerracedBrownianProfile,
    CELLULAR_AUTOMATA: CellularAutomataProfile,
    RIDGED_MULTIFRACTAL: RidgedMultifractalProfile,
    RANDOM_DROP: RandomDropProfile,
}


def build_profile(profile_config: object) -> StochasticProfile:
    """
    Constructs a StochasticProfile instance from a configuration dictionary.
    """
    if not isinstance(profile_config, dict):
        raise ValueError("Profile configuration must be a dictionary.")

    profile_type = profile_config.get("type")
    if not isinstance(profile_type, str) or not profile_type:
        raise ValueError("Profile configuration must contain a non-empty 'type' string.")

    try:
        profile_class = PROFILE_TYPES[profile_type]
    except KeyError as exc:
        valid_types = ", ".join(f"'{k}'" for k in sorted(PROFILE_TYPES.keys()))
        raise ValueError(f"Unknown profile type: '{profile_type}'. Valid types are: {valid_types}.") from exc

    profile_params = profile_config.get("params", {})
    if not isinstance(profile_params, dict):
        raise ValueError("The 'params' key, if present, must be a dictionary.")

    try:
        return profile_class(**profile_params)
    except TypeError as exc:
        raise ValueError(f"Invalid parameters for profile type '{profile_type}': {exc}") from exc
