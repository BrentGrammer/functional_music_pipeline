import math

import pytest

from composition.parser import generate_score_plan
from composition.transformer import transform_score
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.traversal import flatten_phrase_tones
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import PhraseTransformContext
from transforms.geological.fragment import (
    FRAGMENT_PARAMS_SPEC,
    FragmentParams,
    _select_chunks_to_damage,
    fragment_phrase_transform,
)
from transforms.registry import PHRASE_TRANSFORMS


def test_fragment_is_registered_as_phrase_transform():
    assert "fragment" in PHRASE_TRANSFORMS


def test_fragment_params_accept_omitted_pattern_key():
    params = FRAGMENT_PARAMS_SPEC.parse_params(
        {"damage_pct": 0, "damage_tones_chunk_size": 4},
        transform_name="fragment",
    )

    assert params == FragmentParams(damage_pct=0, damage_tones_chunk_size=4, repeatable_damage_key=None)


def test_fragment_params_accept_string_pattern_key():
    repeatable_damage_key = "pattern-key-a"

    params = FRAGMENT_PARAMS_SPEC.parse_params(
        {"damage_pct": 0, "damage_tones_chunk_size": 4, "repeatable_damage_key": repeatable_damage_key},
        transform_name="fragment",
    )

    assert params == FragmentParams(damage_pct=0, damage_tones_chunk_size=4, repeatable_damage_key=repeatable_damage_key)


@pytest.mark.parametrize("invalid_pattern_key", [123, 4.5, True, None, ["string-in-list"]])
def test_fragment_params_reject_invalid_pattern_key_values(invalid_pattern_key: object):
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
        FragmentParams(damage_pct=0, damage_tones_chunk_size=4, repeatable_damage_key=None),
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
    ):
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
