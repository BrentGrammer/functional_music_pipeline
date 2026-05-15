import pytest

from score_model.tone import Tone
from transforms.base import ToneDimension
from transforms.geological.ridged_drop import (
    _RIDGED_DROP_DEPTH_LEVELS,
    _RIDGED_DROP_INTENSITY_PRESETS,
    _resolve_drop_depth,
    _resolve_intensity,
    apply_ridged_drop_transform,
)
from transforms.geological.terraced_drift import apply_terraced_drift_transform


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


@pytest.mark.parametrize(
    ("transform", "kwargs"),
    [
        pytest.param(
            apply_terraced_drift_transform,
            {
                "dimension": ToneDimension.FREQUENCY,
                "max_deviation": 0.1,
                "seed": 42,
                "step_size": 0.25,
                "quantize_resolution": 0.2,
            },
            id="terraced_drift",
        ),
        pytest.param(
            apply_ridged_drop_transform,
            {
                "dimension": ToneDimension.FREQUENCY,
                "max_deviation": 0.1,
                "seed": 42,
                "octaves": 3,
                "ridge_density": 0.3,
                "drop_when_noise_above": 0.5,
            },
            id="ridged_drop",
        ),
    ],
)
def test_seeded_geological_modulation_transforms_are_repeatable(transform, kwargs):
    tones = _build_reference_tones()

    result_a = transform(tones, **kwargs)
    result_b = transform(tones, **kwargs)

    assert _snapshot(result_a) == _snapshot(result_b)
    assert len(result_a) == len(tones)


@pytest.mark.parametrize(
    ("transform", "kwargs"),
    [
        pytest.param(
            apply_terraced_drift_transform,
            {
                "dimension": ToneDimension.FREQUENCY,
                "max_deviation": 0.1,
                "seed": 7,
                "step_size": 0.0,
                "quantize_resolution": 0.2,
            },
            id="terraced_drift-zero-step",
        ),
        pytest.param(
            apply_ridged_drop_transform,
            {
                "dimension": ToneDimension.FREQUENCY,
                "max_deviation": 0.1,
                "seed": 7,
                "octaves": 0,
                "ridge_density": 0.3,
                "drop_when_noise_above": 0.5,
            },
            id="ridged_drop-zero-octaves",
        ),
    ],
)
def test_edge_case_parameters_can_produce_no_modulation(transform, kwargs):
    tones = _build_reference_tones()

    result = transform(tones, **kwargs)

    assert _snapshot(result) == _snapshot(tones)


@pytest.mark.parametrize(
    ("transform", "kwargs"),
    [
        pytest.param(
            apply_terraced_drift_transform,
            {"dimension": ToneDimension.FREQUENCY, "max_deviation": 0.1, "seed": 42},
            id="terraced_drift",
        ),
        pytest.param(
            apply_ridged_drop_transform,
            {"dimension": ToneDimension.FREQUENCY, "max_deviation": 0.1, "seed": 42},
            id="ridged_drop",
        ),
    ],
)
def test_geological_modulation_transforms_return_empty_output_for_empty_input(transform, kwargs):
    assert transform([], **kwargs) == []


def test_terraced_drift_duration_modulates_without_touching_other_dimensions():
    tones = [
        Tone(frequency=440.0, duration=1.0, amplitude=0.5),
        Tone(frequency=880.0, duration=2.0, amplitude=0.8),
    ]

    result = apply_terraced_drift_transform(
        tones,
        dimension=ToneDimension.DURATION,
        max_deviation=0.5,
        seed=42,
        step_size=1.0,
        quantize_resolution=0.5,
    )

    assert any(transformed.duration != original.duration for transformed, original in zip(result, tones))
    assert result[0].frequency == pytest.approx(tones[0].frequency)
    assert result[1].frequency == pytest.approx(tones[1].frequency)
    assert result[0].amplitude == pytest.approx(tones[0].amplitude)
    assert result[1].amplitude == pytest.approx(tones[1].amplitude)


def test_ridged_drop_amplitude_modulates_without_touching_other_dimensions():
    tones = [
        Tone(frequency=440.0, duration=1.0, amplitude=0.8),
        Tone(frequency=880.0, duration=2.0, amplitude=0.8),
    ]

    result = apply_ridged_drop_transform(
        tones,
        dimension=ToneDimension.AMPLITUDE,
        max_deviation=1.0,
        seed=42,
        octaves=1,
        ridge_density=0.3,
        drop_when_noise_above=0.0,
    )

    assert any(transformed.amplitude < original.amplitude for transformed, original in zip(result, tones))
    assert all(0.0 <= tone.amplitude <= 1.0 for tone in result)
    assert result[0].frequency == pytest.approx(tones[0].frequency)
    assert result[1].frequency == pytest.approx(tones[1].frequency)
    assert result[0].duration == pytest.approx(tones[0].duration)
    assert result[1].duration == pytest.approx(tones[1].duration)


def test_resolve_drop_depth_accepts_named_levels():
    for name, expected_value in _RIDGED_DROP_DEPTH_LEVELS.items():
        assert _resolve_drop_depth(name) == expected_value


def test_resolve_drop_depth_accepts_named_levels_case_insensitive():
    assert _resolve_drop_depth("MEDIUM") == _RIDGED_DROP_DEPTH_LEVELS["medium"]
    assert _resolve_drop_depth("High") == _RIDGED_DROP_DEPTH_LEVELS["high"]


def test_resolve_drop_depth_accepts_numeric_values():
    assert _resolve_drop_depth(0.0) == 0.0
    assert _resolve_drop_depth(0.37) == 0.37
    assert _resolve_drop_depth(1.0) == 1.0


def test_resolve_drop_depth_rejects_boolean():
    with pytest.raises(ValueError):
        _resolve_drop_depth(True)
    with pytest.raises(ValueError):
        _resolve_drop_depth(False)


def test_resolve_drop_depth_rejects_unknown_string():
    with pytest.raises(ValueError):
        _resolve_drop_depth("invalid")


def test_resolve_drop_depth_rejects_value_below_zero():
    with pytest.raises(ValueError):
        _resolve_drop_depth(-0.1)


def test_resolve_drop_depth_rejects_value_above_one():
    with pytest.raises(ValueError):
        _resolve_drop_depth(1.5)


def test_resolve_drop_depth_rejects_none():
    with pytest.raises(ValueError):
        _resolve_drop_depth(None)


def test_resolve_intensity_accepts_named_presets():
    for name, expected_preset in _RIDGED_DROP_INTENSITY_PRESETS.items():
        assert _resolve_intensity(name) == expected_preset


def test_resolve_intensity_accepts_named_presets_case_insensitive():
    assert _resolve_intensity("SUBTLE") == _RIDGED_DROP_INTENSITY_PRESETS["subtle"]
    assert _resolve_intensity("Severe") == _RIDGED_DROP_INTENSITY_PRESETS["severe"]


def test_resolve_intensity_rejects_boolean():
    with pytest.raises(ValueError):
        _resolve_intensity(True)
    with pytest.raises(ValueError):
        _resolve_intensity(False)


def test_resolve_intensity_rejects_unknown_string():
    with pytest.raises(ValueError):
        _resolve_intensity("invalid")


def test_resolve_intensity_rejects_none():
    with pytest.raises(ValueError):
        _resolve_intensity(None)


def test_resolve_intensity_rejects_numeric():
    with pytest.raises(ValueError):
        _resolve_intensity(123)
