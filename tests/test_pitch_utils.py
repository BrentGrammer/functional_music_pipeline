import pytest

from score_model.pitch_utils import (
    cents_to_frequency,
    frequency_to_cents,
    frequency_to_semitones,
    transpose_frequency_by_semitones,
)


def test_cents_to_frequency():
    A4 = 440.0
    # +1200 cents is one octave up
    assert cents_to_frequency(A4, 1200.0) == pytest.approx(880.0)
    # -1200 cents is one octave down
    assert cents_to_frequency(A4, -1200.0) == pytest.approx(220.0)
    # +100 cents is a semitone
    assert cents_to_frequency(A4, 100.0) == pytest.approx(440.0 * (2 ** (1 / 12)))


def test_transpose_frequency_by_semitones():
    A4 = 440.0
    # +12 semitones is one octave up
    assert transpose_frequency_by_semitones(A4, 12.0) == pytest.approx(880.0)
    # -12 semitones is one octave down
    assert transpose_frequency_by_semitones(A4, -12.0) == pytest.approx(220.0)
    # +1 semitone is a semitone
    assert transpose_frequency_by_semitones(A4, 1.0) == pytest.approx(440.0 * (2 ** (1 / 12)))
    # +0.5 semitone is a quarter tone
    assert transpose_frequency_by_semitones(A4, 0.5) == pytest.approx(440.0 * (2 ** (0.5 / 12)))


def test_frequency_to_cents():
    A4 = 440.0
    A5 = 880.0
    A3 = 220.0
    assert frequency_to_cents(A5, A4) == pytest.approx(1200.0)
    assert frequency_to_cents(A3, A4) == pytest.approx(-1200.0)
    assert frequency_to_cents(A4, A4) == pytest.approx(0.0)


def test_frequency_to_semitones():
    A4 = 440.0
    A5 = 880.0
    A3 = 220.0
    assert frequency_to_semitones(A5, A4) == pytest.approx(12.0)
    assert frequency_to_semitones(A3, A4) == pytest.approx(-12.0)
    assert frequency_to_semitones(A4, A4) == pytest.approx(0.0)


def test_rejects_nonpositive_frequencies():
    with pytest.raises(ValueError):
        cents_to_frequency(0, 100)
    with pytest.raises(ValueError):
        transpose_frequency_by_semitones(-1, 1)
    with pytest.raises(ValueError):
        frequency_to_cents(0, 440)
    with pytest.raises(ValueError):
        frequency_to_cents(440, -1)
    with pytest.raises(ValueError):
        frequency_to_semitones(0, 440)
    with pytest.raises(ValueError):
        frequency_to_semitones(440, -1)
