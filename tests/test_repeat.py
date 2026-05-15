import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from score_model.tone import Tone
from transforms.basic.repeat import repeat_tones


class TestRepeatTones:
    def test_repeat_once(self):
        """Repeating once should play the series twice total."""
        tones = [Tone(440.0), Tone(523.25)]
        repeat_count = 1
        result = repeat_tones(tones, repeat_count)
        expected_length = len(tones) * (repeat_count + 1)
        assert len(result) == expected_length
        
        for i in range(repeat_count + 1):
            assert result[2 * i].frequency == pytest.approx(440.0)
            assert result[2 * i + 1].frequency == pytest.approx(523.25)

    def test_repeat_multiple_times(self):
        """Repeating multiple times should concatenate the series."""
        tones = [Tone(440.0), Tone(523.25)]
        repeat_count = 3
        result = repeat_tones(tones, repeat_count)
        expected_length = len(tones) * (repeat_count + 1)
        assert len(result) == expected_length
        
        for i in range(repeat_count + 1):
            assert result[2 * i].frequency == pytest.approx(440.0)
            assert result[2 * i + 1].frequency == pytest.approx(523.25)

    def test_repeat_zero_times(self):
        """Repeating zero times should raise ValueError."""
        tones = [Tone(440.0)]
        with pytest.raises(ValueError, match="Repeat count must be at least 1."):
            repeat_tones(tones, 0)

    def test_repeat_negative_times(self):
        """Repeating negative times should raise ValueError."""
        tones = [Tone(440.0)]
        with pytest.raises(ValueError, match="Repeat count must be at least 1."):
            repeat_tones(tones, -1)

    def test_repeat_preserves_attributes(self):
        """Repeat should preserve all tone attributes."""
        tones = [
            Tone(440.0, duration=0.5, amplitude=0.3),
            Tone(523.25, duration=0.3, amplitude=0.7)
        ]
        repeat_count = 2
        result = repeat_tones(tones, repeat_count)
        
        expected_length = len(tones) * (repeat_count + 1)
        assert len(result) == expected_length
        
        for i in range(repeat_count + 1):
            assert result[2 * i].frequency == pytest.approx(440.0)
            assert result[2 * i].duration == pytest.approx(0.5)
            assert result[2 * i].amplitude == pytest.approx(0.3)
            
            assert result[2 * i + 1].frequency == pytest.approx(523.25)
            assert result[2 * i + 1].duration == pytest.approx(0.3)
            assert result[2 * i + 1].amplitude == pytest.approx(0.7)
