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
from transforms.geological.fragment import FRAGMENT_PARAMS_SPEC, FragmentParams, fragment_phrase_transform
from transforms.registry import PHRASE_TRANSFORMS


def test_fragment_is_registered_as_phrase_transform():
    assert "fragment" in PHRASE_TRANSFORMS


def test_fragment_params_accept_omitted_pattern_key():
    params = FRAGMENT_PARAMS_SPEC.parse_params(
        {"damage_pct": 0, "damage_tones_chunk_size": 4},
        transform_name="fragment",
    )

    assert params == FragmentParams(damage_pct=0, damage_tones_chunk_size=4, damage_pattern_key=None)


def test_fragment_params_accept_string_pattern_key():
    damage_pattern_key = "pattern-key-a"

    params = FRAGMENT_PARAMS_SPEC.parse_params(
        {"damage_pct": 0, "damage_tones_chunk_size": 4, "damage_pattern_key": damage_pattern_key},
        transform_name="fragment",
    )

    assert params == FragmentParams(damage_pct=0, damage_tones_chunk_size=4, damage_pattern_key=damage_pattern_key)


@pytest.mark.parametrize("invalid_pattern_key", [123, 4.5, True, None, ["string-in-list"]])
def test_fragment_params_reject_invalid_pattern_key_values(invalid_pattern_key: object):
    with pytest.raises(ValueError):
        FRAGMENT_PARAMS_SPEC.parse_params(
            {"damage_pct": 0, "damage_tones_chunk_size": 4, "damage_pattern_key": invalid_pattern_key},
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
        FragmentParams(damage_pct=0, damage_tones_chunk_size=4, damage_pattern_key=None),
    )

    result_tones = flatten_phrase_tones(result)
    assert result.motifs[0].name == "<transformed>"
    assert [tone.frequency for tone in result_tones] == pytest.approx([original_tones[0].frequency, original_tones[1].frequency])
    assert [tone.duration for tone in result_tones] == pytest.approx([original_tones[0].duration, original_tones[1].duration])
    assert [tone.amplitude for tone in result_tones] == pytest.approx([original_tones[0].amplitude, original_tones[1].amplitude])


class TestFragmentAcceptance:
    def test_fragment_with_same_damage_pattern_key_repeats_the_same_damage_layout(self):
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
                                        "params": {"damage_pct": 50, "damage_tones_chunk_size": 2, "damage_pattern_key": pattern_key},
                                    }
                                ],
                            },
                            {
                                "motifs": ["ruin_seed"],
                                "transforms": [
                                    {
                                        "name": "fragment",
                                        "params": {"damage_pct": 50, "damage_tones_chunk_size": 2, "damage_pattern_key": pattern_key},
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

    def test_fragment_with_different_damage_pattern_keys_can_change_the_fragmented_result(self):
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
                                        "params": {"damage_pct": 50, "damage_tones_chunk_size": 2, "damage_pattern_key": pattern_key_a},
                                    }
                                ],
                            },
                            {
                                "motifs": ["ruin_seed"],
                                "transforms": [
                                    {
                                        "name": "fragment",
                                        "params": {"damage_pct": 50, "damage_tones_chunk_size": 2, "damage_pattern_key": different_pattern_key},
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
                                        "params": {"damage_pct": 50, "damage_tones_chunk_size": 2, "damage_pattern_key": "pattern-key-a"},
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