import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from score_model.tone import Tone


class TestTone:
    def test_generate_tone_type_and_shape(self):
        duration = 0.5
        sample_rate = 44100
        tone = Tone(frequency=440.0, duration=duration, sample_rate=sample_rate)
        
        wave = tone.generate_tone()
        
        expected_length = int(sample_rate * duration)
        assert hasattr(wave, '__len__')
        assert len(wave) == expected_length
        
        if len(wave) > 0:
            assert max(wave) <= 32767
            assert min(wave) >= -32768

    def test_generate_tone_zero_duration(self):
        tone = Tone(frequency=440.0, duration=0.0)
        wave = tone.generate_tone()
        assert hasattr(wave, '__len__')
        assert len(wave) == 0

    def test_sample_rate_initialization(self):
        tone_default = Tone(frequency=440.0)
        assert isinstance(tone_default.sample_rate, int)
        assert tone_default.sample_rate > 0
        
        tone_custom = Tone(frequency=440.0, sample_rate=48000)
        assert tone_custom.sample_rate == 48000

    def test_amplitude_initialization(self):
        tone_default = Tone(frequency=440.0)
        assert tone_default.amplitude == 0.5
        
        tone_custom = Tone(frequency=440.0, amplitude=0.8)
        assert tone_custom.amplitude == 0.8

    def test_silent_tone(self):
        tone = Tone(frequency=0, duration=0.1, amplitude=0.5)
        wave = tone.generate_tone()
        assert np.all(wave == 0)
        
        tone2 = Tone(frequency=440.0, duration=0.1, amplitude=0)
        wave2 = tone2.generate_tone()
        assert np.all(wave2 == 0)
