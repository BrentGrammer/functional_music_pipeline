import math
import random

import pytest

from composition.parser import generate_score_plan
from composition.transformer import transform_score
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones
from score_model.voice import Voice
from transforms.base import PhraseTransformContext, ToneDimension
from transforms.geological.fragment import (
    FRAGMENT_PARAMS_SPEC,
    FragmentParams,
    _damage_selected_tone_across_dimensions,
    _select_chunks_to_damage,
    fragment_phrase_transform,
    fragment_transform,
)
from transforms.registry import PHRASE_TRANSFORMS


class PredictableRandom(random.Random):
    def __init__(self, random_values: list[float], uniform_values: list[float] | None = None):
        super().__init__()
        self.random_values = random_values
        self.uniform_values = uniform_values or []

    def random(self) -> float:
        return self.random_values.pop(0)

    def uniform(self, _low: float, _high: float) -> float:
        return self.uniform_values.pop(0)


def test_fragment_is_registered_as_phrase_transform():
    assert "fragment" in PHRASE_TRANSFORMS


def test_fragment_params_accept_omitted_pattern_key():
    params = FRAGMENT_PARAMS_SPEC.parse_params(
        {"damage_pct": 0, "damage_tones_chunk_size": 4},
        transform_name="fragment",
    )

    assert params == FragmentParams(damage_pct=0, damage_tones_chunk_size=4, dimension=None, repeatable_damage_key=None)


def test_fragment_params_accept_string_pattern_key():
    repeatable_damage_key = "pattern-key-a"

    params = FRAGMENT_PARAMS_SPEC.parse_params(
        {"damage_pct": 0, "damage_tones_chunk_size": 4, "repeatable_damage_key": repeatable_damage_key},
        transform_name="fragment",
    )

    assert params == FragmentParams(
        damage_pct=0,
        damage_tones_chunk_size=4,
        dimension=None,
        repeatable_damage_key=repeatable_damage_key,
    )


def test_fragment_params_accept_explicit_dimension():
    params = FRAGMENT_PARAMS_SPEC.parse_params(
        {"damage_pct": 0, "damage_tones_chunk_size": 4, "dimension": ToneDimension.DURATION},
        transform_name="fragment",
    )

    assert params == FragmentParams(
        damage_pct=0,
        damage_tones_chunk_size=4,
        dimension=ToneDimension.DURATION,
        repeatable_damage_key=None,
    )


@pytest.mark.parametrize("invalid_pattern_key", [123, 4.5, True, None, ["string-in-list"]])
def test_fragment_params_reject_invalid_pattern_key_values(invalid_pattern_key: object) -> None:
    with pytest.raises(ValueError):
        FRAGMENT_PARAMS_SPEC.parse_params(
            {"damage_pct": 0, "damage_tones_chunk_size": 4, "repeatable_damage_key": invalid_pattern_key},
            transform_name="fragment",
        )


def test_fragment_damage_pct_zero_returns_equivalent_phrase():
    original_tones = [
        Tone(220.0, duration=0.5, amplitude=0.25),
        Tone(330.0, duration=0.25, amplitude=0.5),
    ]
    phrase = Phrase(motifs=[Motif(name="fragment-target", tones=original_tones)])
    score = Score(voices=[Voice(phrases=[phrase])])
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    result = fragment_phrase_transform(
        context,
        FragmentParams(damage_pct=0, damage_tones_chunk_size=4, dimension=None, repeatable_damage_key=None),
    )

    result_tones = flatten_phrase_tones(result)
    assert result.motifs[0].name == "<transformed>"
    assert [tone.frequency for tone in result_tones] == pytest.approx([original_tones[0].frequency, original_tones[1].frequency])
    assert [tone.duration for tone in result_tones] == pytest.approx([original_tones[0].duration, original_tones[1].duration])
    assert [tone.amplitude for tone in result_tones] == pytest.approx([original_tones[0].amplitude, original_tones[1].amplitude])


class TestFragmentSelection:
    def test_fragment_selection_returns_no_chunks_for_an_empty_phrase(self):
        selected_chunks = _select_chunks_to_damage(
            tone_count=0,
            damage_pct=50,
            damage_tones_chunk_size=4,
            repeatable_damage_key="pattern-key-a",
        )

        assert selected_chunks == []

    def test_fragment_selection_returns_no_chunks_when_damage_pct_is_zero(self):
        selected_chunks = _select_chunks_to_damage(
            tone_count=8,
            damage_pct=0,
            damage_tones_chunk_size=4,
            repeatable_damage_key="pattern-key-a",
        )

        assert selected_chunks == []

    def test_fragment_selection_shrinks_the_chunk_when_the_damage_target_count_is_smaller_than_chunk_size(self):
        tone_count = 20
        damage_pct = 10
        # Add 0.5 before floor(...) so the fractional damage target rounds to the nearest whole tone count.
        expected_damaged_tone_count = math.floor((tone_count * damage_pct / 100) + 0.5)
        configured_chunk_size = expected_damaged_tone_count + 2

        selected_chunks = _select_chunks_to_damage(
            tone_count=tone_count,
            damage_pct=damage_pct,
            damage_tones_chunk_size=configured_chunk_size,
            repeatable_damage_key="pattern-key-a",
        )
        selected_chunk = selected_chunks[0]
        first_selected_position, second_selected_position = selected_chunk

        # Since the total damage budget is only 2 tones, the selector cannot create a 4-tone chunk without violating damage_pct. So the only valid outcome is:
        # - one chunk
        # - that chunk contains 2 adjacent tone positions

        max_chunks_given_damage_pct_constraint = 1
        assert len(selected_chunks) == max_chunks_given_damage_pct_constraint
        assert len(selected_chunk) == expected_damaged_tone_count
        assert second_selected_position == first_selected_position + 1

    def test_fragment_selection_repeats_full_chunks_until_the_remaining_budget_based_on_damage_pct_requires_a_smaller_chunk(self):
        tone_count = 20
        damage_pct = 30
        configured_chunk_size = 4
        # Add 0.5 before floor(...) so the fractional damage target rounds to the nearest whole tone count.
        configured_damage_budget = math.floor((tone_count * (damage_pct / 100)) + 0.5) # 6 is 30% of 20 tones
        # The first damaged region should use the normal configured chunk width.
        # Whatever damage budget remains after that becomes the smaller second chunk.
        num_tones_still_needing_damage_after_first_full_chunk_applied = configured_damage_budget - configured_chunk_size

        selected_chunks = _select_chunks_to_damage(
            tone_count=tone_count,
            damage_pct=damage_pct,
            damage_tones_chunk_size=configured_chunk_size,
            repeatable_damage_key="pattern-key-a",
        )
        selected_chunk_sizes = sorted(len(chunk) for chunk in selected_chunks)
        selected_tone_count_to_damage = sum(selected_chunk_sizes)

        assert len(selected_chunks) == 2
        assert selected_chunk_sizes == sorted([configured_chunk_size, num_tones_still_needing_damage_after_first_full_chunk_applied])
        assert selected_tone_count_to_damage == configured_damage_budget

    def test_damage_chunk_selection_never_selects_the_same_tone_position_twice(self):
        tone_count = 20
        damage_pct = 60
        configured_chunk_size = 4

        selected_chunks = _select_chunks_to_damage(
            tone_count=tone_count,
            damage_pct=damage_pct,
            damage_tones_chunk_size=configured_chunk_size,
            repeatable_damage_key="pattern-key-a",
        )

        selected_positions = [position for chunk in selected_chunks for position in chunk]
        unique_selected_positions = set(selected_positions)

        assert len(selected_positions) == len(unique_selected_positions)

    @pytest.mark.parametrize(
        ("tone_count", "damage_pct", "damage_tones_chunk_size", "expected_selected_count"),
        [
            (20, 10, 4, 2),
            (20, 30, 4, 6),
            (9, 1, 4, 1),
        ],
    )
    def test_damage_chunk_selection_matches_the_damage_pct_target_count(
        self,
        tone_count: int,
        damage_pct: int,
        damage_tones_chunk_size: int,
        expected_selected_count: int,
    ) -> None:
        selected_chunks = _select_chunks_to_damage(
            tone_count=tone_count,
            damage_pct=damage_pct,
            damage_tones_chunk_size=damage_tones_chunk_size,
            repeatable_damage_key="pattern-key-a",
        )

        selected_positions = [position for chunk in selected_chunks for position in chunk]
        selected_tone_count = len(selected_positions)

        assert selected_tone_count == expected_selected_count

    def test_damage_chunk_selection_with_the_same_repeatable_damage_key_repeats_the_same_chunks(self):
        first_chunks = _select_chunks_to_damage(
            tone_count=20,
            damage_pct=40,
            damage_tones_chunk_size=4,
            repeatable_damage_key="pattern-key-a",
        )
        second_chunks = _select_chunks_to_damage(
            tone_count=20,
            damage_pct=40,
            damage_tones_chunk_size=4,
            repeatable_damage_key="pattern-key-a",
        )

        assert first_chunks == second_chunks


class TestFragmentMultiDimensionalDamage:
    def test_multi_dimensional_damage_can_remove_a_selected_tone(self):
        original_tone = Tone(440.0, duration=1.0, amplitude=0.5)
        removal_roll_hits = 0.0

        transformed_tones = _damage_selected_tone_across_dimensions(
            original_tone,
            PredictableRandom(random_values=[removal_roll_hits]),
        )

        assert len(transformed_tones) == 1
        assert transformed_tones[0].frequency == 0.0
        assert transformed_tones[0].duration == pytest.approx(original_tone.duration)
        assert transformed_tones[0].amplitude == 0.0

    def test_multi_dimensional_damage_can_shorten_without_softening_a_selected_tone(self):
        original_tone = Tone(440.0, duration=1.0, amplitude=0.5)
        removal_roll_misses = 0.99
        duration_roll_hits = 0.0
        amplitude_roll_misses = 0.99
        shortened_duration = 0.5

        transformed_tones = _damage_selected_tone_across_dimensions(
            original_tone,
            PredictableRandom(
                random_values=[removal_roll_misses, duration_roll_hits, amplitude_roll_misses],
                uniform_values=[shortened_duration],
            ),
        )
        damaged_tone, trailing_silence = transformed_tones

        assert damaged_tone.frequency == original_tone.frequency
        assert damaged_tone.duration == pytest.approx(shortened_duration)
        assert damaged_tone.amplitude == original_tone.amplitude
        assert trailing_silence.frequency == 0.0
        assert trailing_silence.amplitude == 0.0
        assert sum(tone.duration for tone in transformed_tones) == pytest.approx(original_tone.duration)

    def test_multi_dimensional_damage_can_soften_without_shortening_a_selected_tone(self):
        original_tone = Tone(440.0, duration=1.0, amplitude=0.5)
        # low values hit to trigger a change, high values miss.
        removal_roll_misses = 0.99
        duration_roll_misses = 0.99
        amplitude_roll_hits = 0.0
        amplitude_reduction_decibels = 6.0

        transformed_tones = _damage_selected_tone_across_dimensions(
            original_tone,
            PredictableRandom(
                random_values=[removal_roll_misses, duration_roll_misses, amplitude_roll_hits],
                uniform_values=[amplitude_reduction_decibels],
            ),
        )

        assert len(transformed_tones) == 1
        assert transformed_tones[0].frequency == original_tone.frequency
        assert transformed_tones[0].duration == pytest.approx(original_tone.duration)
        assert transformed_tones[0].amplitude < original_tone.amplitude

    def test_multi_dimensional_damage_can_shorten_and_soften_the_same_selected_tone(self):
        original_tone = Tone(440.0, duration=1.0, amplitude=0.5)
        removal_roll_misses = 0.99
        duration_roll_hits = 0.0
        amplitude_roll_hits = 0.0
        shortened_duration = 0.5
        amplitude_reduction_decibels = 6.0

        transformed_tones = _damage_selected_tone_across_dimensions(
            original_tone,
            PredictableRandom(
                random_values=[removal_roll_misses, duration_roll_hits, amplitude_roll_hits],
                uniform_values=[shortened_duration, amplitude_reduction_decibels],
            ),
        )
        damaged_tone, trailing_silence = transformed_tones

        assert damaged_tone.frequency == original_tone.frequency
        assert damaged_tone.duration == pytest.approx(shortened_duration)
        assert damaged_tone.amplitude < original_tone.amplitude
        assert trailing_silence.frequency == 0.0
        assert trailing_silence.amplitude == 0.0
        assert sum(tone.duration for tone in transformed_tones) == pytest.approx(original_tone.duration)

    def test_multi_dimensional_damage_can_force_duration_when_duration_and_amplitude_rolls_miss(self):
        original_tone = Tone(440.0, duration=1.0, amplitude=0.5)
        removal_roll_misses = 0.99
        duration_roll_misses = 0.99
        amplitude_roll_misses = 0.99
        fallback_roll_selects_duration = 0.0
        shortened_duration = 0.5

        transformed_tones = _damage_selected_tone_across_dimensions(
            original_tone,
            PredictableRandom(
                random_values=[
                    removal_roll_misses,
                    duration_roll_misses,
                    amplitude_roll_misses,
                    fallback_roll_selects_duration,
                ],
                uniform_values=[shortened_duration],
            ),
        )
        damaged_tone, trailing_silence = transformed_tones

        assert damaged_tone.frequency == original_tone.frequency
        assert damaged_tone.duration == pytest.approx(shortened_duration)
        assert damaged_tone.amplitude == original_tone.amplitude
        assert trailing_silence.frequency == 0.0
        assert trailing_silence.amplitude == 0.0
        assert sum(tone.duration for tone in transformed_tones) == pytest.approx(original_tone.duration)

    def test_multi_dimensional_damage_can_force_amplitude_when_duration_and_amplitude_rolls_miss(self):
        original_tone = Tone(440.0, duration=1.0, amplitude=0.5)
        removal_roll_misses = 0.99
        duration_roll_misses = 0.99
        amplitude_roll_misses = 0.99
        fallback_roll_selects_amplitude = 0.99
        amplitude_reduction_decibels = 6.0

        transformed_tones = _damage_selected_tone_across_dimensions(
            original_tone,
            PredictableRandom(
                random_values=[
                    removal_roll_misses,
                    duration_roll_misses,
                    amplitude_roll_misses,
                    fallback_roll_selects_amplitude,
                ],
                uniform_values=[amplitude_reduction_decibels],
            ),
        )

        assert len(transformed_tones) == 1
        assert transformed_tones[0].frequency == original_tone.frequency
        assert transformed_tones[0].duration == pytest.approx(original_tone.duration)
        assert transformed_tones[0].amplitude < original_tone.amplitude


class TestFragmentDimensionBoundDamage:
    def test_frequency_dimension_replaces_selected_tones_with_silence(self):
        original_tones = [
            Tone(220.0, duration=0.5, amplitude=0.25),
            Tone(330.0, duration=0.25, amplitude=0.5),
        ]

        transformed_tones = fragment_transform(
            original_tones,
            damage_pct=100,
            damage_tones_chunk_size=2,
            dimension=ToneDimension.FREQUENCY,
            repeatable_damage_key="pattern-key-a",
        )
        all_silent_with_100_pct_damage = [0.0, 0.0]
        assert [tone.frequency for tone in transformed_tones] == all_silent_with_100_pct_damage
        assert [tone.duration for tone in transformed_tones] == pytest.approx([0.5, 0.25])
        assert [tone.amplitude for tone in transformed_tones] == all_silent_with_100_pct_damage

    def test_duration_dimension_shortens_selected_tones_and_preserves_the_phrase_timeline(self):
        original_tones = [
            Tone(220.0, duration=0.5, amplitude=0.25),
            Tone(330.0, duration=0.25, amplitude=0.5),
        ]
        original_total_duration = sum(tone.duration for tone in original_tones)

        transformed_tones = fragment_transform(
            original_tones,
            damage_pct=100,
            damage_tones_chunk_size=2,
            dimension=ToneDimension.DURATION,
            repeatable_damage_key="pattern-key-a",
        )

        damaged_first_tone, first_trailing_silence, damaged_second_tone, second_trailing_silence = transformed_tones

        assert sum(tone.duration for tone in transformed_tones) == pytest.approx(original_total_duration)
        
        assert damaged_first_tone.frequency == original_tones[0].frequency
        assert damaged_second_tone.frequency == original_tones[1].frequency
         
        assert damaged_first_tone.amplitude == original_tones[0].amplitude
        assert damaged_second_tone.amplitude == original_tones[1].amplitude

        assert damaged_first_tone.duration < original_tones[0].duration
        assert damaged_second_tone.duration < original_tones[1].duration
        
        assert first_trailing_silence.frequency == 0.0
        assert first_trailing_silence.amplitude == 0.0
        
        assert second_trailing_silence.frequency == 0.0
        assert second_trailing_silence.amplitude == 0.0

    def test_amplitude_dimension_reduces_selected_tone_amplitudes_only(self):
        tone_1_frequency = 220.0
        tone_2_frequency = 330.0

        tone_1_amplitude = 0.25
        tone_2_amplitude = 0.5

        tone_1_duration = 0.5
        tone_2_duration = 0.25

        original_tones = [
            Tone(tone_1_frequency, duration=tone_1_duration, amplitude=tone_1_amplitude),
            Tone(tone_2_frequency, duration=tone_2_duration, amplitude=tone_2_amplitude),
        ]

        transformed_tones = fragment_transform(
            original_tones,
            damage_pct=100,
            damage_tones_chunk_size=2,
            dimension=ToneDimension.AMPLITUDE,
            repeatable_damage_key="pattern-key-a",
        )

        assert [tone.frequency for tone in transformed_tones] == pytest.approx([tone_1_frequency, tone_2_frequency])
        assert [tone.duration for tone in transformed_tones] == pytest.approx([tone_1_duration, tone_2_duration])
        assert transformed_tones[0].amplitude < tone_1_amplitude
        assert transformed_tones[1].amplitude < tone_2_amplitude


class TestFragmentAcceptance:
    def test_fragment_with_same_repeatable_damage_key_repeats_the_same_damage_layout(self):
        pattern_key = "pattern-key-a"
        ruin_seed_snapshot = [
            (220.0, 1.0, 0.5),
            (246.94, 1.0, 0.5),
            (261.63, 1.0, 0.5),
            (293.66, 1.0, 0.5),
            (329.63, 1.0, 0.5),
            (349.23, 1.0, 0.5),
            (392.0, 1.0, 0.5),
            (440.0, 1.0, 0.5),
        ]
        ruin_seed_motif = [f"{frequency}:{duration}" for frequency, duration, _ in ruin_seed_snapshot]

        composition_document = {
            "motifs": {
                "ruin_seed": ruin_seed_motif
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["ruin_seed"],
                                "transforms": [
                                    {
                                        "name": "fragment",
                                        "params": {"damage_pct": 50, "damage_tones_chunk_size": 2, "repeatable_damage_key": pattern_key},
                                    }
                                ],
                            },
                            {
                                "motifs": ["ruin_seed"],
                                "transforms": [
                                    {
                                        "name": "fragment",
                                        "params": {"damage_pct": 50, "damage_tones_chunk_size": 2, "repeatable_damage_key": pattern_key},
                                    }
                                ],
                            },
                        ]
                    }
                ],
                "score_transforms": [],
            },
        }

        score = transform_score(generate_score_plan(composition_document))

        first_phrase_tones = flatten_phrase_tones(score.voices[0].phrases[0])
        second_phrase_tones = flatten_phrase_tones(score.voices[0].phrases[1])

        first_snapshot = [(tone.frequency, tone.duration, tone.amplitude) for tone in first_phrase_tones]
        second_snapshot = [(tone.frequency, tone.duration, tone.amplitude) for tone in second_phrase_tones]

        assert first_snapshot == second_snapshot

    def test_fragment_with_different_repeatable_damage_keys_can_change_the_fragmented_result(self):
        pattern_key_a = "pattern-key-a"
        different_pattern_key = "pattern-key-b"
        ruin_seed_snapshot = [
            (220.0, 1.0, 0.5),
            (246.94, 1.0, 0.5),
            (261.63, 1.0, 0.5),
            (293.66, 1.0, 0.5),
            (329.63, 1.0, 0.5),
            (349.23, 1.0, 0.5),
            (392.0, 1.0, 0.5),
            (440.0, 1.0, 0.5),
        ]
        ruin_seed_motif = [f"{frequency}:{duration}" for frequency, duration, _ in ruin_seed_snapshot]

        composition_document = {
            "motifs": {
                "ruin_seed": ruin_seed_motif
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["ruin_seed"],
                                "transforms": [
                                    {
                                        "name": "fragment",
                                        "params": {"damage_pct": 50, "damage_tones_chunk_size": 2, "repeatable_damage_key": pattern_key_a},
                                    }
                                ],
                            },
                            {
                                "motifs": ["ruin_seed"],
                                "transforms": [
                                    {
                                        "name": "fragment",
                                        "params": {"damage_pct": 50, "damage_tones_chunk_size": 2, "repeatable_damage_key": different_pattern_key},
                                    }
                                ],
                            },
                        ]
                    }
                ],
                "score_transforms": [],
            },
        }

        score = transform_score(generate_score_plan(composition_document))

        first_phrase_tones = flatten_phrase_tones(score.voices[0].phrases[0])
        second_phrase_tones = flatten_phrase_tones(score.voices[0].phrases[1])

        first_snapshot = [(tone.frequency, tone.duration, tone.amplitude) for tone in first_phrase_tones]
        second_snapshot = [(tone.frequency, tone.duration, tone.amplitude) for tone in second_phrase_tones]

        assert first_snapshot != second_snapshot

    def test_fragment_preserves_phrase_timeline_while_audibly_damaging_the_phrase(self):
        ruin_seed_snapshot = [
            (220.0, 1.0, 0.5),
            (246.94, 1.0, 0.5),
            (261.63, 1.0, 0.5),
            (293.66, 1.0, 0.5),
            (329.63, 1.0, 0.5),
            (349.23, 1.0, 0.5),
            (392.0, 1.0, 0.5),
            (440.0, 1.0, 0.5),
        ]
        ruin_seed_motif = [f"{frequency}:{duration}" for frequency, duration, _ in ruin_seed_snapshot]
        original_total_duration = sum(duration for _, duration, _ in ruin_seed_snapshot)

        composition_document = {
            "motifs": {
                "ruin_seed": ruin_seed_motif
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["ruin_seed"],
                                "transforms": [
                                    {
                                        "name": "fragment",
                                        "params": {"damage_pct": 50, "damage_tones_chunk_size": 2, "repeatable_damage_key": "pattern-key-a"},
                                    }
                                ],
                            }
                        ]
                    }
                ],
                "score_transforms": [],
            },
        }

        score = transform_score(generate_score_plan(composition_document))
        transformed_tones = flatten_phrase_tones(score.voices[0].phrases[0])
        transformed_snapshot = [(tone.frequency, tone.duration, tone.amplitude) for tone in transformed_tones]
        transformed_total_duration = sum(tone.duration for tone in transformed_tones)

        assert transformed_total_duration == pytest.approx(original_total_duration)
        assert transformed_snapshot != ruin_seed_snapshot
