import pytest

from composition.profile_factory import (
    CELLULAR_AUTOMATA,
    PROFILE_TYPES,
    RANDOM_DROP,
    RIDGED_MULTIFRACTAL,
    TERRACED,
    WEIERSTRASS,
    build_profile,
)
from composition.schema import ProfileConfig
from transforms.profiles import (
    CellularAutomataProfile,
    RandomDropProfile,
    RidgedMultifractalProfile,
    StochasticProfile,
    TerracedBrownianProfile,
    WeierstrassProfile,
)


class TestProfileSchema:
    def test_profile_config_is_importable_and_definable(self):
        # Verifies ProfileConfig is correctly defined and importable.
        config_with_params: ProfileConfig = {
            "type": WEIERSTRASS,
            "params": {"seed": 42},
        }
        assert config_with_params["type"] == WEIERSTRASS

        config_without_params: ProfileConfig = {"type": TERRACED}
        assert config_without_params["type"] == TERRACED


class TestProfileFactoryRegistry:
    def test_profile_types_registry_contents(self):
        # This test ensures the registry is correctly populated with the expected
        # string-to-class mappings, which is critical for the factory's function.
        assert len(PROFILE_TYPES) == 5
        assert PROFILE_TYPES[WEIERSTRASS] is WeierstrassProfile
        assert PROFILE_TYPES[TERRACED] is TerracedBrownianProfile
        assert PROFILE_TYPES[CELLULAR_AUTOMATA] is CellularAutomataProfile
        assert PROFILE_TYPES[RIDGED_MULTIFRACTAL] is RidgedMultifractalProfile
        assert PROFILE_TYPES[RANDOM_DROP] is RandomDropProfile


class TestBuildProfile:
    def test_build_weierstrass_default_params(self):
        DEFAULT_PROFILE_SEED = 42
        config: ProfileConfig = {"type": WEIERSTRASS}

        profile = build_profile(config)

        assert isinstance(profile, WeierstrassProfile)
        assert isinstance(profile, StochasticProfile)
        # Check default value
        assert profile.seed == DEFAULT_PROFILE_SEED

    def test_build_terraced_with_params(self):
        TERRACED_SEED = 7
        TERRACED_STEP_SIZE = 0.3
        config: ProfileConfig = {
            "type": TERRACED,
            "params": {"seed": TERRACED_SEED, "step_size": TERRACED_STEP_SIZE},
        }

        profile = build_profile(config)

        assert isinstance(profile, TerracedBrownianProfile)
        assert isinstance(profile, StochasticProfile)
        assert profile.seed == TERRACED_SEED
        assert profile.step_size == TERRACED_STEP_SIZE

    def test_build_cellular_automata_with_params(self):
        CELLULAR_AUTOMATA_RULE = 110
        config: ProfileConfig = {
            "type": CELLULAR_AUTOMATA,
            "params": {"rule": CELLULAR_AUTOMATA_RULE},
        }

        profile = build_profile(config)

        assert isinstance(profile, CellularAutomataProfile)
        assert isinstance(profile, StochasticProfile)
        assert profile.rule == CELLULAR_AUTOMATA_RULE

    def test_build_ridged_multifractal_with_params(self):
        RIDGED_SEED = 99
        RIDGED_DROP_WHEN_NOISE_ABOVE = 0.75
        config: ProfileConfig = {
            "type": RIDGED_MULTIFRACTAL,
            "params": {
                "seed": RIDGED_SEED,
                "drop_when_noise_above": RIDGED_DROP_WHEN_NOISE_ABOVE,
            },
        }

        profile = build_profile(config)

        assert isinstance(profile, RidgedMultifractalProfile)
        assert isinstance(profile, StochasticProfile)
        assert profile.seed == RIDGED_SEED
        assert profile.drop_when_noise_above == RIDGED_DROP_WHEN_NOISE_ABOVE

    def test_build_random_drop_with_params(self):
        RANDOM_DROP_SEED = 17
        RANDOM_DROP_RATE = 0.35
        config: ProfileConfig = {
            "type": RANDOM_DROP,
            "params": {"seed": RANDOM_DROP_SEED, "drop_rate": RANDOM_DROP_RATE},
        }

        profile = build_profile(config)

        assert isinstance(profile, RandomDropProfile)
        assert isinstance(profile, StochasticProfile)
        assert profile.seed == RANDOM_DROP_SEED
        assert profile.drop_rate == RANDOM_DROP_RATE

    def test_build_profile_unknown_type_raises_error(self):
        UNKNOWN_PROFILE_TYPE = "nonexistent_profile"
        config: ProfileConfig = {"type": UNKNOWN_PROFILE_TYPE}

        with pytest.raises(ValueError) as exc_info:
            build_profile(config)

        # The error message must guide the user by listing available profiles.
        error_message = str(exc_info.value)
        assert UNKNOWN_PROFILE_TYPE in error_message
        assert "Valid types are" in error_message
        assert WEIERSTRASS in error_message

    @pytest.mark.parametrize(
        "malformed_config, expected_error_msg",
        [
            (None, "must be a dictionary"),
            ([], "must be a dictionary"),
            ({}, "must contain a non-empty 'type' string"),
            ({"type": None}, "must contain a non-empty 'type' string"),
            ({"type": ""}, "must contain a non-empty 'type' string"),
            (
                {"type": WEIERSTRASS, "params": "not_a_dict"},
                "must be a dictionary",
            ),
            ({"type": WEIERSTRASS, "params": 123}, "must be a dictionary"),
        ],
    )
    def test_build_profile_malformed_config_raises_error(
        self, malformed_config, expected_error_msg
    ):
        # The factory must reject fundamentally invalid config shapes
        # before attempting to build a profile.
        with pytest.raises(ValueError) as exc_info:
            build_profile(malformed_config)
        assert expected_error_msg in str(exc_info.value)

    def test_build_profile_with_unknown_param_raises_error(self):
        # The factory must reject configurations with unknown or misspelled parameters
        # to prevent user error. The underlying dataclass raises a TypeError which
        # should be converted to a more user-friendly ValueError.
        UNKNOWN_PARAM_KEY = "nonsense_param"
        config: ProfileConfig = {
            "type": WEIERSTRASS,
            "params": {UNKNOWN_PARAM_KEY: 123},
        }

        with pytest.raises(ValueError) as exc_info:
            build_profile(config)

        error_message = str(exc_info.value)
        assert "Invalid parameters" in error_message
        assert WEIERSTRASS in error_message
        assert UNKNOWN_PARAM_KEY in error_message
