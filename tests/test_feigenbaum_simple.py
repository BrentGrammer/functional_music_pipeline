import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from transforms.duration import feigenbaum_sequence
from score_model.tone import Tone
from score_model.math_constants import FEIGENBAUM_DELTA

class TestFeigenbaumDuration:
    def test_basic_sequence(self):
        tones = [
            Tone(440, duration=FEIGENBAUM_DELTA),
            Tone(523),
            Tone(659)
        ]
        
        result = feigenbaum_sequence(tones)
        
        assert len(result) == 3
        assert result[0].duration == pytest.approx(FEIGENBAUM_DELTA)
        assert result[1].duration == pytest.approx(1.0)
        assert result[2].duration == pytest.approx(1.0 / FEIGENBAUM_DELTA)

    def test_single_tone(self):
        tones = [Tone(440)]
        result = feigenbaum_sequence(tones)
        assert len(result) == 1
        assert result[0].duration == tones[0].duration

    def test_empty_input(self):
        assert feigenbaum_sequence([]) == []
