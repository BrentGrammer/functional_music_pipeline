import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from score_model.tone import Tone
from transforms.base import ToneDimension
from transforms.basic.inversion import invert_tones


class TestInvertTones:
    def test_invert_single_tone(self):
        """Inverting a single tone should return the same tone."""
        tones = [Tone(440.0)]
        result = invert_tones(tones)
        assert len(result) == 1
        assert result[0].frequency == pytest.approx(440.0)
        assert result[0].duration == tones[0].duration

    def test_invert_ascending_sequence(self):
        """Test inversion of an ascending sequence."""
        tones = [Tone(440.0), Tone(523.25), Tone(659.26)]
        result = invert_tones(tones)

        assert len(result) == 3
        assert result[0].frequency == pytest.approx(440.0)

        expected_second = 440.0 / (523.25 / 440.0)
        assert result[1].frequency == pytest.approx(expected_second)

        expected_third = 440.0 / (659.26 / 440.0)
        assert result[2].frequency == pytest.approx(expected_third)

        for i in range(3):
            assert result[i].duration == tones[i].duration

    def test_invert_descending_sequence(self):
        """Test inversion of a descending sequence."""
        tones = [Tone(659.26), Tone(523.25), Tone(440.0)]
        result = invert_tones(tones)

        assert len(result) == 3
        assert result[0].frequency == pytest.approx(659.26)

        expected_second = 659.26 / (523.25 / 659.26)
        assert result[1].frequency == pytest.approx(expected_second)

        expected_third = 659.26 / (440.0 / 659.26)
        assert result[2].frequency == pytest.approx(expected_third)

    def test_invert_mixed_sequence(self):
        """Test inversion of a sequence that goes up then down."""
        tones = [Tone(440.0), Tone(523.25), Tone(440.0)]
        result = invert_tones(tones)

        assert len(result) == 3
        assert result[0].frequency == pytest.approx(440.0)

        expected_second = 440.0 / (523.25 / 440.0)
        assert result[1].frequency == pytest.approx(expected_second)

        expected_third = 440.0 / (440.0 / 440.0)
        assert result[2].frequency == pytest.approx(expected_third)

    def test_invert_with_different_durations(self):
        """Test that inversion preserves durations even when they vary."""
        tones = [
            Tone(440.0, duration=0.5),
            Tone(523.25, duration=1.0),
            Tone(659.26, duration=0.25),
        ]
        result = invert_tones(tones)

        assert len(result) == len(tones)
        assert result[0].frequency == pytest.approx(440.0)
        assert result[1].frequency == pytest.approx(440.0 / (523.25 / 440.0))
        assert result[2].frequency == pytest.approx(440.0 / (659.26 / 440.0))

        assert result[0].duration == pytest.approx(0.5)
        assert result[1].duration == pytest.approx(1.0)
        assert result[2].duration == pytest.approx(0.25)

    def test_invert_duration(self):
        """Test inversion applied to duration."""
        tones = [
            Tone(440.0, duration=1.0),
            Tone(523.25, duration=2.0),
            Tone(659.26, duration=0.5),
        ]
        result = invert_tones(tones, dimension=ToneDimension.DURATION)

        assert len(result) == 3
        assert result[0].duration == pytest.approx(1.0)
        # 1.0 / (2.0 / 1.0) = 0.5
        assert result[1].duration == pytest.approx(0.5)
        # 1.0 / (0.5 / 1.0) = 2.0
        assert result[2].duration == pytest.approx(2.0)
        
        # Frequencies remain unchanged
        for i in range(3):
            assert result[i].frequency == tones[i].frequency

    def test_invert_amplitude(self):
        """Test inversion applied to amplitude."""
        tones = [
            Tone(440.0, amplitude=0.5),
            Tone(523.25, amplitude=1.0),
            Tone(659.26, amplitude=0.25),
        ]
        result = invert_tones(tones, dimension=ToneDimension.AMPLITUDE)

        assert len(result) == 3
        assert result[0].amplitude == pytest.approx(0.5)
        # 0.5 / (1.0 / 0.5) = 0.25
        assert result[1].amplitude == pytest.approx(0.25)
        # 0.5 / (0.25 / 0.5) = 1.0
        assert result[2].amplitude == pytest.approx(1.0)
