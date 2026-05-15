import math
import random

import pytest

from transforms.profiles import (
    CellularAutomataProfile,
    RandomDropProfile,
    RidgedMultifractalProfile,
    StochasticProfile,
    TerracedBrownianProfile,
    WeierstrassProfile,
    _get_next_cellular_state,
    _sample_ridged_noise,
)


class ConformingProfile:
    def generate(self, length: int) -> list[float]:
        return [0.0] * length


class NonConformingProfile:
    def produce(self, length: int) -> list[float]:
        return [0.0] * length


def test_stochastic_profile_is_importable():
    assert StochasticProfile is not None


def test_conforming_class_matches_protocol_structure():
    instance = ConformingProfile()
    assert isinstance(instance, StochasticProfile)


def test_non_conforming_class_does_not_match_protocol_structure():
    instance = NonConformingProfile()
    assert not isinstance(instance, StochasticProfile)


def test_cellular_next_state_rule_zero_clears_all_cells():
    state = [1, 0, 1, 1]
    all_cells_off_rule = 0

    assert _get_next_cellular_state(state, rule=all_cells_off_rule) == [0, 0, 0, 0]


def test_cellular_next_state_rule_255_fills_all_cells():
    state = [1, 0, 1, 1]
    all_cells_on_rule = 255

    assert _get_next_cellular_state(state, rule=all_cells_on_rule) == [1, 1, 1, 1]


def test_sample_ridged_noise_single_octave_matches_octave_value_times_amplitude():
    amplitude = 0.5
    sample_index = 0
    phase = 0.0
    rate = 1.0
    sample = _sample_ridged_noise(
        index=sample_index,
        phases=[phase],
        rates=[rate],
        amplitudes=[amplitude],
    )

    expected_octave_value = 1.0 - abs(math.sin(sample_index * rate + phase))
    assert sample == pytest.approx(expected_octave_value * amplitude)


def test_weierstrass_profile_empty_length_returns_empty_list():
    profile = WeierstrassProfile(seed=3)

    assert profile.generate(0) == []


def test_weierstrass_profile_with_zero_iterations_uses_safe_normalization():
    random_seed = 3
    no_iterations = 0
    generated_length = 3
    profile = WeierstrassProfile(seed=random_seed, iterations=no_iterations)

    assert profile.generate(generated_length) == [0.0, 0.0, 0.0]


def test_weierstrass_profile_is_deterministic_and_bounded():
    profile = WeierstrassProfile(seed=5, iterations=4)
    generated_a = profile.generate(5)
    generated_b = profile.generate(5)

    assert generated_a == generated_b
    assert len(generated_a) == 5
    assert all(-1.0 <= value <= 1.0 for value in generated_a)


def test_terraced_brownian_profile_without_quantization_uses_raw_walk_values():
    seed = 13
    length = 4
    step_size = 0.25
    profile = TerracedBrownianProfile(
        seed=seed,
        step_size=step_size,
        quantize_resolution=0.0,
    )

    expected_values = []
    current_value = 0.0
    rng = random.Random(seed)
    for _ in range(length):
        current_value += rng.uniform(-step_size, step_size)
        current_value = max(-1.0, min(1.0, current_value))
        expected_values.append(current_value)

    assert profile.generate(length) == pytest.approx(expected_values)


def test_terraced_brownian_profile_quantizes_and_clamps_values():
    random_seed = 2
    oversized_step = 3.0
    half_step_quantization = 0.5
    generated_length = 8
    profile = TerracedBrownianProfile(
        seed=random_seed,
        step_size=oversized_step,
        quantize_resolution=half_step_quantization,
    )
    generated = profile.generate(generated_length)

    assert len(generated) == generated_length
    assert all(-1.0 <= value <= 1.0 for value in generated)
    assert all((value * 2).is_integer() for value in generated)


def test_cellular_automata_profile_rule_zero_emits_all_negative_values():
    all_cells_off_rule = 0
    random_seed = 1
    automaton_width = 5
    generated_length = 4
    expected_evolved_signal = [-1.0, -1.0, -1.0]
    profile = CellularAutomataProfile(rule=all_cells_off_rule, seed=random_seed, width=automaton_width)
    generated = profile.generate(generated_length)

    assert len(generated) == generated_length
    assert generated[1:] == expected_evolved_signal


def test_cellular_automata_profile_rule_255_emits_all_positive_values():
    all_cells_on_rule = 255
    random_seed = 1
    automaton_width = 5
    generated_length = 4
    expected_evolved_signal = [1.0, 1.0, 1.0]
    profile = CellularAutomataProfile(rule=all_cells_on_rule, seed=random_seed, width=automaton_width)
    generated = profile.generate(generated_length)

    assert len(generated) == generated_length
    assert generated[1:] == expected_evolved_signal


def test_cellular_automata_profile_outputs_only_binary_extremes():
    wolfram_rule_30 = 30
    random_seed = 9
    automaton_width = 7
    generated_length = 6
    profile = CellularAutomataProfile(rule=wolfram_rule_30, seed=random_seed, width=automaton_width)
    generated = profile.generate(generated_length)

    assert len(generated) == generated_length
    assert set(generated).issubset({-1.0, 1.0})


def test_ridged_multifractal_profile_with_zero_octaves_returns_all_zeros():
    random_seed = 8
    no_octaves = 0
    generated_length = 5
    profile = RidgedMultifractalProfile(seed=random_seed, octaves=no_octaves)

    assert profile.generate(generated_length) == [0.0] * generated_length


def test_ridged_multifractal_profile_threshold_one_emits_full_drop_only_for_strict_overflow():
    random_seed = 8
    single_octave = 1
    full_drop_threshold = 1.0
    generated_length = 5
    profile = RidgedMultifractalProfile(
        seed=random_seed,
        octaves=single_octave,
        drop_when_noise_above=full_drop_threshold,
    )

    assert profile.generate(generated_length) == [0.0] * generated_length


def test_ridged_multifractal_profile_values_stay_in_expected_range():
    random_seed = 4
    octave_count = 3
    medium_ridge_density = 0.6
    low_drop_threshold = 0.3
    generated_length = 10
    profile = RidgedMultifractalProfile(
        seed=random_seed,
        octaves=octave_count,
        ridge_density=medium_ridge_density,
        drop_when_noise_above=low_drop_threshold,
    )
    generated = profile.generate(generated_length)

    assert len(generated) == generated_length
    assert all(-1.0 <= value <= 0.0 for value in generated)


def test_random_drop_profile_zero_drop_rate_emits_no_drops():
    random_seed = 6
    no_drop_rate = 0.0
    generated_length = 5
    profile = RandomDropProfile(seed=random_seed, drop_rate=no_drop_rate)

    assert profile.generate(generated_length) == [0.0] * generated_length


def test_random_drop_profile_full_drop_rate_emits_only_negative_values():
    random_seed = 6
    guaranteed_drop_rate = 1.0
    generated_length = 8
    profile = RandomDropProfile(seed=random_seed, drop_rate=guaranteed_drop_rate)
    generated = profile.generate(generated_length)

    assert len(generated) == generated_length
    assert all(-1.0 <= value <= 0.0 for value in generated)
    assert any(value < 0.0 for value in generated)
