import pytest

from score_model.tone import Tone
from transforms.complexity.weierstrass import apply_weierstrass_transform


def _snapshot(tones: list[Tone]) -> list[tuple[float, float, int, float]]:
    return [(tone.frequency, tone.duration, tone.sample_rate, tone.amplitude) for tone in tones]


def _build_reference_tones() -> list[Tone]:
    return [
        Tone(frequency=440.0, duration=1.0, amplitude=0.5),
        Tone(frequency=880.0, duration=2.0, amplitude=0.8),
        Tone(frequency=660.0, duration=0.75, amplitude=0.2),
        Tone(frequency=330.0, duration=1.25, amplitude=0.6),
        Tone(frequency=550.0, duration=0.5, amplitude=0.4),
    ]


def test_weierstrass_is_repeatable():
    tones = _build_reference_tones()

    result_a = apply_weierstrass_transform(tones, dimension="frequency", intensity="medium")
    result_b = apply_weierstrass_transform(tones, dimension="frequency", intensity="medium")

    assert _snapshot(result_a) == _snapshot(result_b)
    assert len(result_a) == len(tones)


def test_weierstrass_with_low_intensity_is_nearly_no_modulation():
    tones = _build_reference_tones()

    result = apply_weierstrass_transform(tones, dimension="frequency", intensity="low")

    for original, transformed in zip(tones, result):
        assert transformed.frequency == pytest.approx(original.frequency, rel=0.1)


def test_weierstrass_returns_empty_for_empty_input():
    assert apply_weierstrass_transform([], dimension="frequency", intensity="medium") == []








