from composition.parser import build_score, parse_score_plan
from composition.schema import CompositionDocument
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


def test_parse_score_plan_resolves_motifs_and_preserves_structure():
    composition_document: CompositionDocument = {
        "motifs": {
            "m1": ["440.0:1.0"],
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {"motifs": ["m1"]},
                        {"motifs": ["m1", "m1"]},
                    ]
                }
            ],
            "score_transforms": [
                {
                    "name": "add_pedal_tone",
                    "params": {"frequency": 130.81},
                }
            ],
        },
    }

    score_plan = parse_score_plan(composition_document)

    assert "m1" in score_plan.motifs
    assert len(score_plan.motifs["m1"].tones) == 1

    assert len(score_plan.voices) == 1
    assert len(score_plan.voices[0].phrases) == 2
    assert len(score_plan.voices[0].phrases[0].motifs) == 1
    assert len(score_plan.voices[0].phrases[1].motifs) == 2
    
    # Resolves to the exact same motif instance in the plan
    plan_motif = score_plan.motifs["m1"]
    assert score_plan.voices[0].phrases[0].motifs[0] is plan_motif
    assert score_plan.voices[0].phrases[1].motifs[0] is plan_motif
    assert score_plan.voices[0].phrases[1].motifs[1] is plan_motif

    assert len(score_plan.score_transform_requests) == 1
    assert score_plan.score_transform_requests[0].transform_request.name == "add_pedal_tone"


def test_parse_score_plan_collects_phrase_transform_requests():
    composition_document: CompositionDocument = {
        "motifs": {
            "m1": ["440.0:1.0"],
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {"motifs": ["m1"]},
                        {
                            "motifs": ["m1"],
                            "transforms": [
                                {"name": "delay", "params": {"seconds": 0.5}},
                            ],
                        },
                    ]
                },
                {
                    "phrases": [
                        {
                            "motifs": ["m1"],
                            "transforms": [
                                {"name": "reverse"},
                                {"name": "transpose", "params": {"semitones": 2}},
                            ],
                        }
                    ]
                },
            ]
        },
    }

    score_plan = parse_score_plan(composition_document)

    requests = score_plan.phrase_transform_requests
    assert len(requests) == 3

    # First request: Voice 0, Phrase 1, "delay"
    assert requests[0].voice_index == 0
    assert requests[0].phrase_index == 1
    assert requests[0].transform_request.name == "delay"
    assert requests[0].transform_request.params == {"seconds": 0.5}

    # Second request: Voice 1, Phrase 0, "reverse"
    assert requests[1].voice_index == 1
    assert requests[1].phrase_index == 0
    assert requests[1].transform_request.name == "reverse"
    assert requests[1].transform_request.params == {}

    # Third request: Voice 1, Phrase 0, "transpose"
    assert requests[2].voice_index == 1
    assert requests[2].phrase_index == 0
    assert requests[2].transform_request.name == "transpose"
    assert requests[2].transform_request.params == {"semitones": 2}


def test_build_score_creates_fresh_instances_for_repeated_references():
    composition_document: CompositionDocument = {
        "motifs": {
            "m1": ["440.0:1.0"],
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {"motifs": ["m1", "m1"]},
                    ]
                }
            ]
        },
    }

    score_plan = parse_score_plan(composition_document)
    score = build_score(score_plan)

    assert len(score.voices) == 1
    assert len(score.voices[0].phrases) == 1
    phrase = score.voices[0].phrases[0]
    
    assert len(phrase.motifs) == 2
    motif_a = phrase.motifs[0]
    motif_b = phrase.motifs[1]

    # They should be distinct motif instances
    assert motif_a is not motif_b
    assert motif_a.name == "m1"
    assert motif_b.name == "m1"

    # They should have distinct tone instances
    assert len(motif_a.tones) == 1
    assert len(motif_b.tones) == 1
    tone_a = motif_a.tones[0]
    tone_b = motif_b.tones[0]
    
    assert tone_a is not tone_b
    assert tone_a.frequency == 440.0
    assert tone_b.frequency == 440.0
    assert tone_a.duration == 1.0
    assert tone_b.duration == 1.0
