import pytest
from score_model.tone import Tone
from transforms.base import ToneDimension
from transforms.scale import scale_transform


class TestScaleTransform:
    def test_scale_frequency(self):
        tones = [Tone(440.0)]
        result = scale_transform(tones, ToneDimension.FREQUENCY, 1.5)
        assert result[0].frequency == pytest.approx(660.0)

    def test_scale_duration(self):
        tones = [Tone(440.0, duration=1.0)]
        result = scale_transform(tones, ToneDimension.DURATION, 2.0)
        assert result[0].duration == pytest.approx(2.0)

    def test_scale_amplitude(self):
        tones = [Tone(440.0, amplitude=0.5)]
        result = scale_transform(tones, ToneDimension.AMPLITUDE, 0.5)
        assert result[0].amplitude == pytest.approx(0.25)

    def test_scale_amplitude_clamp(self):
        tones = [Tone(440.0, amplitude=0.8)]
        result = scale_transform(tones, ToneDimension.AMPLITUDE, 2.0)
        assert result[0].amplitude == pytest.approx(1.0)
