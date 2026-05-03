import pytest
from score_model.tone import Tone
from transforms.duration import (
    resolve_strength,
    resolve_jaggedness,
    accelerando_transform,
    ritardando_transform,
    _compute_tempo_change_factors,
    _resolve_accelerando_final_duration_multiplier,
    _resolve_ritardando_final_duration_multiplier,
    _interpolate_multiplier_at_position,
    STRENGTH_NONE,
    STRENGTH_LOW,
    STRENGTH_MEDIUM,
    STRENGTH_HIGH,
    STRENGTH_EXTREME,
)


class TestResolveStrength:
    def test_default_is_medium(self):
        assert resolve_strength() == STRENGTH_MEDIUM

    def test_presets_case_insensitive(self):
        assert resolve_strength("none") == STRENGTH_NONE
        assert resolve_strength("NONE") == STRENGTH_NONE
        assert resolve_strength("None") == STRENGTH_NONE
        assert resolve_strength("low") == STRENGTH_LOW
        assert resolve_strength("medium") == STRENGTH_MEDIUM
        assert resolve_strength("high") == STRENGTH_HIGH
        assert resolve_strength("extreme") == STRENGTH_EXTREME

    def test_numeric_values_in_range(self):
        assert resolve_strength(0.0) == STRENGTH_NONE
        assert resolve_strength(0.5) == STRENGTH_MEDIUM
        assert resolve_strength(1.0) == STRENGTH_EXTREME
        assert resolve_strength(0.37) == 0.37

    def test_integer_values_in_range(self):
        assert resolve_strength(0) == STRENGTH_NONE
        assert resolve_strength(1) == STRENGTH_EXTREME

    def test_invalid_preset_raises_valueerror(self):
        with pytest.raises(ValueError):
            resolve_strength("wild")

    def test_out_of_range_numeric_raises_valueerror(self):
        with pytest.raises(ValueError):
            resolve_strength(-0.1)
        with pytest.raises(ValueError):
            resolve_strength(1.1)

    def test_boolean_raises_valueerror(self):
        with pytest.raises(ValueError):
            resolve_strength(True)
        with pytest.raises(ValueError):
            resolve_strength(False)

    def test_numeric_string_raises_valueerror(self):
        with pytest.raises(ValueError):
            resolve_strength("0.75")

    def test_invalid_type_raises_valueerror(self):
        with pytest.raises(ValueError):
            resolve_strength(None)


class TestResolveJaggedness:
    def test_default_is_none(self):
        assert resolve_jaggedness() == STRENGTH_NONE

    def test_presets_case_insensitive(self):
        assert resolve_jaggedness("none") == STRENGTH_NONE
        assert resolve_jaggedness("NONE") == STRENGTH_NONE
        assert resolve_jaggedness("low") == STRENGTH_LOW
        assert resolve_jaggedness("medium") == STRENGTH_MEDIUM
        assert resolve_jaggedness("high") == STRENGTH_HIGH
        assert resolve_jaggedness("extreme") == STRENGTH_EXTREME

    def test_numeric_values_in_range(self):
        assert resolve_jaggedness(0.0) == STRENGTH_NONE
        assert resolve_jaggedness(0.5) == STRENGTH_MEDIUM
        assert resolve_jaggedness(1.0) == STRENGTH_EXTREME

    def test_invalid_preset_raises_valueerror(self):
        with pytest.raises(ValueError):
            resolve_jaggedness("crazy")

    def test_out_of_range_numeric_raises_valueerror(self):
        with pytest.raises(ValueError):
            resolve_jaggedness(-0.1)
        with pytest.raises(ValueError):
            resolve_jaggedness(1.5)

    def test_boolean_raises_valueerror(self):
        with pytest.raises(ValueError):
            resolve_jaggedness(True)

    def test_numeric_string_raises_valueerror(self):
        with pytest.raises(ValueError):
            resolve_jaggedness("0.5")


class TestResolveAccelerandoFinalDurationMultiplier:
    def test_strength_none_returns_neutral(self):
        assert _resolve_accelerando_final_duration_multiplier(STRENGTH_NONE) == 1.0

    def test_strength_extreme_returns_minimum_ratio(self):
        multiplier = _resolve_accelerando_final_duration_multiplier(STRENGTH_EXTREME)
        assert 0.0 < multiplier <= 0.10

    def test_strength_medium_returns_multiplier_between_neutral_and_minimum(self):
        multiplier = _resolve_accelerando_final_duration_multiplier(STRENGTH_MEDIUM)
        assert 0.10 < multiplier < 1.0

    def test_higher_strength_produces_shorter_durations(self):
        final_duration_multiplier_low_strength = _resolve_accelerando_final_duration_multiplier(STRENGTH_LOW)
        final_duration_multiplier_high_strength = _resolve_accelerando_final_duration_multiplier(STRENGTH_HIGH)
        assert final_duration_multiplier_low_strength > final_duration_multiplier_high_strength


class TestResolveRitardandoFinalDurationMultiplier:
    def test_strength_none_returns_neutral(self):
        assert _resolve_ritardando_final_duration_multiplier(STRENGTH_NONE) == 1.0

    def test_strength_extreme_returns_maximum_ratio(self):
        multiplier = _resolve_ritardando_final_duration_multiplier(STRENGTH_EXTREME)
        assert multiplier == 4.0

    def test_strength_medium_returns_multiplier_between_neutral_and_maximum(self):
        multiplier = _resolve_ritardando_final_duration_multiplier(STRENGTH_MEDIUM)
        assert 1.0 < multiplier < 4.0

    def test_higher_strength_produces_longer_durations(self):
        final_duration_multiplier_low_strength = _resolve_ritardando_final_duration_multiplier(STRENGTH_LOW)
        final_duration_multiplier_high_strength = _resolve_ritardando_final_duration_multiplier(STRENGTH_HIGH)
        assert final_duration_multiplier_low_strength < final_duration_multiplier_high_strength


class TestComputeTempoChangeFactors:
    def test_empty_returns_empty(self):
        assert _compute_tempo_change_factors(0, 1.0, 0.5) == []

    def test_single_tone_returns_neutral_factor(self):
        assert _compute_tempo_change_factors(1, 1.0, 0.5) == [1.0]

    def test_first_factor_is_start_factor(self):
        factors = _compute_tempo_change_factors(5, 1.0, 0.5)
        assert factors[0] == 1.0

    def test_last_factor_is_end_factor(self):
        factors = _compute_tempo_change_factors(5, 1.0, 0.5)
        assert factors[-1] == 0.5

    def test_strength_none_all_factors_are_neutral(self):
        factors = _compute_tempo_change_factors(5, 1.0, 1.0)
        assert all(f == 1.0 for f in factors)

    def test_factors_inbetween_are_linearly_interpolated(self):
        factors = _compute_tempo_change_factors(3, 1.0, 0.7)
        assert factors[0] == 1.0
        assert factors[1] == pytest.approx(0.85)
        assert factors[2] == 0.7


class TestAccelerandoTransform:
    def test_empty_phrase_returns_empty(self):
        assert accelerando_transform([]) == []

    def test_single_tone_unchanged(self):
        tone = Tone(frequency=440.0, duration=1.0)
        result = accelerando_transform([tone])
        assert len(result) == 1
        assert result[0].duration == 1.0
        assert result[0].frequency == 440.0

    def test_durations_decrease_across_phrase(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(5)]
        result = accelerando_transform(tones, strength="medium", jaggedness="none")
        for i in range(1, len(result)):
            assert result[i].duration < result[i - 1].duration

    def test_uneven_durations_scaled_proportionally(self):
        tones = [
            Tone(frequency=440.0, duration=2.0),
            Tone(frequency=440.0, duration=1.0),
            Tone(frequency=440.0, duration=0.5),
        ]
        result = accelerando_transform(tones, strength="high", jaggedness="none")
        assert result[0].duration == 2.0

        final_multiplier = _resolve_accelerando_final_duration_multiplier(STRENGTH_HIGH)
        multiplier_at_position_1 = _interpolate_multiplier_at_position(
            position_index=1, total_tones=len(tones), start_multiplier=1.0, end_multiplier=final_multiplier
        )
        expected_second_duration = tones[1].duration * multiplier_at_position_1
        assert result[1].duration == pytest.approx(expected_second_duration)

    def test_preserves_frequency_sample_rate_and_amplitude(self):
        tones = [Tone(frequency=440.0, duration=1.0, sample_rate=44100, amplitude=0.8)]
        result = accelerando_transform(tones, strength="high", jaggedness="none")
        assert result[0].frequency == 440.0
        assert result[0].sample_rate == 44100
        assert result[0].amplitude == 0.8

    def test_first_tone_duration_unchanged(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(5)]
        result = accelerando_transform(tones, strength="high", jaggedness="none")
        assert result[0].duration == 1.0


class TestRitardandoTransform:
    def test_empty_phrase_returns_empty(self):
        assert ritardando_transform([]) == []

    def test_single_tone_unchanged(self):
        tone = Tone(frequency=440.0, duration=1.0)
        result = ritardando_transform([tone])
        assert len(result) == 1
        assert result[0].duration == 1.0
        assert result[0].frequency == 440.0

    def test_durations_increase_across_phrase(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(5)]
        result = ritardando_transform(tones, strength="medium", jaggedness="none")
        for i in range(1, len(result)):
            assert result[i].duration > result[i - 1].duration

    def test_uneven_durations_scaled_proportionally(self):
        tones = [
            Tone(frequency=440.0, duration=1.0),
            Tone(frequency=440.0, duration=0.5),
            Tone(frequency=440.0, duration=0.25),
        ]
        result = ritardando_transform(tones, strength="high", jaggedness="none")
        assert result[0].duration == 1.0

        final_multiplier = _resolve_ritardando_final_duration_multiplier(STRENGTH_HIGH)
        multiplier_for_second_tone = _interpolate_multiplier_at_position(
            position_index=1, total_tones=len(tones), start_multiplier=1.0, end_multiplier=final_multiplier
        )
        expected_second_duration = tones[1].duration * multiplier_for_second_tone
        assert result[1].duration == pytest.approx(expected_second_duration)

    def test_preserves_frequency_sample_rate_and_amplitude(self):
        tones = [Tone(frequency=440.0, duration=1.0, sample_rate=44100, amplitude=0.8)]
        result = ritardando_transform(tones, strength="high", jaggedness="none")
        assert result[0].frequency == 440.0
        assert result[0].sample_rate == 44100
        assert result[0].amplitude == 0.8

    def test_first_tone_duration_unchanged(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(5)]
        result = ritardando_transform(tones, strength="high", jaggedness="none")
        assert result[0].duration == 1.0


class TestComputeJaggednessWeights:
    def test_empty_returns_empty(self):
        from transforms.duration import _compute_jaggedness_weights
        assert _compute_jaggedness_weights(0, 0.5) == []

    def test_jaggedness_none_all_weights_are_neutral(self):
        from transforms.duration import _compute_jaggedness_weights
        weights = _compute_jaggedness_weights(5, 0.0)
        assert all(w == 1.0 for w in weights)

    def test_high_jaggedness_produces_variation_with_seed(self):
        from transforms.duration import _compute_jaggedness_weights
        import random
        seed = 42
        weights = _compute_jaggedness_weights(5, 1.0, random.Random(seed))
        assert len(weights) == 5
        assert any(w != 1.0 for w in weights)
        
    def test_jaggedness_output_is_deterministic_with_same_seed(self):
        from transforms.duration import _compute_jaggedness_weights
        import random
        seed = 123
        weights_1 = _compute_jaggedness_weights(10, 0.5, random.Random(seed))
        weights_2 = _compute_jaggedness_weights(10, 0.5, random.Random(seed))
        assert weights_1 == weights_2


class TestJaggedTempoTransforms:
    def test_accelerando_with_jaggedness_can_produce_local_reversals(self):
        # We use a specific seed that is known to produce a local reversal 
        # (a later note being longer than a previous one) at high jaggedness.
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(5)]
        seed = 42 # Chosen via experimentation to trigger reversal
        
        result = accelerando_transform(tones, strength="low", jaggedness="extreme", seed=seed)
        
        # Check if any later tone is longer than the previous one
        reversals = []
        for i in range(1, len(result)):
            if result[i].duration > result[i-1].duration:
                reversals.append(i)
        
        assert len(reversals) > 0, "Extreme jaggedness should produce at least one local reversal with this seed."

    def test_ritardando_with_jaggedness_can_produce_local_reversals(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(5)]
        seed = 7 # Chosen to trigger reversal in ritardando
        
        result = ritardando_transform(tones, strength="low", jaggedness="extreme", seed=seed)
        
        # In ritardando, a reversal means a later tone is shorter than the previous one
        reversals = []
        for i in range(1, len(result)):
            if result[i].duration < result[i-1].duration:
                reversals.append(i)
                
        assert len(reversals) > 0, "Extreme jaggedness should produce at least one local reversal with this seed."

    def test_jaggedness_none_is_smooth(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(5)]
        
        result_accel = accelerando_transform(tones, strength="medium", jaggedness="none")
        for i in range(1, len(result_accel)):
            assert result_accel[i].duration < result_accel[i-1].duration
            
        result_rit = ritardando_transform(tones, strength="medium", jaggedness="none")
        for i in range(1, len(result_rit)):
            assert result_rit[i].duration > result_rit[i-1].duration
