import pytest
from composition.transformer import (
    apply_transform_requests,
    assemble_prepared_transforms,
    prepare_phrase_transform,
    prepare_score_transform,
)
from composition.score_plan import (
    PhraseTransformRequest,
    ScorePlan,
    ScoreTransformRequest,
    TransformRequest,
)
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice


def test_prepare_phrase_transform_applies_transform_and_replaces_target_phrase():
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
        assert voice.phrases[0].motifs[0].name == "<each_voice>"


def test_assemble_and_apply_transform_requests():
    score = Score(
        [
            Voice([Phrase([Motif("seed_a", [Tone(440)])])]),
        ]
    )

    score_plan = ScorePlan(
        motifs={},
        voices=[],
        phrase_transform_requests=[
            PhraseTransformRequest(
                voice_index=0,
                phrase_index=0,
                transform_request=TransformRequest(name="transpose", params={"semitones": 1}),
            )
        ],
        score_transform_requests=[
            ScoreTransformRequest(
                transform_request=TransformRequest(name="add_pedal_tone", params={"frequency": 110.0}),
            )
        ],
    )

    prepared_transforms = assemble_prepared_transforms(score_plan)
    assert len(prepared_transforms) == 2

    new_score = apply_transform_requests(score, score_plan)

    assert len(new_score.voices) == 2
    # Check that phrase transform was applied (transposed up 1 semitone)
    assert flatten_voice_tones(new_score.voices[0])[0].frequency == pytest.approx(466.16, rel=1e-2)
    # Check that score transform was applied (pedal tone added)
    assert new_score.voices[-1].phrases[0].motifs[0].name == "<pedal>"
    assert flatten_voice_tones(new_score.voices[-1])[0].frequency == 110.0
