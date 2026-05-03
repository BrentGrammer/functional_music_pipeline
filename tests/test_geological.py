import pytest

from score_model.tone import Tone
from transforms.base import ToneDimension
from transforms.geological import (
    _apply_stochastic_profile,
    apply_geological_transform,
)
from transforms.profiles import (
    CellularAutomataProfile,
    RandomDropProfile,
    RidgedMultifractalProfile,
    TerracedBrownianProfile,
    WeierstrassProfile,
)


class FakeProfile:
    def __init__(self, values: list[float]):
        self._values = values

    def generate(self, length: int) -> list[float]:
        return self._values[:length]


class TestGeologicalTransforms:
    def test_apply_stochastic_profile_frequency(self):
        tones = [Tone(frequency=440.0), Tone(frequency=880.0)]
        profile = [1.0, -1.0]  # Max intensity up, max intensity down
        intensity = 0.5  # +/- 50% variance

        result = _apply_stochastic_profile(tones, profile, ToneDimension.FREQUENCY, intensity)

        assert len(result) == 2
        assert result[0].frequency == pytest.approx(440.0 * 1.5)
        assert result[1].frequency == pytest.approx(880.0 * 0.5)

    def test_apply_stochastic_profile_duration(self):
        tones = [Tone(frequency=440.0, duration=1.0)]
        profile = [-0.2]
        intensity = 0.5

        result = _apply_stochastic_profile(tones, profile, ToneDimension.DURATION, intensity)

        assert len(result) == 1
        assert result[0].duration == pytest.approx(1.0 * (1.0 - (0.2 * 0.5)))

    def test_apply_stochastic_profile_amplitude(self):
        tones = [
            Tone(frequency=440.0, amplitude=0.5),
            Tone(frequency=440.0, amplitude=0.5)
        ]
        profile = [1.0, -1.0]
        intensity = 0.5

        # First tone gets scaled by +50% (0.5 * 1.5 = 0.75)
        # Second tone gets scaled by -50% (0.5 * 0.5 = 0.25)
        result = _apply_stochastic_profile(tones, profile, ToneDimension.AMPLITUDE, intensity)

        assert len(result) == 2
        assert result[0].amplitude == pytest.approx(0.75)
        assert result[1].amplitude == pytest.approx(0.25)

    def test_apply_geological_transform_with_fake_profile(self):
        # This test verifies the unified transform function works against the
        # `StochasticProfile` protocol interface, not a specific concrete implementation.
        tones = [Tone(frequency=440.0), Tone(frequency=880.0)]
        profile = FakeProfile([1.0, -1.0])  # Max intensity up, max intensity down
        intensity = 0.1  # +/- 10%

        result = apply_geological_transform(tones, profile, ToneDimension.FREQUENCY, intensity)

        assert len(result) == 2
        assert result[0].frequency == pytest.approx(440.0 * 1.1)
        assert result[1].frequency == pytest.approx(880.0 * 0.9)

    @pytest.mark.parametrize(
        "profile_instance",
        [
            WeierstrassProfile(seed=42),
            TerracedBrownianProfile(seed=42),
            CellularAutomataProfile(seed=42),
            RidgedMultifractalProfile(seed=42),
            RandomDropProfile(seed=42),
        ],
    )
    def test_apply_geological_transform_with_real_profiles(self, profile_instance):
        # This test locks in the behavior of the unified transform against all
        # concrete profile implementations before we refactor the old wrappers.
        tones = [Tone(440.0) for _ in range(5)]
        intensity = 0.1

        # Test determinism
        result1 = apply_geological_transform(
            tones, profile_instance, ToneDimension.FREQUENCY, intensity
        )
        result2 = apply_geological_transform(
            tones, profile_instance, ToneDimension.FREQUENCY, intensity
        )

        assert [t.frequency for t in result1] == [t.frequency for t in result2]

        # Test invariants
        assert len(result1) == len(tones)
        assert all(isinstance(t, Tone) for t in result1)

    def test_empty_sequence(self):
        profile = FakeProfile([])
        assert apply_geological_transform([], profile, ToneDimension.FREQUENCY, 0.1) == []
