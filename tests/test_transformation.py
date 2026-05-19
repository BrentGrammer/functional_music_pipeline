import pytest

from composition.score_plan import (
    PhrasePlan,
    PhraseTransformRequest,
    ScorePlan,
    ScoreTransformRequest,
    TransformRequest,
    VoicePlan,
)
from composition.transformer import (
    assemble_prepared_transforms,
    prepare_phrase_transform,
    prepare_score_transform,
    transform_score,
)
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.pitch_utils import transpose_frequency_by_semitones
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from transforms.base import PhraseTransformDefinition
from transforms.registry import PHRASE_TRANSFORMS


def test_prepare_phrase_transform_applies_transform_and_replaces_target_phrase():
    descriptor = PHRASE_TRANSFORMS["reverse"]
    assert isinstance(descriptor, PhraseTransformDefinition)

    score = Score(
        [
            Voice(
                [
                    Phrase([Motif("seed_a", [Tone(440)])]),
                    Phrase([Motif("seed_b", [Tone(880)])]),
                ]
            )
        ]
    )

    request = PhraseTransformRequest(
        voice_index=0,
        phrase_index=1,
        transform_request=TransformRequest(name="reverse", params={}),
    )

    prepared_transform = prepare_phrase_transform(request)
    new_score = prepared_transform(score)

    assert new_score is not score
    assert len(new_score.voices) == 1
    assert len(new_score.voices[0].phrases) == 2

    # First phrase should be unchanged structurally
    assert new_score.voices[0].phrases[0] is score.voices[0].phrases[0]

    # Second phrase should be replaced
    new_phrase = new_score.voices[0].phrases[1]
    assert new_phrase is not score.voices[0].phrases[1]
    assert new_phrase.motifs[0].name == "<transformed>"
    assert new_phrase.motifs[0].tones[0].frequency == 880


def test_prepare_score_transform_applies_each_voice_transform():
    score = Score(
        [
            Voice([Phrase([Motif("seed_a", [Tone(440)])])]),
            Voice([Phrase([Motif("seed_b", [Tone(880)])])]),
        ]
    )

    request = ScoreTransformRequest(
        transform_request=TransformRequest(name="reverse", params={}),
    )

    prepared_transform = prepare_score_transform(request)
    new_score = prepared_transform(score)

    assert new_score is not score
    assert len(new_score.voices) == 2

    for voice in new_score.voices:
        assert voice.phrases[0].motifs[0].name == "<transformed>"


def test_transform_score_builds_score_and_applies_transform_requests():
    motif_name = "seed_a"
    seed_frequency = 440.0
    transpose_up_one_semitone = 1
    expected_seed_frequency_after_transpose = transpose_frequency_by_semitones(
        seed_frequency,
        transpose_up_one_semitone,
    )
    pedal_tone_frequency = 110.0
    expected_transform_request_count = 2

    score_plan = ScorePlan(
        motifs={motif_name: Motif(motif_name, [Tone(seed_frequency)])},
        voices=[],
        phrase_transform_requests=[
            PhraseTransformRequest(
                voice_index=0,
                phrase_index=0,
                transform_request=TransformRequest(
                    name="transpose",
                    params={"semitones": transpose_up_one_semitone},
                ),
            )
        ],
        score_transform_requests=[
            ScoreTransformRequest(
                transform_request=TransformRequest(
                    name="add_pedal_tone",
                    params={"frequency": pedal_tone_frequency},
                ),
            )
        ],
    )
    score_plan.voices.append(
        VoicePlan(
            phrases=[
                PhrasePlan(
                    motifs=[score_plan.motifs[motif_name]],
                )
            ]
        )
    )

    prepared_transforms = assemble_prepared_transforms(score_plan)
    assert len(prepared_transforms) == expected_transform_request_count

    new_score = transform_score(score_plan)

    assert len(new_score.voices) == 2
    assert flatten_voice_tones(new_score.voices[0])[0].frequency == pytest.approx(
        expected_seed_frequency_after_transpose,
    )
    assert flatten_voice_tones(new_score.voices[-1])[0].frequency == pedal_tone_frequency
