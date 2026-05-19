import pytest

from score_model.tone import Tone
from transforms.geological.terraced_drift import _TerracedBrownianProfile, apply_terraced_drift_transform


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

    result_a = apply_terraced_drift_transform(tones, dimension="frequency", max_step_change_pct=25)
    result_b = apply_terraced_drift_transform(tones, dimension="frequency", max_step_change_pct=25)

    assert _snapshot(result_a) == _snapshot(result_b)
    assert len(result_a) == len(tones)


def test_terraced_drift_with_minimal_step_is_nearly_no_modulation():
    tones = _build_reference_tones()

    result = apply_terraced_drift_transform(tones, dimension="frequency", max_step_change_pct=10)

    for original, transformed in zip(tones, result):
        assert transformed.frequency == pytest.approx(original.frequency, rel=0.15)


def test_terraced_drift_returns_empty_for_empty_input():
    assert apply_terraced_drift_transform([], dimension="frequency", max_step_change_pct=25) == []


def test_terraced_drift_duration_modulates_without_touching_other_dimensions():
    tones = [
        Tone(frequency=440.0, duration=1.0, amplitude=0.5),
        Tone(frequency=880.0, duration=2.0, amplitude=0.8),
    ]

    result = apply_terraced_drift_transform(
        tones,
        dimension="duration",
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
        dimension="amplitude",
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


def test_terraced_brownian_profile_returns_raw_values_when_quantization_is_disabled():
    profile = _TerracedBrownianProfile(seed=7, step_size=0.1, quantize_resolution=0.0)

    generated_profile = profile.generate(5)

    assert len(generated_profile) == 5
    assert all(-1.0 <= value <= 1.0 for value in generated_profile)
    assert any(value != round(value / 0.2) * 0.2 for value in generated_profile)


def test_terraced_drift_rejects_non_integer_and_out_of_range_step_percentages():
    tones = _build_reference_tones()

    with pytest.raises(ValueError, match="must be an integer"):
        apply_terraced_drift_transform(tones, dimension="frequency", max_step_change_pct=1.5)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="between 1 and 100"):
        apply_terraced_drift_transform(tones, dimension="frequency", max_step_change_pct=0)

    with pytest.raises(ValueError, match="between 1 and 100"):
        apply_terraced_drift_transform(tones, dimension="frequency", max_step_change_pct=101)
