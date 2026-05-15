import random

import pytest

from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.frost_effect import (
    FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS,
    FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS,
    FROST_ROLE_CENTER,
    FROST_ROLE_SIDE,
    FrostEventBuildSpec,
    FrostVoiceBuildSpec,
    _advance_edge_delay,
    _apply_frost_iteration,
    _build_edge_voices,
    _build_frost_voice,
    _build_initial_frost_event_voices,
    _build_later_frost_event_voices,
    _build_pending_edge_expansions,
    _build_replay_entry_delays,
    _build_replayed_event_voices,
    _copy_voice_retaining_frost_history,
    _first_audible_frequency,
    _first_audible_tone,
    _random_edge_stagger_seconds,
    _random_single_seed_edge_separation_seconds,
    _score_end_time,
    frost_effect,
)


def _voice_start_time(voice: Voice) -> float:
    if voice.tones and voice.tones[0].frequency == 0:
        return voice.tones[0].duration

    return 0.0


def test_copy_voice_retaining_frost_history_preserves_metadata_and_copies_tones():
    source_frequency = 440.0
    source_duration = 1.0
    source_voice = Voice([Tone(source_frequency, duration=source_duration)])
    expected_generation = 3
    expected_role = FROST_ROLE_SIDE
    setattr(source_voice, "frost_generation", expected_generation)
    setattr(source_voice, "frost_role", expected_role)

    copied_voice = _copy_voice_retaining_frost_history(source_voice)

    assert copied_voice is not source_voice
    assert copied_voice.tones is not source_voice.tones
    assert copied_voice.tones[0] is not source_voice.tones[0]
    assert copied_voice.tones[0].frequency == pytest.approx(source_frequency)
    assert getattr(copied_voice, "frost_generation") == expected_generation
    assert getattr(copied_voice, "frost_role") == expected_role


def test_build_frost_voice_applies_delay_and_metadata():
    child_frequency = 660.0
    child_duration = 0.5
    child_delay_seconds = 0.25
    expected_generation = 2
    expected_role = FROST_ROLE_CENTER
    spec = FrostVoiceBuildSpec(
        tone=Tone(440.0, duration=child_duration, amplitude=0.7),
        delay_seconds=child_delay_seconds,
        generation=expected_generation,
        frequency=child_frequency,
        role=expected_role,
    )

    child_voice = _build_frost_voice(spec)

    assert len(child_voice.tones) == 2
    assert child_voice.tones[0].frequency == 0.0
    assert child_voice.tones[0].duration == pytest.approx(child_delay_seconds)
    assert child_voice.tones[1].frequency == pytest.approx(child_frequency)
    assert child_voice.tones[1].duration == pytest.approx(child_duration)
    assert getattr(child_voice, "frost_generation") == expected_generation
    assert getattr(child_voice, "frost_role") == expected_role


def test_voice_start_time_returns_zero_for_undelayed_voice():
    undelayed_voice = Voice([Tone(440.0, duration=1.0)])

    assert _voice_start_time(undelayed_voice) == pytest.approx(0.0)


def test_score_end_time_uses_longest_voice_and_handles_empty_score():
    shorter_voice_duration = 1.5
    longer_voice_duration = 2.25
    score = Score(
        [
            Voice([Tone(440.0, duration=shorter_voice_duration)]),
            Voice([Tone(660.0, duration=1.0), Tone(660.0, duration=1.25)]),
        ]
    )
    empty_score = Score()

    assert _score_end_time(score) == pytest.approx(longer_voice_duration)
    assert _score_end_time(empty_score) == pytest.approx(0.0)


def test_first_audible_tone_and_frequency_return_none_for_silent_voice():
    silent_voice = Voice([Tone(0.0, duration=1.0), Tone(440.0, duration=1.0, amplitude=0.0)])

    assert _first_audible_tone(silent_voice) is None
    assert _first_audible_frequency(silent_voice) is None


def test_build_pending_edge_expansions_returns_down_and_up_for_single_audible_voice():
    only_voice = Voice([Tone(440.0, duration=1.0)])

    pending_edge_expansions = _build_pending_edge_expansions([only_voice])

    assert len(pending_edge_expansions) == 2
    assert pending_edge_expansions[0][0] is only_voice
    assert pending_edge_expansions[1][0] is only_voice
    assert pending_edge_expansions[0][1] is not pending_edge_expansions[1][1]


def test_random_stagger_helpers_stay_within_declared_bounds():
    random_seed = 0
    random.seed(random_seed)

    edge_stagger_seconds = _random_edge_stagger_seconds()
    single_seed_separation_seconds = _random_single_seed_edge_separation_seconds()

    assert FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS <= edge_stagger_seconds <= FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS
    assert (
        FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS
        <= single_seed_separation_seconds
        <= FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS
    )


def test_build_replay_entry_delays_returns_empty_for_non_positive_voice_count():
    assert _build_replay_entry_delays(0) == []
    assert _build_replay_entry_delays(-1) == []


def test_advance_edge_delay_uses_base_delay_for_first_edge_and_callback_for_later_edges():
    base_event_delay = 1.5
    first_edge_extra_delay = 0.3
    later_edge_extra_delay = 0.2

    original_random_edge_stagger_seconds = _advance_edge_delay.__globals__["_random_edge_stagger_seconds"]
    try:
        _advance_edge_delay.__globals__["_random_edge_stagger_seconds"] = lambda: first_edge_extra_delay

        first_edge_delay = _advance_edge_delay(
            previous_edge_delay=None,
            edge_base_delay=base_event_delay,
            next_delay=lambda: later_edge_extra_delay,
        )
        later_edge_delay = _advance_edge_delay(
            previous_edge_delay=first_edge_delay,
            edge_base_delay=base_event_delay,
            next_delay=lambda: later_edge_extra_delay,
        )
    finally:
        _advance_edge_delay.__globals__["_random_edge_stagger_seconds"] = original_random_edge_stagger_seconds

    assert first_edge_delay == pytest.approx(base_event_delay + first_edge_extra_delay)
    assert later_edge_delay == pytest.approx(first_edge_delay + later_edge_extra_delay)


def test_build_replayed_event_voices_skips_silent_voice_and_preserves_existing_role_when_requested():
    event_start_time = 2.0
    replay_generation = 4
    first_entry_delay = 0.1
    second_entry_delay = 0.3
    replayed_frequency = 440.0
    audible_voice = Voice([Tone(replayed_frequency, duration=1.0)])
    setattr(audible_voice, "frost_role", FROST_ROLE_SIDE)
    silent_voice = Voice([Tone(0.0, duration=1.0)])

    replayed_voices = _build_replayed_event_voices(
        [audible_voice, silent_voice],
        event_start=event_start_time,
        generation=replay_generation,
        preserve_existing_roles=True,
        entry_delays=[first_entry_delay, second_entry_delay],
    )

    assert len(replayed_voices) == 1
    assert getattr(replayed_voices[0], "frost_generation") == replay_generation
    assert getattr(replayed_voices[0], "frost_role") == FROST_ROLE_SIDE
    assert replayed_voices[0].tones[0].duration == pytest.approx(event_start_time + first_entry_delay)
    assert replayed_voices[0].tones[1].frequency == pytest.approx(replayed_frequency)


def test_build_edge_voices_returns_empty_when_no_audible_edge_voices_exist():
    event_spec = FrostEventBuildSpec(
        source_voices=[Voice([Tone(0.0, duration=1.0)])],
        event_start=1.0,
        generation=1,
        preserve_existing_roles=False,
        single_seed_event=False,
    )

    assert _build_edge_voices(event_spec, edge_base_delay=0.5) == []


def test_build_initial_and_later_frost_event_voices_return_empty_when_no_audible_sources_exist():
    silent_source_voice = Voice([Tone(0.0, duration=1.0)])
    setattr(silent_source_voice, "frost_generation", 2)
    score = Score([silent_source_voice])
    event_start_time = 1.0

    assert _build_initial_frost_event_voices(score, event_start=event_start_time) == []
    assert _build_later_frost_event_voices(score, latest_generation=2, event_start=event_start_time) == []


def test_apply_frost_iteration_preserves_original_metadata_on_copied_source_voices():
    source_voice = Voice([Tone(440.0, duration=1.0)])
    expected_generation = 2
    expected_role = FROST_ROLE_SIDE
    setattr(source_voice, "frost_generation", expected_generation)
    setattr(source_voice, "frost_role", expected_role)
    score = Score([source_voice])

    result = _apply_frost_iteration(score)

    copied_source_voice = result.voices[0]
    assert copied_source_voice is not source_voice
    assert getattr(copied_source_voice, "frost_generation") == expected_generation
    assert getattr(copied_source_voice, "frost_role") == expected_role


@pytest.mark.parametrize("invalid_iterations", [True, False, 0, -1, 1.5, "2"])
def test_frost_effect_rejects_non_positive_or_non_integer_iterations(invalid_iterations):
    seed_score = Score([Voice([Tone(440.0, duration=1.0)])])

    with pytest.raises(ValueError, match="positive integer"):
        frost_effect(seed_score, iterations=invalid_iterations)
