import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from score_model.tone import Tone
from transforms.reversal import reverse_tones


class TestReverseTones:
    def test_reverse(self):
        tones = [Tone(440), Tone(880), Tone(523)]
        result = reverse_tones(tones)
        assert len(result) == 3
        assert result[0].frequency == 523
        assert result[1].frequency == 880
        assert result[2].frequency == 440
