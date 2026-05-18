import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from score_model.pitch_utils import transpose_frequency_by_semitones
from score_model.tone import Tone
from transforms.basic.transpose import transpose_tones


class TestTransposeTones:
    def test_transpose_up_octave(self):
        tones = [Tone(440)]
        result = transpose_tones(tones, 12)
        assert result[0].frequency == pytest.approx(880.0)

    def test_transpose_down_octave(self):
        tones = [Tone(440)]
        result = transpose_tones(tones, -12)
        assert result[0].frequency == pytest.approx(220.0)

    def test_transpose_semitone(self):
        tones = [Tone(440)]
        result = transpose_tones(tones, 1)
        assert result[0].frequency == pytest.approx(440.0 * (2 ** (1.0 / 12.0)))

    def test_transpose_ignores_rests(self):
        tones = [Tone(0)]
        result = transpose_tones(tones, 12)
        assert result[0].frequency == 0.0

    def test_fractional_transpose_is_microtonal(self):
        # This test verifies that a fractional transpose produces a frequency
        # that is genuinely between the standard 12-TET semitones.
        A4 = 440.0
        A_SHARP_4 = transpose_frequency_by_semitones(A4, 1)

        tones = [Tone(A4)]

        # Transpose up by a half-semitone (50 cents)
        result = transpose_tones(tones, 0.5)

        # 1. Check that the frequency is correct
        expected_freq = transpose_frequency_by_semitones(A4, 0.5)
        assert result[0].frequency == pytest.approx(expected_freq)

        # 2. Check that the frequency is NOT the original note
        assert result[0].frequency != pytest.approx(A4)

        # 3. Check that the frequency has NOT snapped to the next semitone
        assert result[0].frequency != pytest.approx(A_SHARP_4)
