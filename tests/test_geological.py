import pytest

from score_model.tone import Tone
from transforms.base import ToneDimension
from transforms.geological import apply_stochastic_profile
from transforms.profiles import (
    CellularAutomataProfile,
    RandomDropProfile,
    RidgedMultifractalProfile,
    TerracedBrownianProfile,
    WeierstrassProfile,
)


class DeterministicMockProfile:
    """Deterministic test double for profiles that normally generate noise."""

    def __init__(self, deviation_scale_per_tone: list[float]):
        '''The tone deviation is scaled by the value in the list per tone matching the index position'''
        self._deviation_scales = deviation_scale_per_tone

    def generate(self, length: int) -> list[float]:
        return self._deviation_scales[:length]


class TestApplyStochasticProfile:
    def test_frequency_modulation_full_up_and_full_down_have_obvious_expected_outputs(self):
        first_base_frequency_hz = 440.0
        second_base_frequency_hz = 880.0
        deviation_scale_per_tone = [1.0, -1.0]
        max_deviation = 0.5  # allow up to +/-50% change from the original value
        tones = [
            Tone(frequency=first_base_frequency_hz),
            Tone(frequency=second_base_frequency_hz),
        ]
        profile = DeterministicMockProfile(deviation_scale_per_tone)

        result = apply_stochastic_profile(tones, profile, ToneDimension.FREQUENCY, max_deviation)
        
        FourFortyHz_pushed_up_50_percent = 660.0
        EightEightyHz_pushed_down_50_percent = 440.0

        assert len(result) == len(tones)
        assert result[0].frequency == pytest.approx(FourFortyHz_pushed_up_50_percent)
        assert result[1].frequency == pytest.approx(EightEightyHz_pushed_down_50_percent)
        assert result[0].duration == pytest.approx(tones[0].duration)
        assert result[1].duration == pytest.approx(tones[1].duration)
        assert result[0].amplitude == pytest.approx(tones[0].amplitude)
        assert result[1].amplitude == pytest.approx(tones[1].amplitude)

    def test_duration_modulation_uses_a_concrete_partial_downward_example(self):
        base_frequency_hz = 440.0
        base_duration_seconds = 1.0
        deviation_scale_for_tone = -0.2
        max_deviation = 0.5
        tones = [Tone(frequency=base_frequency_hz, duration=base_duration_seconds)]
        profile = DeterministicMockProfile([deviation_scale_for_tone])

        result = apply_stochastic_profile(tones, profile, ToneDimension.DURATION, max_deviation)

        # This example uses only part of the allowed downward motion:
        # 1.0s becomes 0.9s, while frequency and amplitude remain unchanged.
        expected_duration_seconds = 0.9

        assert len(result) == len(tones)
        assert result[0].duration == pytest.approx(expected_duration_seconds)
        assert result[0].frequency == pytest.approx(base_frequency_hz)
        assert result[0].amplitude == pytest.approx(tones[0].amplitude)

    def test_amplitude_modulation_uses_concrete_values_when_no_clamp_is_needed(self):
        base_frequency_hz = 440.0
        base_amplitude = 0.5
        deviation_scale_per_tone = [1.0, -1.0]
        max_deviation = 0.5
        tones = [
            Tone(frequency=base_frequency_hz, amplitude=base_amplitude),
            Tone(frequency=base_frequency_hz, amplitude=base_amplitude),
        ]
        profile = DeterministicMockProfile(deviation_scale_per_tone)

        result = apply_stochastic_profile(tones, profile, ToneDimension.AMPLITUDE, max_deviation)

        # Starting from 0.5 amplitude:
        # - full upward deviation produces 0.75
        # - full downward deviation produces 0.25
        expected_first_amplitude = 0.75
        expected_second_amplitude = 0.25

        assert len(result) == len(tones)
        assert result[0].amplitude == pytest.approx(expected_first_amplitude)
        assert result[1].amplitude == pytest.approx(expected_second_amplitude)
        assert result[0].frequency == pytest.approx(base_frequency_hz)
        assert result[1].frequency == pytest.approx(base_frequency_hz)
        assert result[0].duration == pytest.approx(tones[0].duration)
        assert result[1].duration == pytest.approx(tones[1].duration)

    def test_amplitude_modulation_clamps_to_the_valid_range(self):
        tones = [
            Tone(frequency=440.0, amplitude=0.8),
            Tone(frequency=440.0, amplitude=0.2),
        ]
        profile = DeterministicMockProfile([1.0, -1.0])
        max_deviation = 0.5

        result = apply_stochastic_profile(tones, profile, ToneDimension.AMPLITUDE, max_deviation)

        # Without clamping these would become 1.2 and 0.1.
        # The implementation must cap amplitudes at 1.0 and never go below 0.0.
        assert result[0].amplitude == pytest.approx(1.0)
        assert result[1].amplitude == pytest.approx(0.1)

    @pytest.mark.parametrize(
        "profile_instance",
        [
            pytest.param(WeierstrassProfile(seed=42), id="weierstrass"),
            pytest.param(TerracedBrownianProfile(seed=42), id="terraced_brownian"),
            pytest.param(CellularAutomataProfile(seed=42), id="cellular_automata"),
            pytest.param(RidgedMultifractalProfile(seed=42), id="ridged_multifractal"),
            pytest.param(RandomDropProfile(seed=42), id="random_drop"),
        ],
    )
    def test_seeded_profiles_produce_repeatable_modulation(self, profile_instance):
        tone_count = 5
        base_frequency_hz = 440.0
        max_deviation = 0.1
        tones = [Tone(base_frequency_hz) for _ in range(tone_count)]

        # Each concrete stochastic profile above is seeded. Reapplying the same profile
        # to the same input should therefore produce the same transformed frequencies.
        result1 = apply_stochastic_profile(
            tones, profile_instance, ToneDimension.FREQUENCY, max_deviation
        )
        result2 = apply_stochastic_profile(
            tones, profile_instance, ToneDimension.FREQUENCY, max_deviation
        )

        assert [t.frequency for t in result1] == [t.frequency for t in result2]
        assert len(result1) == len(tones)
        assert all(isinstance(t, Tone) for t in result1)

    def test_empty_sequence_returns_empty_list_without_asking_profile_for_values(self):
        class _ProfileThatMustNotBeCalled:
            def generate(self, length: int) -> list[float]:
                raise AssertionError("generate() should not be called for an empty tone sequence")

        profile = _ProfileThatMustNotBeCalled()

        result = apply_stochastic_profile([], profile, ToneDimension.FREQUENCY, 0.1)

        assert result == []
