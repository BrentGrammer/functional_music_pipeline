from composition.score_plan import (
    PhrasePlan,
    PhraseTransformRequest,
    ScorePlan,
    ScoreTransformRequest,
    TransformRequest,
    VoicePlan,
)
from score_model.motif import Motif
from score_model.tone import Tone


def test_score_plan_defaults_to_empty_collections():
    score_plan = ScorePlan()

    assert score_plan.motifs == {}
    assert score_plan.voices == []
    assert score_plan.phrase_transform_requests == []
    assert score_plan.score_transform_requests == []


def test_score_plan_preserves_planning_metadata():
    motif = Motif("seed", [Tone(440.0, duration=0.5)])
    phrase_plan = PhrasePlan(motifs=[motif])
    voice_plan = VoicePlan(phrases=[phrase_plan])
    phrase_request = PhraseTransformRequest(
        voice_index=1,
        phrase_index=2,
        transform_request=TransformRequest(name="delay", params={"seconds": 1.0}),
    )
    score_request = ScoreTransformRequest(
        transform_request=TransformRequest(name="add_pedal_tone", params={"frequency": 130.81}),
    )

    score_plan = ScorePlan(
        motifs={"seed": motif},
        voices=[voice_plan],
        phrase_transform_requests=[phrase_request],
        score_transform_requests=[score_request],
    )

    assert score_plan.motifs["seed"] is motif
    assert score_plan.voices[0].phrases[0].motifs[0] is motif
    assert score_plan.phrase_transform_requests[0] is phrase_request
    assert score_plan.score_transform_requests[0] is score_request
