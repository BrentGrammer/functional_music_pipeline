import pytest

from score_model.tone import Tone
from transforms.base import ToneDimension
from transforms.complexity.cellular_automata import apply_cellular_automata_transform
from transforms.complexity.random_drop import apply_random_drop_transform
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


@pytest.mark.parametrize(
    ("transform", "kwargs"),
    [
        pytest.param(
            apply_weierstrass_transform,
            {
                "dimension": ToneDimension.FREQUENCY,
                "max_deviation": 0.1,
                "seed": 42,
                "amplitude_scaling": 0.5,
                "ripples_per_wave": 3.0,
                "iterations": 10,
            },
            id="weierstrass",
        ),
        pytest.param(
            apply_cellular_automata_transform,
            {
                "dimension": ToneDimension.FREQUENCY,
                "max_deviation": 0.1,
                "rule": 30,
                "seed": 42,
                "width": 31,
            },
            id="cellular_automata",
        ),
        pytest.param(
            apply_random_drop_transform,
            {
                "dimension": ToneDimension.FREQUENCY,
                "max_deviation": 0.1,
                "seed": 42,
                "drop_rate": 0.2,
            },
            id="random_drop",
        ),
    ],
)
def test_seeded_complexity_transforms_are_repeatable(transform, kwargs):
    tones = _build_reference_tones()

    result_a = transform(tones, **kwargs)
    result_b = transform(tones, **kwargs)

    assert _snapshot(result_a) == _snapshot(result_b)
    assert len(result_a) == len(tones)


@pytest.mark.parametrize(
    ("transform", "kwargs"),
    [
        pytest.param(
            apply_weierstrass_transform,
            {
                "dimension": ToneDimension.FREQUENCY,
                "max_deviation": 0.0,
                "seed": 7,
                "iterations": 10,
            },
            id="weierstrass-zero-deviation",
        ),
        pytest.param(
            apply_cellular_automata_transform,
            {
                "dimension": ToneDimension.FREQUENCY,
                "max_deviation": 0.0,
                "rule": 30,
                "seed": 7,
                "width": 31,
            },
            id="cellular_automata-zero-deviation",
        ),
        pytest.param(
            apply_random_drop_transform,
            {
                "dimension": ToneDimension.FREQUENCY,
                "max_deviation": 0.1,
                "seed": 7,
                "drop_rate": 0.0,
            },
            id="random_drop-zero-rate",
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
            apply_weierstrass_transform,
            {"dimension": ToneDimension.FREQUENCY, "max_deviation": 0.1, "seed": 42},
            id="weierstrass",
        ),
        pytest.param(
            apply_cellular_automata_transform,
            {"dimension": ToneDimension.FREQUENCY, "max_deviation": 0.1, "seed": 42},
            id="cellular_automata",
        ),
        pytest.param(
            apply_random_drop_transform,
            {"dimension": ToneDimension.FREQUENCY, "max_deviation": 0.1, "seed": 42},
            id="random_drop",
        ),
    ],
)
def test_complexity_transforms_return_empty_output_for_empty_input(transform, kwargs):
    assert transform([], **kwargs) == []


def test_cellular_automata_frequency_modulates_without_touching_other_dimensions():
    tones = [
        Tone(frequency=440.0, duration=1.0, amplitude=0.5),
        Tone(frequency=880.0, duration=2.0, amplitude=0.8),
    ]

    result = apply_cellular_automata_transform(
        tones,
        dimension=ToneDimension.FREQUENCY,
        max_deviation=0.5,
        rule=0,
        seed=1,
        width=5,
    )

    assert result[1].frequency == pytest.approx(440.0)
    assert result[1].duration == pytest.approx(tones[1].duration)
    assert result[1].amplitude == pytest.approx(tones[1].amplitude)


def test_cellular_automata_duration_modulates_without_touching_other_dimensions():
    tones = [
        Tone(frequency=440.0, duration=1.0, amplitude=0.5),
        Tone(frequency=880.0, duration=2.0, amplitude=0.8),
    ]

    result = apply_cellular_automata_transform(
        tones,
        dimension=ToneDimension.DURATION,
        max_deviation=0.5,
        rule=0,
        seed=1,
        width=5,
    )

    assert result[1].duration == pytest.approx(1.0)
    assert result[1].frequency == pytest.approx(tones[1].frequency)
    assert result[1].amplitude == pytest.approx(tones[1].amplitude)


def test_cellular_automata_amplitude_modulation_clamps_at_valid_bounds():
    tones = [
        Tone(frequency=440.0, duration=1.0, amplitude=0.8),
        Tone(frequency=880.0, duration=2.0, amplitude=0.8),
    ]

    result = apply_cellular_automata_transform(
        tones,
        dimension=ToneDimension.AMPLITUDE,
        max_deviation=0.5,
        rule=255,
        seed=1,
        width=5,
    )

    assert result[1].amplitude == pytest.approx(1.0)
    assert result[1].frequency == pytest.approx(tones[1].frequency)
    assert result[1].duration == pytest.approx(tones[1].duration)
