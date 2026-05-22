import pytest

from score_model.tone import Tone
from transforms.base import ToneDimension
from transforms.geological.terraced_drift import TERRACED_DRIFT_PARAMS_SPEC, _build_terraced_fluctuations, apply_terraced_drift_transform


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


def test_terraced_drift_is_repeatable():
    tones = _build_reference_tones()

    result_a = apply_terraced_drift_transform(tones, dimension=ToneDimension.FREQUENCY, max_step_change_pct=25)
    result_b = apply_terraced_drift_transform(tones, dimension=ToneDimension.FREQUENCY, max_step_change_pct=25)

    assert _snapshot(result_a) == _snapshot(result_b)
    assert len(result_a) == len(tones)


def test_terraced_drift_with_minimal_step_is_nearly_no_modulation():
    tones = _build_reference_tones()

    result = apply_terraced_drift_transform(tones, dimension=ToneDimension.FREQUENCY, max_step_change_pct=10)

    for original, transformed in zip(tones, result):
        assert transformed.frequency == pytest.approx(original.frequency, rel=0.15)


def test_terraced_drift_returns_empty_for_empty_input():
    assert apply_terraced_drift_transform([], dimension=ToneDimension.FREQUENCY, max_step_change_pct=25) == []


def test_terraced_drift_duration_modulates_without_touching_other_dimensions():
    tones = [
        Tone(frequency=440.0, duration=1.0, amplitude=0.5),
        Tone(frequency=880.0, duration=2.0, amplitude=0.8),
    ]

    result = apply_terraced_drift_transform(
        tones,
        dimension=ToneDimension.DURATION,
        max_step_change_pct=50,
    )

    assert any(transformed.duration != original.duration for transformed, original in zip(result, tones))
    assert result[0].frequency == pytest.approx(tones[0].frequency)
    assert result[1].frequency == pytest.approx(tones[1].frequency)
    assert result[0].amplitude == pytest.approx(tones[0].amplitude)
    assert result[1].amplitude == pytest.approx(tones[1].amplitude)


def test_terraced_drift_amplitude_modulates_without_touching_other_dimensions():
    tones = [
        Tone(frequency=440.0, duration=1.0, amplitude=0.95),
        Tone(frequency=880.0, duration=2.0, amplitude=0.05),
        Tone(frequency=660.0, duration=0.75, amplitude=0.6),
    ]

    result = apply_terraced_drift_transform(
        tones,
        dimension=ToneDimension.AMPLITUDE,
        max_step_change_pct=100,
    )

    assert any(transformed.amplitude != original.amplitude for transformed, original in zip(result, tones))
    assert all(0.0 <= tone.amplitude <= 1.0 for tone in result)
    assert result[0].frequency == pytest.approx(tones[0].frequency)
    assert result[1].frequency == pytest.approx(tones[1].frequency)
    assert result[2].frequency == pytest.approx(tones[2].frequency)
    assert result[0].duration == pytest.approx(tones[0].duration)
    assert result[1].duration == pytest.approx(tones[1].duration)
    assert result[2].duration == pytest.approx(tones[2].duration)


def test_build_terraced_fluctuations_without_quantization_returns_raw_values():
    """
    When quantize_resolution is 0.0 the builder must skip quantization and
    return raw floating-point values from the Brownian walk. Without this
    guarantee, callers wanting continuous (non-stepped) modulation cannot
    disable the quantization step.
    """
    tone_count = 5
    step_size = 0.1
    QUANTIZATION_DISABLED = 0.0
    MODULATION_LOWER_BOUND = -1.0
    MODULATION_UPPER_BOUND = 1.0
    ARBITRARY_QUANTIZATION_STEP = 0.2

    fluctuations = _build_terraced_fluctuations(
        length=tone_count, step_size=step_size, quantize_resolution=QUANTIZATION_DISABLED
    )

    assert len(fluctuations) == tone_count
    assert all(MODULATION_LOWER_BOUND <= value <= MODULATION_UPPER_BOUND for value in fluctuations)
    # Quantization snaps every value to the nearest multiple of a step
    # size (e.g. 0.0, 0.2, 0.4, ...). If the builder truly skipped
    # quantization, the raw Brownian walk values will NOT land neatly on
    # those grid points — at least one value will be something like
    # 0.173 instead of 0.0 or 0.2. Finding any such "off-grid" value
    # proves quantization was genuinely disabled.
    assert any(value != round(value / ARBITRARY_QUANTIZATION_STEP) * ARBITRARY_QUANTIZATION_STEP for value in fluctuations)


def test_terraced_drift_rejects_non_integer_and_out_of_range_step_percentages():
    tones = _build_reference_tones()

    with pytest.raises(ValueError):
        TERRACED_DRIFT_PARAMS_SPEC.parse_params(
            {"dimension": ToneDimension.FREQUENCY, "max_step_change_pct": 1.5},
            transform_name="terraced_drift",
        )

    with pytest.raises(ValueError, match="between 1 and 100"):
        apply_terraced_drift_transform(tones, dimension=ToneDimension.FREQUENCY, max_step_change_pct=0)

    with pytest.raises(ValueError, match="between 1 and 100"):
        apply_terraced_drift_transform(tones, dimension=ToneDimension.FREQUENCY, max_step_change_pct=101)
