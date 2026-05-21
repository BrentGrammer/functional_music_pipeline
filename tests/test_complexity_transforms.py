import pytest

from score_model.tone import Tone
from transforms.base import ToneDimension
from transforms.complexity.cellular_automata import _derive_initial_state, apply_cellular_automata_transform
from transforms.complexity.random_drop import apply_random_drop_transform
from transforms.complexity.weierstrass import _resolve_intensity, _build_weierstrass_fluctuations, apply_weierstrass_transform


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


def test_build_weierstrass_fluctuations_with_zero_iterations_returns_zeros():
    tone_count = 3
    fluctuations = _build_weierstrass_fluctuations(
        length=tone_count, amplitude_scaling=0.5, ripples_per_wave=3.0, iterations=0
    )

    assert fluctuations == [0.0, 0.0, 0.0]


def test_weierstrass_resolve_intensity_rejects_non_string_and_unknown_values():
    with pytest.raises(ValueError, match="must be a string"):
        _resolve_intensity(1.0)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Invalid intensity"):
        _resolve_intensity("ultra")


def test_cellular_automata_is_deterministic():
    tones = _build_reference_tones()

    result_a = apply_cellular_automata_transform(tones, dimension="frequency", rule=30, generations=5, max_deviation=0.3)
    result_b = apply_cellular_automata_transform(tones, dimension="frequency", rule=30, generations=5, max_deviation=0.3)

    assert _snapshot(result_a) == _snapshot(result_b)


def test_cellular_automata_different_input_tones_produce_different_output():
    tones_a = _build_reference_tones()
    tones_b = [
        Tone(frequency=261.63, duration=0.5, amplitude=0.3),
        Tone(frequency=293.66, duration=0.5, amplitude=0.5),
        Tone(frequency=329.63, duration=0.5, amplitude=0.7),
        Tone(frequency=349.23, duration=0.5, amplitude=0.4),
        Tone(frequency=392.00, duration=0.5, amplitude=0.6),
    ]

    result_a = apply_cellular_automata_transform(tones_a, dimension="frequency", rule=30, generations=5, max_deviation=0.3)
    result_b = apply_cellular_automata_transform(tones_b, dimension="frequency", rule=30, generations=5, max_deviation=0.3)

    assert _snapshot(result_a) != _snapshot(result_b)


def test_cellular_automata_different_rules_produce_different_output():
    tones = _build_reference_tones()

    result_rule30 = apply_cellular_automata_transform(tones, dimension="frequency", rule=30, generations=5, max_deviation=0.3)
    result_rule110 = apply_cellular_automata_transform(tones, dimension="frequency", rule=110, generations=5, max_deviation=0.3)

    assert _snapshot(result_rule30) != _snapshot(result_rule110)


def test_cellular_automata_returns_empty_for_empty_input():
    assert apply_cellular_automata_transform([], dimension="frequency", rule=30, generations=5, max_deviation=0.3) == []


def test_cellular_automata_returns_single_tone_unchanged():
    tone = Tone(frequency=440.0, duration=1.0, amplitude=0.5)

    result = apply_cellular_automata_transform([tone], dimension="frequency", rule=30, generations=5, max_deviation=0.3)

    assert len(result) == 1
    assert result[0].frequency == pytest.approx(tone.frequency)
    assert result[0].duration == pytest.approx(tone.duration)
    assert result[0].amplitude == pytest.approx(tone.amplitude)


def test_cellular_automata_uniform_input_uses_alternating_fallback():
    # All tones have the same frequency — _derive_initial_state falls back to
    # alternating [1, 0, 1, 0, ...] rather than a flat row. The result should
    # still be a valid, non-trivial output.
    tones = [Tone(frequency=440.0, duration=1.0, amplitude=0.5) for _ in range(6)]

    result = apply_cellular_automata_transform(tones, dimension="frequency", rule=30, generations=5, max_deviation=0.3)

    assert len(result) == len(tones)
    assert all(tone.frequency > 0 for tone in result)


def test_cellular_automata_rejects_invalid_dimension_in_internal_state_derivation():
    tones = _build_reference_tones()

    with pytest.raises(ValueError):
        _derive_initial_state(tones, "invalid") # type: ignore[arg-type]


def test_cellular_automata_internal_state_derivation_supports_amplitude_dimension():
    tones = _build_reference_tones()

    state = _derive_initial_state(tones, ToneDimension.AMPLITUDE)

    assert len(state) == len(tones)
    assert all(cell in (0, 1) for cell in state)


def test_random_drop_is_deterministic():
    tones = _build_reference_tones()

    result_a = apply_random_drop_transform(tones, dimension=ToneDimension.AMPLITUDE, max_drop_pct=50, drop_frequency_pct=40)
    result_b = apply_random_drop_transform(tones, dimension=ToneDimension.AMPLITUDE, max_drop_pct=50, drop_frequency_pct=40)

    assert _snapshot(result_a) == _snapshot(result_b)


def test_random_drop_only_reduces_target_dimension():
    tones = _build_reference_tones()

    result = apply_random_drop_transform(tones, dimension=ToneDimension.AMPLITUDE, max_drop_pct=50, drop_frequency_pct=100)

    for original, transformed in zip(tones, result):
        assert transformed.amplitude <= original.amplitude
        assert transformed.frequency == pytest.approx(original.frequency)
        assert transformed.duration == pytest.approx(original.duration)


def test_random_drop_higher_frequency_affects_more_tones():
    # A large number of tones makes the probability difference statistically reliable.
    tones = [Tone(frequency=440.0, duration=1.0, amplitude=0.8) for _ in range(100)]

    result_rare = apply_random_drop_transform(tones, dimension=ToneDimension.AMPLITUDE, max_drop_pct=50, drop_frequency_pct=10)
    result_frequent = apply_random_drop_transform(tones, dimension=ToneDimension.AMPLITUDE, max_drop_pct=50, drop_frequency_pct=90)

    drops_rare = sum(1 for original, transformed in zip(tones, result_rare) if transformed.amplitude < original.amplitude)
    drops_frequent = sum(1 for original, transformed in zip(tones, result_frequent) if transformed.amplitude < original.amplitude)

    assert drops_frequent > drops_rare


def test_random_drop_returns_empty_for_empty_input():
    assert apply_random_drop_transform([], dimension=ToneDimension.AMPLITUDE, max_drop_pct=50, drop_frequency_pct=40) == []


def test_random_drop_rejects_out_of_range_max_drop_pct():
    tones = _build_reference_tones()

    with pytest.raises(ValueError):
        apply_random_drop_transform(tones, dimension=ToneDimension.AMPLITUDE, max_drop_pct=0, drop_frequency_pct=40)
    with pytest.raises(ValueError):
        apply_random_drop_transform(tones, dimension=ToneDimension.AMPLITUDE, max_drop_pct=101, drop_frequency_pct=40)


def test_random_drop_rejects_out_of_range_drop_frequency_pct():
    tones = _build_reference_tones()

    with pytest.raises(ValueError):
        apply_random_drop_transform(tones, dimension=ToneDimension.AMPLITUDE, max_drop_pct=50, drop_frequency_pct=0)
    with pytest.raises(ValueError):
        apply_random_drop_transform(tones, dimension=ToneDimension.AMPLITUDE, max_drop_pct=50, drop_frequency_pct=101)


def test_random_drop_rejects_non_integer_max_drop_pct():
    tones = _build_reference_tones()

    with pytest.raises(ValueError):
        apply_random_drop_transform(
            tones, dimension=ToneDimension.AMPLITUDE,
            max_drop_pct=50.0, # type: ignore[arg-type]
            drop_frequency_pct=40
        )


def test_random_drop_rejects_non_integer_drop_frequency_pct():
    tones = _build_reference_tones()

    with pytest.raises(ValueError):
        apply_random_drop_transform(
            tones,
            dimension=ToneDimension.AMPLITUDE,
            max_drop_pct=50,
            drop_frequency_pct=40.0,  # type: ignore[arg-type]
        )
