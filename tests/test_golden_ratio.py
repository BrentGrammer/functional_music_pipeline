import pytest

from score_model.math_constants import GOLDEN_RATIO
from score_model.tone import Tone
from transforms.golden_ratio import (
    golden_ratio_transform,
    phrase_golden_ratio_grow,
    phrase_golden_ratio_shrink,
)


class TestGoldenRatioTransform:
    def test_golden_ratio_scales_duration_by_inverse_constant(self):
        original_duration = 1.0
        tones = [Tone(440.0, original_duration)]

        result = golden_ratio_transform(tones)

        assert result[0].duration == pytest.approx(original_duration / GOLDEN_RATIO)

    def test_golden_ratio_scales_frequency_when_dimension_is_frequency_string(self):
        original_frequency = 440.0
        original_duration = 1.0
        tones = [Tone(original_frequency, original_duration)]

        result = golden_ratio_transform(tones, dimension="FREQUENCY")

        assert result[0].frequency == pytest.approx(original_frequency / GOLDEN_RATIO)
        assert result[0].duration == pytest.approx(original_duration)


class TestPhraseGoldenRatioShrink:
    def test_relative_scale_on_duration_dimension(self):
        previous_phrase_total_duration = 1.0
        previous_phrase = [Tone(440.0, duration=previous_phrase_total_duration)]

        current_tone_duration = 1.0
        current_phrase = [
            Tone(880.0, duration=current_tone_duration),
            Tone(523.0, duration=current_tone_duration),
        ]

        transformed_phrase = phrase_golden_ratio_shrink(current_phrase, previous_phrase)

        expected_total_duration = previous_phrase_total_duration / GOLDEN_RATIO
        actual_total_duration = sum(tone.duration for tone in transformed_phrase)
        expected_duration_per_tone = expected_total_duration / len(current_phrase)

        assert actual_total_duration == pytest.approx(expected_total_duration)
        assert transformed_phrase[0].duration == pytest.approx(expected_duration_per_tone)
        assert transformed_phrase[1].duration == pytest.approx(expected_duration_per_tone)

    def test_empty_previous_phrase_raises_error(self):
        current_phrase = [Tone(880.0, 1.0)]

        with pytest.raises(
            ValueError,
            match="Cannot apply phrase-golden-ratio-shrink: no preceding phrases exist to relate to.",
        ):
            phrase_golden_ratio_shrink(current_phrase, [])

    def test_empty_current_phrase_returns_empty_list(self):
        previous_phrase = [Tone(440.0, duration=1.0)]

        assert phrase_golden_ratio_shrink([], previous_phrase) == []

    def test_zero_current_total_returns_original_tones(self):
        previous_phrase = [Tone(440.0, duration=1.0)]
        zero_duration_phrase = [Tone(880.0, duration=0.0), Tone(523.0, duration=0.0)]

        result = phrase_golden_ratio_shrink(zero_duration_phrase, previous_phrase)

        assert result is zero_duration_phrase

    def test_zero_previous_total_returns_original_tones(self):
        zero_duration_previous_phrase = [Tone(440.0, duration=0.0)]
        current_phrase = [Tone(880.0, duration=1.0)]

        result = phrase_golden_ratio_shrink(current_phrase, zero_duration_previous_phrase)

        assert result is current_phrase

    def test_relative_scale_on_amplitude_dimension(self):
        previous_phrase_total_amplitude = 0.6
        previous_phrase = [Tone(440.0, amplitude=previous_phrase_total_amplitude)]
        current_phrase = [
            Tone(660.0, amplitude=0.3),
            Tone(880.0, amplitude=0.3),
        ]

        transformed_phrase = phrase_golden_ratio_shrink(
            current_phrase,
            previous_phrase,
            dimension="AMPLITUDE",
        )

        expected_total_amplitude = previous_phrase_total_amplitude / GOLDEN_RATIO
        actual_total_amplitude = sum(tone.amplitude for tone in transformed_phrase)

        assert actual_total_amplitude == pytest.approx(expected_total_amplitude)


class TestPhraseGoldenRatioGrow:
    def test_inverse_relative_scale_on_duration_dimension(self):
        previous_phrase_total_duration = 1.0
        previous_phrase = [Tone(440.0, duration=previous_phrase_total_duration)]

        current_tone_duration = 1.0
        current_phrase = [
            Tone(880.0, duration=current_tone_duration),
            Tone(523.0, duration=current_tone_duration),
        ]

        transformed_phrase = phrase_golden_ratio_grow(current_phrase, previous_phrase)

        expected_total_duration = previous_phrase_total_duration * GOLDEN_RATIO
        actual_total_duration = sum(tone.duration for tone in transformed_phrase)
        expected_duration_per_tone = expected_total_duration / len(current_phrase)

        assert actual_total_duration == pytest.approx(expected_total_duration)
        assert transformed_phrase[0].duration == pytest.approx(expected_duration_per_tone)
        assert transformed_phrase[1].duration == pytest.approx(expected_duration_per_tone)

    def test_empty_previous_phrase_raises_error(self):
        current_phrase = [Tone(880.0, 1.0)]

        with pytest.raises(
            ValueError,
            match="Cannot apply phrase-golden-ratio-grow: no preceding phrases exist to relate to.",
        ):
            phrase_golden_ratio_grow(current_phrase, [])

    def test_empty_current_phrase_returns_empty_list(self):
        previous_phrase = [Tone(440.0, duration=1.0)]

        assert phrase_golden_ratio_grow([], previous_phrase) == []

    def test_zero_current_total_returns_original_tones(self):
        previous_phrase = [Tone(440.0, duration=1.0)]
        zero_duration_phrase = [Tone(880.0, duration=0.0), Tone(523.0, duration=0.0)]

        result = phrase_golden_ratio_grow(zero_duration_phrase, previous_phrase)

        assert result is zero_duration_phrase

    def test_zero_previous_total_returns_original_tones(self):
        zero_duration_previous_phrase = [Tone(440.0, duration=0.0)]
        current_phrase = [Tone(880.0, duration=1.0)]

        result = phrase_golden_ratio_grow(current_phrase, zero_duration_previous_phrase)

        assert result is current_phrase

    def test_relative_scale_on_frequency_dimension(self):
        previous_phrase_total_frequency = 440.0
        previous_phrase = [Tone(previous_phrase_total_frequency, duration=1.0)]
        current_phrase = [
            Tone(220.0, duration=1.0),
            Tone(220.0, duration=1.0),
        ]

        transformed_phrase = phrase_golden_ratio_grow(
            current_phrase,
            previous_phrase,
            dimension="FREQUENCY",
        )

        expected_total_frequency = previous_phrase_total_frequency * GOLDEN_RATIO
        actual_total_frequency = sum(tone.frequency for tone in transformed_phrase)

        assert actual_total_frequency == pytest.approx(expected_total_frequency)
