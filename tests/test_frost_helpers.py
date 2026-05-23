import random
from unittest.mock import patch

import pytest

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from transforms.geological.frost_effect import (
    DEFAULT_FROST_EFFECT_ITERATIONS,
    DEFAULT_FROST_EFFECT_SUSTAIN_NOTES,
    FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS,
    FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS,
    FROST_EFFECT_PARAMS_SPEC,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS,
    FrostEffectParams,
    _apply_frost_iteration,
    _build_frost_voice,
    _collect_audible_seed_events,
    _copy_voice_retaining_frost_history,
    _find_frost_edge_voices,
    _first_audible_tone,
    _random_edge_stagger_seconds,
    _random_single_seed_edge_separation_seconds,
    _score_end_time,
    frost_effect,
    frost_effect_score_transform_adapter,
)


def _voice_start_time(voice: Voice) -> float:
    voice_tones = flatten_voice_tones(voice)
    if voice_tones and voice_tones[0].frequency == 0:
        return voice_tones[0].duration
    return 0.0

def test_copy_voice_retaining_frost_history_preserves_generation_and_copies_tones():
    source_voice = Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])
    setattr(source_voice, "frost_generation", 3)

    copied_voice = _copy_voice_retaining_frost_history(source_voice)

    assert copied_voice is not source_voice
    assert flatten_voice_tones(copied_voice) is not flatten_voice_tones(source_voice)
    assert flatten_voice_tones(copied_voice)[0] is not flatten_voice_tones(source_voice)[0]
    assert flatten_voice_tones(copied_voice)[0].frequency == pytest.approx(440.0)
    assert getattr(copied_voice, "frost_generation") == 3


def test_build_frost_voice_applies_delay_and_generation():
    child_voice = _build_frost_voice(
        tone=Tone(440.0, duration=0.5, amplitude=0.7),
        delay_seconds=0.25,
        generation=2,
        frequency=660.0,
    )

    assert len(flatten_voice_tones(child_voice)) == 2
    assert flatten_voice_tones(child_voice)[0].frequency == 0.0
    assert flatten_voice_tones(child_voice)[0].duration == pytest.approx(0.25)
    assert flatten_voice_tones(child_voice)[1].frequency == pytest.approx(660.0)
    assert flatten_voice_tones(child_voice)[1].duration == pytest.approx(0.5)
    assert getattr(child_voice, "frost_generation") == 2


def test_score_end_time_uses_longest_voice_and_handles_empty_score():
    score = Score(
        [
            Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.5)])])]),
            Voice([Phrase([Motif("<test>", [Tone(660.0, duration=1.0), Tone(660.0, duration=1.25)])])]),
        ]
    )

    assert _score_end_time(score) == pytest.approx(2.25)
    assert _score_end_time(Score()) == pytest.approx(0.0)


def test_first_audible_tone_returns_none_for_silent_voice():
    silent_voice = Voice([Phrase([Motif("<test>", [Tone(0.0, duration=1.0), Tone(440.0, duration=1.0, amplitude=0.0)])])])

    assert _first_audible_tone(silent_voice) is None


def test_collect_audible_seed_events_collects_multiple_tones_in_one_phrase_in_voice():
    first_frequency = 440.0
    second_frequency = 660.0
    first_duration_seconds = 0.5
    second_duration_seconds = 1.25

    score = Score(
        [Voice([Phrase([Motif("<test>", [Tone(first_frequency, duration=first_duration_seconds), Tone(second_frequency, duration=second_duration_seconds)])])])]
    )

    seed_events = _collect_audible_seed_events(score)

    assert [
        (seed_event.tone.frequency, seed_event.start_time, seed_event.end_time)
        for seed_event in seed_events
    ] == [
        (first_frequency, 0.0, first_duration_seconds),
        (second_frequency, first_duration_seconds, first_duration_seconds + second_duration_seconds),
    ]


def test_collect_audible_seed_events_collects_across_multiple_phrases_in_one_voice():
    first_frequency = 440.0
    second_frequency = 660.0
    first_duration_seconds = 0.5
    second_duration_seconds = 0.75

    score = Score(
        [
            Voice(
                [
                    Phrase([Motif("<first>", [Tone(first_frequency, duration=first_duration_seconds)])]),
                    Phrase([Motif("<second>", [Tone(second_frequency, duration=second_duration_seconds)])]),
                ]
            )
        ]
    )

    seed_events = _collect_audible_seed_events(score)

    assert [
        (seed_event.tone.frequency, seed_event.start_time, seed_event.end_time)
        for seed_event in seed_events
    ] == [
        (first_frequency, 0.0, first_duration_seconds),
        (second_frequency, first_duration_seconds, first_duration_seconds + second_duration_seconds),
    ]


def test_collect_audible_seed_events_collects_from_multiple_voices():
    high_frequency = 880.0
    low_frequency = 220.0
    high_duration_seconds = 0.5
    low_duration_seconds = 1.0

    score = Score(
        [
            Voice([Phrase([Motif("<high>", [Tone(high_frequency, duration=high_duration_seconds)])])]),
            Voice([Phrase([Motif("<low>", [Tone(low_frequency, duration=low_duration_seconds)])])]),
        ]
    )

    seed_events = _collect_audible_seed_events(score)

    assert [
        (seed_event.tone.frequency, seed_event.start_time, seed_event.end_time)
        for seed_event in seed_events
    ] == [
        (high_frequency, 0.0, high_duration_seconds),
        (low_frequency, 0.0, low_duration_seconds),
    ]


def test_collect_audible_seed_events_uses_leading_silence_in_seed_timing():
    leading_silence_seconds = 0.25
    audible_frequency = 440.0
    audible_duration_seconds = 0.5
    audible_end_time_seconds = leading_silence_seconds + audible_duration_seconds

    score = Score(
        [
            Voice(
                [
                    Phrase(
                        [
                            Motif(
                                "<test>",
                                [
                                    Tone(0.0, duration=leading_silence_seconds),
                                    Tone(audible_frequency, duration=audible_duration_seconds),
                                ],
                            )
                        ]
                    )
                ]
            )
        ]
    )

    seed_events = _collect_audible_seed_events(score)

    assert [
        (seed_event.tone.frequency, seed_event.start_time, seed_event.end_time)
        for seed_event in seed_events
    ] == [
        (audible_frequency, leading_silence_seconds, audible_end_time_seconds),
    ]


def test_collect_audible_seed_events_skips_rests_and_zero_amplitude_tones():
    rest_duration_seconds = 0.5
    muted_frequency = 440.0
    muted_duration_seconds = 0.25
    audible_frequency = 550.0
    audible_duration_seconds = 0.75
    zero_duration_frequency = 660.0
    audible_start_time_seconds = rest_duration_seconds + muted_duration_seconds
    audible_end_time_seconds = audible_start_time_seconds + audible_duration_seconds

    score = Score(
        [
            Voice(
                [
                    Phrase(
                        [
                            Motif(
                                "<test>",
                                [
                                    Tone(0.0, duration=rest_duration_seconds),
                                    Tone(muted_frequency, duration=muted_duration_seconds, amplitude=0.0),
                                    Tone(audible_frequency, duration=audible_duration_seconds),
                                    Tone(zero_duration_frequency, duration=0.0),
                                ],
                            )
                        ]
                    )
                ]
            )
        ]
    )

    seed_events = _collect_audible_seed_events(score)

    assert [
        (seed_event.tone.frequency, seed_event.start_time, seed_event.end_time)
        for seed_event in seed_events
    ] == [
        (audible_frequency, audible_start_time_seconds, audible_end_time_seconds),
    ]


def test_find_frost_edge_voices_returns_lowest_and_highest_audible_voice():
    lower_voice = Voice([Phrase([Motif("<test>", [Tone(418.0, duration=1.0)])])])
    center_voice = Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])
    upper_voice = Voice([Phrase([Motif("<test>", [Tone(481.0, duration=1.0)])])])

    found_lower, found_upper = _find_frost_edge_voices([center_voice, upper_voice, lower_voice])

    assert found_lower is lower_voice
    assert found_upper is upper_voice


def test_find_frost_edge_voices_returns_none_when_no_audible_voices_exist():
    found_lower, found_upper = _find_frost_edge_voices(
        [
            Voice([]),
            Voice([Phrase([Motif("<test>", [Tone(0.0, duration=1.0)])])]),
            Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0, amplitude=0.0)])])]),
        ]
    )

    assert found_lower is None
    assert found_upper is None


def test_random_stagger_helpers_stay_within_declared_bounds():
    random.seed(0)

    edge_stagger_seconds = _random_edge_stagger_seconds()
    single_seed_separation_seconds = _random_single_seed_edge_separation_seconds()

    assert FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS <= edge_stagger_seconds <= FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS
    assert FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS <= single_seed_separation_seconds <= FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS


def test_apply_frost_iteration_returns_no_new_voices_when_source_event_has_no_audible_tones():
    silent_source_voice = Voice([Phrase([Motif("<test>", [Tone(0.0, duration=1.0)])])])

    result = _apply_frost_iteration(Score([silent_source_voice]))

    assert len(result.voices) == 1
    assert flatten_voice_tones(result.voices[0])[0].frequency == pytest.approx(0.0)


def test_apply_frost_iteration_returns_no_new_voices_when_latest_generation_is_silent():
    silent_source_voice = Voice([Phrase([Motif("<test>", [Tone(0.0, duration=1.0)])])])
    setattr(silent_source_voice, "frost_generation", 2)

    result = _apply_frost_iteration(Score([silent_source_voice]))

    assert len(result.voices) == 1
    assert getattr(result.voices[0], "frost_generation") == 2


def test_apply_frost_iteration_replays_source_voice_after_score_end():
    source_voice = Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])

    result = _apply_frost_iteration(Score([source_voice]))
    replayed_voice = result.voices[1]

    assert len(result.voices) == 4
    assert flatten_voice_tones(replayed_voice)[1].frequency == pytest.approx(440.0)
    assert _voice_start_time(replayed_voice) >= 1.0


def test_apply_frost_iteration_skips_replay_when_source_voice_lacks_audible_tone_during_iteration():
    source_voice = Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])
    audible_tone = Tone(440.0, duration=1.0)

    with patch("transforms.geological.frost_effect._first_audible_start_time_voices", return_value=[source_voice]):
        with patch("transforms.geological.frost_effect._find_frost_edge_voices", return_value=(source_voice, source_voice)):
            with patch(
                "transforms.geological.frost_effect._first_audible_tone",
                side_effect=[None, audible_tone, audible_tone],
            ):
                result = _apply_frost_iteration(Score([source_voice]))

    assert len(result.voices) == 3


def test_apply_frost_iteration_raises_when_edge_voices_are_missing_despite_audible_sources():
    source_voice = Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])

    with patch("transforms.geological.frost_effect._find_frost_edge_voices", return_value=(None, None)):
        with pytest.raises(RuntimeError, match="expected audible edge voices"):
            _apply_frost_iteration(Score([source_voice]))


def test_apply_frost_iteration_raises_when_edge_voice_lacks_audible_tone():
    source_voice = Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])
    audible_tone = Tone(440.0, duration=1.0)

    with patch("transforms.geological.frost_effect._find_frost_edge_voices", return_value=(source_voice, source_voice)):
        with patch("transforms.geological.frost_effect._first_audible_tone", side_effect=[audible_tone, None]):
            with pytest.raises(RuntimeError, match="did not contain an audible tone"):
                _apply_frost_iteration(Score([source_voice]))


def test_frost_effect_score_transform_adapter_rejects_non_integer_iterations():
    with pytest.raises(ValueError):
        FROST_EFFECT_PARAMS_SPEC.parse_params({"iterations": True}, transform_name="frost_effect")


def test_frost_effect_score_transform_adapter_rejects_non_boolean_sustain_notes():
    with pytest.raises(ValueError):
        FROST_EFFECT_PARAMS_SPEC.parse_params({"sustain_notes": 1}, transform_name="frost_effect")


def test_frost_effect_score_transform_adapter_applies_default_params():
    seed_score = Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])])
    params = FROST_EFFECT_PARAMS_SPEC.parse_params({}, transform_name="frost_effect")

    assert params == FrostEffectParams(
        iterations=DEFAULT_FROST_EFFECT_ITERATIONS,
        sustain_notes=DEFAULT_FROST_EFFECT_SUSTAIN_NOTES,
    )

    result = frost_effect_score_transform_adapter(seed_score, params)

    assert result != seed_score
    assert len(result.voices) == len(seed_score.voices) + 3


def test_frost_effect_score_transform_adapter_passes_sustain_notes_to_frost_effect():
    seed_score = Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])])
    params = FrostEffectParams(iterations=2, sustain_notes=True)

    with patch("transforms.geological.frost_effect.frost_effect", return_value=seed_score) as frost_effect_mock:
        result = frost_effect_score_transform_adapter(seed_score, params)

    assert result is seed_score
    frost_effect_mock.assert_called_once_with(seed_score, iterations=2, sustain_notes=True)


@pytest.mark.parametrize("invalid_iterations", [0, -1])
def test_frost_effect_rejects_non_positive_iterations(invalid_iterations):
    seed_score = Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])])

    with pytest.raises(ValueError, match="positive integer"):
        frost_effect(seed_score, iterations=invalid_iterations)
