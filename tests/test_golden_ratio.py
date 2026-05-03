import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from transforms.golden_ratio import golden_ratio_transform, phrase_golden_ratio_shrink, phrase_golden_ratio_grow
from score_model.math_constants import GOLDEN_RATIO
from score_model.tone import Tone

class TestGoldenRatioTransform:
    def test_golden_ratio(self):
        tones = [Tone(440, 1.0)]
        result = golden_ratio_transform(tones)
        assert result[0].duration == pytest.approx(1.0 / GOLDEN_RATIO)

class TestPhraseGoldenRatioShrink:
    def test_relative_scale(self):
        first_phrase_total_duration = 1.0
        first_phrase = [Tone(440, duration=first_phrase_total_duration)]
        
        second_phrase_tone_duration = 1.0
        second_phrase = [Tone(880, duration=second_phrase_tone_duration), Tone(523, duration=second_phrase_tone_duration)]
        
        transformed_second_phrase = phrase_golden_ratio_shrink(second_phrase, first_phrase)
        
        expected_total_duration = first_phrase_total_duration / GOLDEN_RATIO
        actual_total_duration = sum(t.duration for t in transformed_second_phrase)
        
        assert actual_total_duration == pytest.approx(expected_total_duration)
        
        expected_duration_per_tone = expected_total_duration / 2
        assert transformed_second_phrase[0].duration == pytest.approx(expected_duration_per_tone)
        assert transformed_second_phrase[1].duration == pytest.approx(expected_duration_per_tone)

    def test_empty_previous(self):
        second_phrase = [Tone(880, 1.0)]
        with pytest.raises(ValueError, match="Cannot apply phrase-golden-ratio-shrink: no preceding phrases exist to relate to."):
            phrase_golden_ratio_shrink(second_phrase, [])

class TestPhraseGoldenRatioGrow:
    def test_inverse_relative_scale(self):
        first_phrase_total_duration = 1.0
        first_phrase = [Tone(440, duration=first_phrase_total_duration)]
        
        second_phrase_tone_duration = 1.0
        second_phrase = [Tone(880, duration=second_phrase_tone_duration), Tone(523, duration=second_phrase_tone_duration)]
        
        transformed_second_phrase = phrase_golden_ratio_grow(second_phrase, first_phrase)
        
        expected_total_duration = first_phrase_total_duration * GOLDEN_RATIO
        actual_total_duration = sum(t.duration for t in transformed_second_phrase)
        
        assert actual_total_duration == pytest.approx(expected_total_duration)
        
        expected_duration_per_tone = expected_total_duration / 2
        assert transformed_second_phrase[0].duration == pytest.approx(expected_duration_per_tone)
        assert transformed_second_phrase[1].duration == pytest.approx(expected_duration_per_tone)

    def test_empty_previous(self):
        second_phrase = [Tone(880, 1.0)]
        with pytest.raises(ValueError, match="Cannot apply phrase-golden-ratio-grow: no preceding phrases exist to relate to."):
            phrase_golden_ratio_grow(second_phrase, [])
