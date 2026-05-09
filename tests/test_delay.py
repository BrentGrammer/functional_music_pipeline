import sys
import os
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from transforms.delay import delay_tones
from score_model.tone import Tone

def test_delay_zero():
    """Zero delay should return original tones."""
    tones = [Tone(440.0), Tone(523.25)]
    result = delay_tones(tones, seconds=0)
    assert len(result) == 2
    assert result[0].frequency == pytest.approx(440.0)
    assert result[1].frequency == pytest.approx(523.25)

def test_delay_positive():
    """Positive delay should prepend a silent tone."""
    tones = [Tone(440.0, duration=0.5), Tone(523.25, duration=0.3)]
    delay_time = 0.2
    result = delay_tones(tones, seconds=delay_time)
    
    expected_length = len(tones) + 1
    assert len(result) == expected_length
    
    assert result[0].frequency == 0
    assert result[0].amplitude == 0
    assert result[0].duration == pytest.approx(delay_time)
    
    assert result[1].frequency == pytest.approx(440.0)
    assert result[1].duration == pytest.approx(0.5)
    assert result[2].frequency == pytest.approx(523.25)
    assert result[2].duration == pytest.approx(0.3)

def test_delay_negative():
    """Negative delay should raise ValueError."""
    tones = [Tone(440.0)]
    with pytest.raises(ValueError, match="Delay must be non-negative. Negative offsets are not supported."):
        delay_tones(tones, seconds=-0.5)

def test_delay_preserves_amplitude():
    """Delay should preserve amplitude of original tones."""
    tones = [Tone(440.0, amplitude=0.3), Tone(523.25, amplitude=0.7)]
    result = delay_tones(tones, seconds=0.1)
    
    assert len(result) == 3
    assert result[0].amplitude == 0
    assert result[1].amplitude == pytest.approx(0.3)
    assert result[2].amplitude == pytest.approx(0.7)

def test_delay_generates_silence():
    """The silent tone should generate actual silence (all zeros)."""
    delay_time = 0.1
    silent_tone = Tone(frequency=0, duration=delay_time, amplitude=0)
    wave = silent_tone.generate_tone()
    
    assert np.all(wave == 0)
    expected_length = int(silent_tone.sample_rate * delay_time)
    assert len(wave) == expected_length

def test_delay_empty_list():
    """Delaying an empty tone list should still prepend a silent tone."""
    result = delay_tones([], seconds=0.5)
    assert len(result) == 1
    assert result[0].frequency == 0
    assert result[0].duration == pytest.approx(0.5)
