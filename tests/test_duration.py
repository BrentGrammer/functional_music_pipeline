import sys
import os
import pytest
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from transforms.duration import (
    _interpolate_multiplier_at_position,
    feigenbaum_sequence,
    score_feigenbaum_sequence,
    phrase_feigenbaum_shrink,
    phrase_feigenbaum_grow,
    accelerando_transform,
    ritardando_transform,
    resolve_strength,
    resolve_jaggedness,
    STRENGTH_NONE,
    STRENGTH_LOW,
    STRENGTH_MEDIUM,
    STRENGTH_HIGH,
    STRENGTH_EXTREME,
)
from score_model.math_constants import FEIGENBAUM_DELTA
from score_model.tone import Tone
from score_model.voice import Voice
from score_model.score import Score
from transforms.base import ToneDimension

class TestFeigenbaumDurationSequence:
    def test_feigenbaum_duration(self):
        tones = [Tone(440, 1.0), Tone(880, 1.0), Tone(523, 1.0)]
        result = feigenbaum_sequence(tones)
        
        assert len(result) == 3
        assert result[0].duration == 1.0
        assert result[1].duration == pytest.approx(1.0 / FEIGENBAUM_DELTA)
        assert result[2].duration == pytest.approx((1.0 / FEIGENBAUM_DELTA) / FEIGENBAUM_DELTA)

    def test_feigenbaum_amplitude(self):
        tones = [Tone(440, amplitude=1.0), Tone(880, amplitude=1.0)]
        result = feigenbaum_sequence(tones, dimension=ToneDimension.AMPLITUDE)
        
        assert result[0].amplitude == 1.0
        assert result[1].amplitude == pytest.approx(1.0 / FEIGENBAUM_DELTA)

class TestPhraseFeigenbaumShrink:
    def test_relative_scale(self):
        first_phrase_total_duration = 1.0
        first_phrase = [Tone(440, duration=first_phrase_total_duration)]
        
        second_phrase_tone_duration = 1.0
        second_phrase = [Tone(880, duration=second_phrase_tone_duration), Tone(523, duration=second_phrase_tone_duration)]
        
        transformed_second_phrase = phrase_feigenbaum_shrink(second_phrase, first_phrase)
        
        expected_total_duration = first_phrase_total_duration / FEIGENBAUM_DELTA
        actual_total_duration = sum(t.duration for t in transformed_second_phrase)
        
        assert actual_total_duration == pytest.approx(expected_total_duration)
        
        expected_duration_per_tone = expected_total_duration / 2
        assert transformed_second_phrase[0].duration == pytest.approx(expected_duration_per_tone)
        assert transformed_second_phrase[1].duration == pytest.approx(expected_duration_per_tone)

    def test_empty_previous(self):
        second_phrase = [Tone(880, 1.0)]
        with pytest.raises(ValueError, match="Cannot apply phrase-feigenbaum-shrink: no preceding phrases exist to relate to."):
            phrase_feigenbaum_shrink(second_phrase, [])

    def test_empty_current_phrase_returns_empty_list(self):
        reference_frequency = 440.0
        reference_duration = 1.0
        previous_phrase = [Tone(reference_frequency, duration=reference_duration)]

        assert phrase_feigenbaum_shrink([], previous_phrase) == []

    def test_zero_current_total_returns_original_tones(self):
        reference_frequency = 440.0
        reference_duration = 1.0
        zero_duration_seconds = 0.0
        first_current_frequency = 880.0
        second_current_frequency = 523.0
        previous_phrase = [Tone(reference_frequency, duration=reference_duration)]
        zero_duration_phrase = [
            Tone(first_current_frequency, duration=zero_duration_seconds),
            Tone(second_current_frequency, duration=zero_duration_seconds),
        ]

        result = phrase_feigenbaum_shrink(zero_duration_phrase, previous_phrase)

        assert result is zero_duration_phrase

    def test_zero_previous_total_returns_original_tones(self):
        reference_frequency = 440.0
        zero_duration_seconds = 0.0
        current_frequency = 880.0
        current_duration = 1.0
        zero_duration_previous_phrase = [Tone(reference_frequency, duration=zero_duration_seconds)]
        current_phrase = [Tone(current_frequency, duration=current_duration)]

        result = phrase_feigenbaum_shrink(current_phrase, zero_duration_previous_phrase)

        assert result is current_phrase

    def test_relative_scale_on_amplitude_dimension(self):
        previous_total_amplitude = 0.6
        first_current_frequency = 880.0
        second_current_frequency = 523.0
        current_tone_amplitude = 0.3
        previous_phrase = [Tone(440.0, amplitude=previous_total_amplitude)]
        current_phrase = [
            Tone(first_current_frequency, amplitude=current_tone_amplitude),
            Tone(second_current_frequency, amplitude=current_tone_amplitude),
        ]

        transformed_phrase = phrase_feigenbaum_shrink(
            current_phrase,
            previous_phrase,
            dimension="AMPLITUDE",
        )

        expected_total_amplitude = previous_total_amplitude / FEIGENBAUM_DELTA
        actual_total_amplitude = sum(tone.amplitude for tone in transformed_phrase)

        assert actual_total_amplitude == pytest.approx(expected_total_amplitude)

class TestPhraseFeigenbaumGrow:
    def test_inverse_relative_scale(self):
        first_phrase_total_duration = 1.0
        first_phrase = [Tone(440, duration=first_phrase_total_duration)]
        
        second_phrase_tone_duration = 1.0
        second_phrase = [Tone(880, duration=second_phrase_tone_duration), Tone(523, duration=second_phrase_tone_duration)]
        
        transformed_second_phrase = phrase_feigenbaum_grow(second_phrase, first_phrase)
        
        expected_total_duration = first_phrase_total_duration * FEIGENBAUM_DELTA
        actual_total_duration = sum(t.duration for t in transformed_second_phrase)
        
        assert actual_total_duration == pytest.approx(expected_total_duration)
        
        expected_duration_per_tone = expected_total_duration / 2
        assert transformed_second_phrase[0].duration == pytest.approx(expected_duration_per_tone)
        assert transformed_second_phrase[1].duration == pytest.approx(expected_duration_per_tone)

    def test_empty_previous(self):
        second_phrase = [Tone(880, 1.0)]
        with pytest.raises(ValueError, match="Cannot apply phrase-feigenbaum-grow: no preceding phrases exist to relate to."):
            phrase_feigenbaum_grow(second_phrase, [])

    def test_empty_current_phrase_returns_empty_list(self):
        reference_frequency = 440.0
        reference_duration = 1.0
        previous_phrase = [Tone(reference_frequency, duration=reference_duration)]

        assert phrase_feigenbaum_grow([], previous_phrase) == []

    def test_zero_current_total_returns_original_tones(self):
        reference_frequency = 440.0
        reference_duration = 1.0
        zero_duration_seconds = 0.0
        first_current_frequency = 880.0
        second_current_frequency = 523.0
        previous_phrase = [Tone(reference_frequency, duration=reference_duration)]
        zero_duration_phrase = [
            Tone(first_current_frequency, duration=zero_duration_seconds),
            Tone(second_current_frequency, duration=zero_duration_seconds),
        ]

        result = phrase_feigenbaum_grow(zero_duration_phrase, previous_phrase)

        assert result is zero_duration_phrase

    def test_zero_previous_total_returns_original_tones(self):
        reference_frequency = 440.0
        zero_duration_seconds = 0.0
        current_frequency = 880.0
        current_duration = 1.0
        zero_duration_previous_phrase = [Tone(reference_frequency, duration=zero_duration_seconds)]
        current_phrase = [Tone(current_frequency, duration=current_duration)]

        result = phrase_feigenbaum_grow(current_phrase, zero_duration_previous_phrase)

        assert result is current_phrase

    def test_relative_scale_on_frequency_dimension(self):
        previous_total_frequency = 440.0
        reference_duration = 1.0
        current_tone_frequency = 220.0
        current_tone_duration = 1.0
        previous_phrase = [Tone(previous_total_frequency, duration=reference_duration)]
        current_phrase = [
            Tone(current_tone_frequency, duration=current_tone_duration),
            Tone(current_tone_frequency, duration=current_tone_duration),
        ]

        transformed_phrase = phrase_feigenbaum_grow(
            current_phrase,
            previous_phrase,
            dimension="FREQUENCY",
        )

        expected_total_frequency = previous_total_frequency * FEIGENBAUM_DELTA
        actual_total_frequency = sum(tone.frequency for tone in transformed_phrase)

        assert actual_total_frequency == pytest.approx(expected_total_frequency)

class TestScoreFeigenbaumDuration:
    def test_score_feigenbaum_duration(self):
        v1 = Voice([Tone(440, 1.0)])
        v2 = Voice([Tone(880, 1.0)])
        v3 = Voice([Tone(523, 1.0)])
        score = Score([v1, v2, v3])
        
        result_score = score_feigenbaum_sequence(score)
        
        assert len(result_score.voices) == 3
        assert result_score.voices[0][0].duration == 1.0
        assert result_score.voices[1][0].duration == pytest.approx(1.0 / FEIGENBAUM_DELTA)
        assert result_score.voices[2][0].duration == pytest.approx((1.0 / FEIGENBAUM_DELTA) / FEIGENBAUM_DELTA)

    def test_empty_score_returns_original_score(self):
        empty_score = Score()

        result = score_feigenbaum_sequence(empty_score)

        assert result is empty_score

    def test_single_voice_score_raises_error(self):
        reference_frequency = 440.0
        reference_duration = 1.0
        single_voice_score = Score([Voice([Tone(reference_frequency, duration=reference_duration)])])

        with pytest.raises(ValueError, match="requires at least 2 voices"):
            score_feigenbaum_sequence(single_voice_score)

    def test_score_feigenbaum_frequency_scales_each_voice_by_position(self):
        reference_frequency = 440.0
        reference_duration = 1.0
        first_voice = Voice([Tone(reference_frequency, duration=reference_duration)])
        second_voice = Voice([Tone(reference_frequency, duration=reference_duration)])
        score = Score([first_voice, second_voice])

        result = score_feigenbaum_sequence(score, dimension="FREQUENCY")

        assert result.voices[0][0].frequency == pytest.approx(reference_frequency)
        assert result.voices[1][0].frequency == pytest.approx(reference_frequency / FEIGENBAUM_DELTA)


class TestFeigenbaumTempoHelpers:
    def test_interpolate_multiplier_for_single_tone_returns_neutral(self):
        first_tone_position = 0
        single_tone_count = 1
        neutral_start_multiplier = 1.0
        ending_accelerando_multiplier = 0.1
        neutral_multiplier = _interpolate_multiplier_at_position(
            position_index=first_tone_position,
            total_tones=single_tone_count,
            start_multiplier=neutral_start_multiplier,
            end_multiplier=ending_accelerando_multiplier,
        )

        assert neutral_multiplier == neutral_start_multiplier

    def test_feigenbaum_frequency_clamps_to_minimum_positive_frequency(self):
        sub_minimum_frequency = 0.5
        reference_duration = 1.0
        minimum_allowed_frequency = 1.0
        tones = [
            Tone(sub_minimum_frequency, reference_duration),
            Tone(sub_minimum_frequency, reference_duration),
        ]

        result = feigenbaum_sequence(tones, dimension=ToneDimension.FREQUENCY)

        assert result[1].frequency == minimum_allowed_frequency


class TestMinimumDurationProtection:
    """
    Durations should not become negative or collapse to zero.
    Very short but audible durations may be allowed.
    """

    def test_accelerando_extreme_strength_preserves_positive_durations(self):
        tones = [Tone(440, 1.0), Tone(880, 1.0), Tone(523, 1.0)]
        result = accelerando_transform(tones, strength="extreme", jaggedness="none")

        for tone in result:
            assert tone.duration > 0

    def test_accelerando_extreme_strength_with_jaggedness_preserves_positive_durations(self):
        tones = [Tone(440, 1.0), Tone(880, 1.0), Tone(523, 1.0), Tone(660, 1.0)]
        result = accelerando_transform(tones, strength="extreme", jaggedness="extreme")

        for tone in result:
            assert tone.duration > 0

    def test_accelerando_clamps_to_minimum_duration(self):
        tones = [Tone(440, 0.0001), Tone(880, 0.0001)]
        result = accelerando_transform(tones, strength="extreme", jaggedness="none")

        assert result[0].duration >= 0.001
        assert result[1].duration >= 0.001

    def test_single_tone_protected_from_collapse(self):
        tone = Tone(440, 0.0001)
        result = accelerando_transform([tone], strength="extreme", jaggedness="extreme")

        assert len(result) == 1
        assert result[0].duration >= 0.001

    def test_ritardando_preserves_positive_durations(self):
        tones = [Tone(440, 1.0), Tone(880, 1.0), Tone(523, 1.0)]
        result = ritardando_transform(tones, strength="extreme", jaggedness="none")

        for tone in result:
            assert tone.duration > 0


class TestLocalReversals:
    """
    High jaggedness should create local duration reversals:
    - Accelerando: a later tone can be longer than an earlier tone
    - Ritardando: a later tone can be shorter than an earlier tone
    """

    def test_accelerando_with_high_jaggedness_can_produce_local_reversal(self):
        """
        With enough tones and extreme jaggedness, at least one pair of adjacent
        tones should have a reversal (later tone longer than earlier tone)
        despite the overall accelerando trend.
        """
        random.seed(12345)
        tones = [Tone(440 + i * 100, 1.0) for i in range(20)]

        for _ in range(10):
            result = accelerando_transform(tones, strength="high", jaggedness="extreme")
            durations = [t.duration for t in result]

            for i in range(len(durations) - 1):
                if durations[i + 1] > durations[i]:
                    return

        pytest.fail("No local reversal found after 10 attempts with high jaggedness")

    def test_ritardando_with_high_jaggedness_can_produce_local_reversal(self):
        """
        With enough tones and extreme jaggedness, at least one pair of adjacent
        tones should have a reversal (later tone shorter than earlier tone)
        despite the overall ritardando trend.
        """
        random.seed(54321)
        tones = [Tone(440 + i * 100, 1.0) for i in range(20)]

        for _ in range(10):
            result = ritardando_transform(tones, strength="high", jaggedness="extreme")
            durations = [t.duration for t in result]

            for i in range(len(durations) - 1):
                if durations[i + 1] < durations[i]:
                    return

        pytest.fail("No local reversal found after 10 attempts with high jaggedness")

    def test_smooth_accelerando_never_reverses(self):
        """With jaggedness=none, accelerando should always produce decreasing durations."""
        tones = [Tone(440 + i * 100, 1.0) for i in range(10)]
        result = accelerando_transform(tones, strength="medium", jaggedness="none")
        durations = [t.duration for t in result]

        for i in range(len(durations) - 1):
            assert durations[i + 1] <= durations[i]

    def test_smooth_ritardando_never_reverses(self):
        """With jaggedness=none, ritardando should always produce increasing durations."""
        tones = [Tone(440 + i * 100, 1.0) for i in range(10)]
        result = ritardando_transform(tones, strength="medium", jaggedness="none")
        durations = [t.duration for t in result]

        for i in range(len(durations) - 1):
            assert durations[i + 1] >= durations[i]


class TestJaggednessPresetEquivalence:
    """
    Tests that preset strings and numeric values resolve correctly.

    Note: Direct output comparison is only valid for jaggedness=none (deterministic).
    For non-zero jaggedness, the stochastic weights produce different results
    on each call, so we only verify that both preset and numeric forms
    are accepted and produce valid output.
    """

    def test_jaggedness_none_preset_matches_none_numeric(self):
        tones = [Tone(440, 1.0), Tone(880, 1.0)]
        result_preset = accelerando_transform(tones, strength="medium", jaggedness="none")
        result_numeric = accelerando_transform(tones, strength="medium", jaggedness=STRENGTH_NONE)

        assert result_preset[0].duration == pytest.approx(result_numeric[0].duration)
        assert result_preset[1].duration == pytest.approx(result_numeric[1].duration)

    def test_jaggedness_low_preset_is_accepted(self):
        tones = [Tone(440, 1.0), Tone(880, 1.0), Tone(523, 1.0)]
        result_preset = accelerando_transform(tones, strength="low", jaggedness="low")
        result_numeric = accelerando_transform(tones, strength="low", jaggedness=STRENGTH_LOW)

        assert len(result_preset) == len(tones)
        assert len(result_numeric) == len(tones)
        for tone in result_preset:
            assert tone.duration > 0
        for tone in result_numeric:
            assert tone.duration > 0

    def test_jaggedness_extreme_preset_is_accepted(self):
        tones = [Tone(440, 1.0), Tone(880, 1.0)]
        result_preset = accelerando_transform(tones, strength="medium", jaggedness="extreme")
        result_numeric = accelerando_transform(tones, strength="medium", jaggedness=STRENGTH_EXTREME)

        assert len(result_preset) == len(result_numeric)


class TestJaggednessPreservesToneProperties:
    """Tests that jaggedness preserves non-duration tone properties."""

    def test_jaggedness_preserves_frequencies(self):
        tones = [Tone(440, 1.0), Tone(880, 1.0), Tone(523, 1.0)]
        result = accelerando_transform(tones, strength="medium", jaggedness="extreme")

        assert result[0].frequency == tones[0].frequency
        assert result[1].frequency == tones[1].frequency
        assert result[2].frequency == tones[2].frequency

    def test_jaggedness_preserves_amplitudes(self):
        tones = [Tone(440, 1.0, amplitude=0.8), Tone(880, 1.0, amplitude=0.6)]
        result = accelerando_transform(tones, strength="high", jaggedness="extreme")

        assert result[0].amplitude == tones[0].amplitude
        assert result[1].amplitude == tones[1].amplitude

    def test_jaggedness_preserves_sample_rates(self):
        tones = [Tone(440, 1.0, sample_rate=48000), Tone(880, 1.0, sample_rate=48000)]
        result = accelerando_transform(tones, strength="medium", jaggedness="high")

        assert result[0].sample_rate == tones[0].sample_rate
        assert result[1].sample_rate == tones[1].sample_rate


class TestUnevenDurationProportionalScaling:
    """
    Tests for uneven input durations under tempo transforms.

    The transforms apply position-varying trend factors, which intentionally
    change duration ratios between tones. These tests verify that:
    - Short notes don't collapse to inaudible durations
    - The overall tempo direction is preserved
    - Tones with equal duration at adjacent positions maintain similar durations
    """

    def test_accelerando_decreases_durations_except_first(self):
        tones = [
            Tone(440, 1.0),
            Tone(494, 0.25),
            Tone(523, 0.5),
        ]
        result = accelerando_transform(tones, strength="medium", jaggedness="none")

        # First tone stays at 1.0 (trend develops across the phrase)
        assert result[0].duration == tones[0].duration
        # Later tones decrease (accelerando effect)
        assert result[1].duration < tones[1].duration
        assert result[2].duration < tones[2].duration

    def test_ritardando_increases_durations_except_first(self):
        tones = [
            Tone(440, 0.25),
            Tone(494, 1.0),
            Tone(523, 0.5),
        ]
        result = ritardando_transform(tones, strength="medium", jaggedness="none")

        # First tone stays at 1.0 (trend develops across the phrase)
        assert result[0].duration == tones[0].duration
        # Later tones increase (ritardando effect)
        assert result[1].duration > tones[1].duration
        assert result[2].duration > tones[2].duration

    def test_accelerando_does_not_collapse_short_notes(self):
        tones = [
            Tone(440, 2.0),
            Tone(494, 0.1),
            Tone(523, 0.1),
        ]
        result = accelerando_transform(tones, strength="high", jaggedness="none")

        # Short notes should remain audible
        assert result[1].duration >= 0.001
        assert result[2].duration >= 0.001

    def test_uneven_durations_preserve_overall_ordering_at_low_strength(self):
        tones = [
            Tone(440, 0.5),
            Tone(494, 1.0),
            Tone(523, 0.25),
        ]
        result = accelerando_transform(tones, strength="low", jaggedness="none")

        # At low strength, the longest tone should still be longest
        # (trend factors are close to 1.0, so original ordering mostly preserved)
        assert result[1].duration > result[0].duration
        assert result[1].duration > result[2].duration

    def test_equal_duration_tones_scale_proportionally_to_position(self):
        tones = [
            Tone(440, 1.0),
            Tone(494, 1.0),
            Tone(523, 1.0),
        ]
        result = accelerando_transform(tones, strength="medium", jaggedness="none")

        # All tones start with equal duration (1.0)
        # After transform, durations reflect their position in the accelerando curve:
        # - Position 0: factor 1.0 (no change)
        # - Position 1: factor ~0.55 (midway)
        # - Position 2: factor ~0.10 (end)
        assert result[0].duration == 1.0
        assert result[1].duration < result[0].duration
        assert result[2].duration < result[1].duration


class TestStrengthResolver:
    """Tests for the resolve_strength function."""

    def test_preset_strings_resolve_correctly(self):
        assert resolve_strength("none") == STRENGTH_NONE
        assert resolve_strength("low") == STRENGTH_LOW
        assert resolve_strength("medium") == STRENGTH_MEDIUM
        assert resolve_strength("high") == STRENGTH_HIGH
        assert resolve_strength("extreme") == STRENGTH_EXTREME

    def test_presets_are_case_insensitive(self):
        assert resolve_strength("NONE") == STRENGTH_NONE
        assert resolve_strength("Low") == STRENGTH_LOW
        assert resolve_strength("MEDIUM") == STRENGTH_MEDIUM
        assert resolve_strength("High") == STRENGTH_HIGH
        assert resolve_strength("EXTREME") == STRENGTH_EXTREME

    def test_numeric_values_resolve_correctly(self):
        assert resolve_strength(0.0) == 0.0
        assert resolve_strength(0.5) == 0.5
        assert resolve_strength(1.0) == 1.0
        assert resolve_strength(0) == 0.0
        assert resolve_strength(1) == 1.0

    def test_numeric_strings_are_rejected(self):
        with pytest.raises(ValueError, match="Invalid strength"):
            resolve_strength("0.75")

    def test_booleans_are_rejected(self):
        with pytest.raises(ValueError, match="Invalid strength"):
            resolve_strength(True)
        with pytest.raises(ValueError, match="Invalid strength"):
            resolve_strength(False)

    def test_invalid_strings_raise_helpful_error(self):
        with pytest.raises(ValueError, match="Invalid strength.*wild"):
            resolve_strength("wild")

    def test_out_of_range_numbers_raise_helpful_error(self):
        with pytest.raises(ValueError, match="Invalid strength.*-0.5"):
            resolve_strength(-0.5)
        with pytest.raises(ValueError, match="Invalid strength.*1.5"):
            resolve_strength(1.5)


class TestJaggednessResolver:
    """Tests for the resolve_jaggedness function."""

    def test_preset_strings_resolve_correctly(self):
        assert resolve_jaggedness("none") == STRENGTH_NONE
        assert resolve_jaggedness("low") == STRENGTH_LOW
        assert resolve_jaggedness("medium") == STRENGTH_MEDIUM
        assert resolve_jaggedness("high") == STRENGTH_HIGH
        assert resolve_jaggedness("extreme") == STRENGTH_EXTREME

    def test_presets_are_case_insensitive(self):
        assert resolve_jaggedness("NONE") == STRENGTH_NONE
        assert resolve_jaggedness("Low") == STRENGTH_LOW
        assert resolve_jaggedness("MEDIUM") == STRENGTH_MEDIUM
        assert resolve_jaggedness("High") == STRENGTH_HIGH
        assert resolve_jaggedness("EXTREME") == STRENGTH_EXTREME

    def test_numeric_values_resolve_correctly(self):
        assert resolve_jaggedness(0.0) == 0.0
        assert resolve_jaggedness(0.5) == 0.5
        assert resolve_jaggedness(1.0) == 1.0
        assert resolve_jaggedness(0) == 0.0
        assert resolve_jaggedness(1) == 1.0

    def test_numeric_strings_are_rejected(self):
        with pytest.raises(ValueError, match="Invalid jaggedness"):
            resolve_jaggedness("0.75")

    def test_booleans_are_rejected(self):
        with pytest.raises(ValueError, match="Invalid jaggedness"):
            resolve_jaggedness(True)
        with pytest.raises(ValueError, match="Invalid jaggedness"):
            resolve_jaggedness(False)

    def test_invalid_strings_raise_helpful_error(self):
        with pytest.raises(ValueError, match="Invalid jaggedness.*wild"):
            resolve_jaggedness("wild")

    def test_out_of_range_numbers_raise_helpful_error(self):
        with pytest.raises(ValueError, match="Invalid jaggedness.*-0.5"):
            resolve_jaggedness(-0.5)
        with pytest.raises(ValueError, match="Invalid jaggedness.*1.5"):
            resolve_jaggedness(1.5)


class TestEmptyAndSingleToneInputs:
    """Tests for edge cases with empty or single-tone phrases."""

    def test_accelerando_empty_phrase_returns_empty(self):
        result = accelerando_transform([], strength="medium", jaggedness="none")
        assert result == []

    def test_ritardando_empty_phrase_returns_empty(self):
        result = ritardando_transform([], strength="medium", jaggedness="none")
        assert result == []

    def test_accelerando_single_tone_unchanged(self):
        tones = [Tone(440, 1.0)]
        result = accelerando_transform(tones, strength="extreme", jaggedness="none")
        assert len(result) == 1
        assert result[0].duration == 1.0

    def test_ritardando_single_tone_unchanged(self):
        tones = [Tone(440, 1.0)]
        result = ritardando_transform(tones, strength="extreme", jaggedness="none")
        assert len(result) == 1
        assert result[0].duration == 1.0

    def test_accelerando_single_tone_with_jaggedness_remains_positive(self):
        tones = [Tone(440, 1.0)]
        result = accelerando_transform(tones, strength="medium", jaggedness="extreme")
        assert len(result) == 1
        assert result[0].duration > 0
