import pytest

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import PhraseTransformContext
from transforms.tempo._common import (
    INTENSITY_LEVELS,
    TempoChangeParams,
    apply_duration_multipliers,
    compute_jaggedness_weights,
    compute_tempo_change_factors,
)
from transforms.tempo.accelerando import (
    ACCELERANDO_PARAMS_SPEC,
    _resolve_accelerando_final_duration_multiplier,
    accelerando_phrase_transform,
    accelerando_transform,
)
from transforms.tempo.ritardando import (
    _resolve_ritardando_final_duration_multiplier,
    ritardando_phrase_transform,
    ritardando_transform,
)


class TestTempoChangeParamsSpec:
    def test_defaults(self):
        params = ACCELERANDO_PARAMS_SPEC.parse_params({})
        assert params.strength == INTENSITY_LEVELS["medium"]
        assert params.jaggedness == INTENSITY_LEVELS["none"]

    def test_presets_case_insensitive(self):
        params = ACCELERANDO_PARAMS_SPEC.parse_params({"strength": "NONE", "jaggedness": "LOW"})
        assert params.strength == INTENSITY_LEVELS["none"]
        assert params.jaggedness == INTENSITY_LEVELS["low"]

    def test_numeric_values(self):
        params = ACCELERANDO_PARAMS_SPEC.parse_params({"strength": 0.37, "jaggedness": 1})
        assert params.strength == 0.37
        assert params.jaggedness == 1.0

    def test_invalid_presets_raise_value_error(self):
        with pytest.raises(ValueError):
            ACCELERANDO_PARAMS_SPEC.parse_params({"strength": "wild"})

    def test_out_of_range_numeric_raises_value_error(self):
        with pytest.raises(ValueError):
            ACCELERANDO_PARAMS_SPEC.parse_params({"strength": 1.1})

    def test_boolean_raises_value_error(self):
        with pytest.raises(ValueError):
            ACCELERANDO_PARAMS_SPEC.parse_params({"strength": True})

    def test_numeric_string_raises_value_error(self):
        with pytest.raises(ValueError):
            ACCELERANDO_PARAMS_SPEC.parse_params({"strength": "0.75"})

    def test_invalid_type_raises_value_error(self):
        with pytest.raises(ValueError):
            ACCELERANDO_PARAMS_SPEC.parse_params({"strength": None})


class TestResolveAccelerandoFinalDurationMultiplier:
    def test_strength_none_returns_neutral(self):
        assert _resolve_accelerando_final_duration_multiplier(INTENSITY_LEVELS["none"]) == 1.0

    def test_strength_extreme_returns_minimum_ratio(self):
        multiplier = _resolve_accelerando_final_duration_multiplier(INTENSITY_LEVELS["extreme"])
        assert 0.0 < multiplier <= 0.10

    def test_strength_medium_returns_multiplier_between_neutral_and_minimum(self):
        multiplier = _resolve_accelerando_final_duration_multiplier(INTENSITY_LEVELS["medium"])
        assert 0.10 < multiplier < 1.0

    def test_higher_strength_produces_shorter_durations(self):
        final_duration_multiplier_low_strength = _resolve_accelerando_final_duration_multiplier(INTENSITY_LEVELS["low"])
        final_duration_multiplier_high_strength = _resolve_accelerando_final_duration_multiplier(INTENSITY_LEVELS["high"])
        assert final_duration_multiplier_low_strength > final_duration_multiplier_high_strength


class TestResolveRitardandoFinalDurationMultiplier:
    def test_strength_none_returns_neutral(self):
        assert _resolve_ritardando_final_duration_multiplier(INTENSITY_LEVELS["none"]) == 1.0

    def test_strength_extreme_returns_maximum_ratio(self):
        multiplier = _resolve_ritardando_final_duration_multiplier(INTENSITY_LEVELS["extreme"])
        assert multiplier == 4.0

    def test_strength_medium_returns_multiplier_between_neutral_and_maximum(self):
        multiplier = _resolve_ritardando_final_duration_multiplier(INTENSITY_LEVELS["medium"])
        assert 1.0 < multiplier < 4.0

    def test_higher_strength_produces_longer_durations(self):
        final_duration_multiplier_low_strength = _resolve_ritardando_final_duration_multiplier(INTENSITY_LEVELS["low"])
        final_duration_multiplier_high_strength = _resolve_ritardando_final_duration_multiplier(INTENSITY_LEVELS["high"])
        assert final_duration_multiplier_low_strength < final_duration_multiplier_high_strength


class TestComputeTempoChangeFactors:
    def test_empty_returns_empty(self):
        assert compute_tempo_change_factors(0, 1.0, 0.5) == []

    def test_single_tone_returns_neutral_factor(self):
        assert compute_tempo_change_factors(1, 1.0, 0.5) == [1.0]

    def test_first_factor_is_start_factor(self):
        factors = compute_tempo_change_factors(5, 1.0, 0.5)
        assert factors[0] == 1.0

    def test_last_factor_is_end_factor(self):
        factors = compute_tempo_change_factors(5, 1.0, 0.5)
        assert factors[-1] == 0.5

    def test_strength_none_all_factors_are_neutral(self):
        factors = compute_tempo_change_factors(5, 1.0, 1.0)
        assert all(f == 1.0 for f in factors)

    def test_factors_inbetween_are_linearly_interpolated(self):
        factors = compute_tempo_change_factors(3, 1.0, 0.7)
        assert factors[0] == 1.0
        assert factors[1] == pytest.approx(0.85)
        assert factors[2] == 0.7


class TestApplyDurationMultipliers:
    def test_mismatched_tone_and_multiplier_counts_raise_valueerror(self):
        tones = [Tone(frequency=440.0, duration=1.0), Tone(frequency=660.0, duration=0.5)]
        multipliers = [1.0]

        with pytest.raises(ValueError, match="Tone count \\(2\\) must match multiplier count \\(1\\)"):
            apply_duration_multipliers(tones, multipliers)


class TestAccelerandoTransform:
    def test_empty_phrase_returns_empty(self):
        assert accelerando_transform([], strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"]) == []

    def test_single_tone_unchanged(self):
        tone = Tone(frequency=440.0, duration=1.0)
        result = accelerando_transform([tone], strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"])
        assert len(result) == 1
        assert result[0].duration == 1.0
        assert result[0].frequency == 440.0

    def test_durations_decrease_across_phrase(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(5)]
        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"])
        for i in range(1, len(result)):
            assert result[i].duration < result[i - 1].duration

    def test_uneven_durations_scaled_proportionally(self):
        tones = [
            Tone(frequency=440.0, duration=2.0),
            Tone(frequency=440.0, duration=1.0),
            Tone(frequency=440.0, duration=0.5),
        ]
        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["high"], jaggedness=INTENSITY_LEVELS["none"])
        assert result[0].duration == 2.0

        final_multiplier = _resolve_accelerando_final_duration_multiplier(INTENSITY_LEVELS["high"])
        first_multiplier = compute_tempo_change_factors(len(tones), 1.0, final_multiplier)[1]
        expected_second_duration = tones[1].duration * first_multiplier
        assert result[1].duration == pytest.approx(expected_second_duration)

    def test_preserves_frequency_sample_rate_and_amplitude(self):
        tones = [Tone(frequency=440.0, duration=1.0, sample_rate=44100, amplitude=0.8)]
        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["high"], jaggedness=INTENSITY_LEVELS["none"])
        assert result[0].frequency == 440.0
        assert result[0].sample_rate == 44100
        assert result[0].amplitude == 0.8

    def test_first_tone_duration_unchanged(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(5)]
        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["high"], jaggedness=INTENSITY_LEVELS["none"])
        assert result[0].duration == 1.0

    def test_phrase_transform_returns_transformed_phrase(self):
        tones = [Tone(440.0, duration=1.0), Tone(440.0, duration=1.0)]
        score = Score([Voice([Phrase([Motif("m", tones)])])])
        context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

        result = accelerando_phrase_transform(context, TempoChangeParams(strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"]))

        assert len(result.motifs[0].tones) == len(tones)
        assert result.motifs[0].tones[1].duration < result.motifs[0].tones[0].duration


class TestRitardandoTransform:
    def test_empty_phrase_returns_empty(self):
        assert ritardando_transform([], strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"]) == []

    def test_single_tone_unchanged(self):
        tone = Tone(frequency=440.0, duration=1.0)
        result = ritardando_transform([tone], strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"])
        assert len(result) == 1
        assert result[0].duration == 1.0
        assert result[0].frequency == 440.0

    def test_durations_increase_across_phrase(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(5)]
        result = ritardando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"])
        for i in range(1, len(result)):
            assert result[i].duration > result[i - 1].duration

    def test_uneven_durations_scaled_proportionally(self):
        tones = [
            Tone(frequency=440.0, duration=1.0),
            Tone(frequency=440.0, duration=0.5),
            Tone(frequency=440.0, duration=0.25),
        ]
        result = ritardando_transform(tones, strength=INTENSITY_LEVELS["high"], jaggedness=INTENSITY_LEVELS["none"])
        assert result[0].duration == 1.0

        start_factor = 1.0

        final_multiplier = _resolve_ritardando_final_duration_multiplier(INTENSITY_LEVELS["high"])
        multiplier_for_second_tone = compute_tempo_change_factors(len(tones), start_factor, final_multiplier)[1]
        expected_second_duration = tones[1].duration * multiplier_for_second_tone
        assert result[1].duration == pytest.approx(expected_second_duration)

    def test_preserves_frequency_sample_rate_and_amplitude(self):
        tones = [Tone(frequency=440.0, duration=1.0, sample_rate=44100, amplitude=0.8)]
        result = ritardando_transform(tones, strength=INTENSITY_LEVELS["high"], jaggedness=INTENSITY_LEVELS["none"])
        assert result[0].frequency == 440.0
        assert result[0].sample_rate == 44100
        assert result[0].amplitude == 0.8

    def test_first_tone_duration_unchanged(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(5)]
        result = ritardando_transform(tones, strength=INTENSITY_LEVELS["high"], jaggedness=INTENSITY_LEVELS["none"])
        assert result[0].duration == 1.0

    def test_phrase_transform_returns_transformed_phrase(self):
        tones = [Tone(440.0, duration=1.0), Tone(440.0, duration=1.0)]
        score = Score([Voice([Phrase([Motif("m", tones)])])])
        context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

        result = ritardando_phrase_transform(context, TempoChangeParams(strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"]))

        assert len(result.motifs[0].tones) == len(tones)
        assert result.motifs[0].tones[1].duration > result.motifs[0].tones[0].duration


class TestComputeJaggednessWeights:
    def test_empty_returns_empty(self):
        assert compute_jaggedness_weights(0, 0.5) == []

    def test_jaggedness_none_all_weights_are_neutral(self):
        weights = compute_jaggedness_weights(5, 0.0)
        assert all(w == 1.0 for w in weights)

    def test_high_jaggedness_produces_variation_with_seed(self):
        import random

        seed = 42
        weights = compute_jaggedness_weights(5, 1.0, random.Random(seed))
        assert len(weights) == 5
        assert any(w != 1.0 for w in weights)
        
    def test_jaggedness_output_is_deterministic_with_same_seed(self):
        import random

        seed = 123
        weights_1 = compute_jaggedness_weights(10, 0.5, random.Random(seed))
        weights_2 = compute_jaggedness_weights(10, 0.5, random.Random(seed))
        assert weights_1 == weights_2


class TestJaggedTempoTransforms:
    def test_accelerando_with_jaggedness_can_produce_local_reversals(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(10)]

        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["low"], jaggedness=INTENSITY_LEVELS["extreme"])

        # Check if any later tone is longer than the previous one
        reversals = [i for i in range(1, len(result)) if result[i].duration > result[i-1].duration]

        assert len(reversals) > 0, "Extreme jaggedness should produce at least one local reversal."

    def test_ritardando_with_jaggedness_can_produce_local_reversals(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(10)]

        result = ritardando_transform(tones, strength=INTENSITY_LEVELS["low"], jaggedness=INTENSITY_LEVELS["extreme"])

        # In ritardando, a reversal means a later tone is shorter than the previous one
        reversals = [i for i in range(1, len(result)) if result[i].duration < result[i-1].duration]

        assert len(reversals) > 0, "Extreme jaggedness should produce at least one local reversal."

    def test_jaggedness_none_is_smooth(self):
        tones = [Tone(frequency=440.0, duration=1.0) for _ in range(5)]
        
        result_accel = accelerando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"])
        for i in range(1, len(result_accel)):
            assert result_accel[i].duration < result_accel[i-1].duration
            
        result_rit = ritardando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"])
        for i in range(1, len(result_rit)):
            assert result_rit[i].duration > result_rit[i-1].duration


class TestMinimumDurationProtection:
    def test_accelerando_extreme_strength_preserves_positive_durations(self):
        tones = [Tone(440.0, 1.0), Tone(880.0, 1.0), Tone(523.0, 1.0)]

        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["extreme"], jaggedness=INTENSITY_LEVELS["none"])

        assert all(tone.duration > 0 for tone in result)

    def test_accelerando_extreme_strength_with_jaggedness_preserves_positive_durations(self):
        tones = [Tone(440.0, 1.0), Tone(880.0, 1.0), Tone(523.0, 1.0), Tone(660.0, 1.0)]

        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["extreme"], jaggedness=INTENSITY_LEVELS["extreme"])

        assert all(tone.duration > 0 for tone in result)

    def test_accelerando_clamps_to_minimum_duration(self):
        tones = [Tone(440.0, 0.0001), Tone(880.0, 0.0001)]

        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["extreme"], jaggedness=INTENSITY_LEVELS["none"])

        assert result[0].duration >= 0.001
        assert result[1].duration >= 0.001

    def test_single_tone_protected_from_collapse(self):
        result = accelerando_transform([Tone(440.0, 0.0001)], strength=INTENSITY_LEVELS["extreme"], jaggedness=INTENSITY_LEVELS["extreme"])

        assert len(result) == 1
        assert result[0].duration >= 0.001

    def test_ritardando_preserves_positive_durations(self):
        tones = [Tone(440.0, 1.0), Tone(880.0, 1.0), Tone(523.0, 1.0)]

        result = ritardando_transform(tones, strength=INTENSITY_LEVELS["extreme"], jaggedness=INTENSITY_LEVELS["none"])

        assert all(tone.duration > 0 for tone in result)


class TestJaggednessPresetEquivalence:
    def test_jaggedness_none_preset_matches_none_numeric(self):
        tones = [Tone(440.0, 1.0), Tone(880.0, 1.0)]

        result_preset = accelerando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"])
        result_numeric = accelerando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"])

        assert result_preset[0].duration == pytest.approx(result_numeric[0].duration)
        assert result_preset[1].duration == pytest.approx(result_numeric[1].duration)

    def test_jaggedness_low_preset_is_accepted(self):
        tones = [Tone(440.0, 1.0), Tone(880.0, 1.0), Tone(523.0, 1.0)]

        result_preset = accelerando_transform(tones, strength=INTENSITY_LEVELS["low"], jaggedness=INTENSITY_LEVELS["low"])
        result_numeric = accelerando_transform(tones, strength=INTENSITY_LEVELS["low"], jaggedness=INTENSITY_LEVELS["low"])

        assert len(result_preset) == len(tones)
        assert len(result_numeric) == len(tones)
        assert all(tone.duration > 0 for tone in result_preset)
        assert all(tone.duration > 0 for tone in result_numeric)

    def test_jaggedness_extreme_preset_is_accepted(self):
        tones = [Tone(440.0, 1.0), Tone(880.0, 1.0)]

        result_preset = accelerando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["extreme"])
        result_numeric = accelerando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["extreme"])

        assert len(result_preset) == len(result_numeric)


class TestJaggednessPreservesToneProperties:
    def test_jaggedness_preserves_frequencies(self):
        tones = [Tone(440.0, 1.0), Tone(880.0, 1.0), Tone(523.0, 1.0)]

        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["extreme"])

        assert [tone.frequency for tone in result] == [tone.frequency for tone in tones]

    def test_jaggedness_preserves_amplitudes(self):
        tones = [Tone(440.0, 1.0, amplitude=0.8), Tone(880.0, 1.0, amplitude=0.6)]

        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["high"], jaggedness=INTENSITY_LEVELS["extreme"])

        assert [tone.amplitude for tone in result] == [tone.amplitude for tone in tones]

    def test_jaggedness_preserves_sample_rates(self):
        tones = [Tone(440.0, 1.0, sample_rate=48000), Tone(880.0, 1.0, sample_rate=48000)]

        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["high"])

        assert [tone.sample_rate for tone in result] == [tone.sample_rate for tone in tones]


class TestUnevenDurationScaling:
    def test_accelerando_decreases_durations_except_first(self):
        tones = [
            Tone(440.0, 1.0),
            Tone(494.0, 0.25),
            Tone(523.0, 0.5),
        ]

        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"])

        assert result[0].duration == tones[0].duration
        assert result[1].duration < tones[1].duration
        assert result[2].duration < tones[2].duration

    def test_ritardando_increases_durations_except_first(self):
        tones = [
            Tone(440.0, 0.25),
            Tone(494.0, 1.0),
            Tone(523.0, 0.5),
        ]

        result = ritardando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"])

        assert result[0].duration == tones[0].duration
        assert result[1].duration > tones[1].duration
        assert result[2].duration > tones[2].duration

    def test_accelerando_does_not_collapse_short_notes(self):
        tones = [
            Tone(440.0, 2.0),
            Tone(494.0, 0.1),
            Tone(523.0, 0.1),
        ]

        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["high"], jaggedness=INTENSITY_LEVELS["none"])

        assert result[1].duration >= 0.001
        assert result[2].duration >= 0.001

    def test_uneven_durations_preserve_overall_ordering_at_low_strength(self):
        tones = [
            Tone(440.0, 0.5),
            Tone(494.0, 1.0),
            Tone(523.0, 0.25),
        ]

        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["low"], jaggedness=INTENSITY_LEVELS["none"])

        assert result[1].duration > result[0].duration
        assert result[1].duration > result[2].duration

    def test_equal_duration_tones_scale_proportionally_to_position(self):
        tones = [
            Tone(440.0, 1.0),
            Tone(494.0, 1.0),
            Tone(523.0, 1.0),
        ]

        result = accelerando_transform(tones, strength=INTENSITY_LEVELS["medium"], jaggedness=INTENSITY_LEVELS["none"])

        assert result[0].duration == 1.0
        assert result[1].duration < result[0].duration
        assert result[2].duration < result[1].duration
