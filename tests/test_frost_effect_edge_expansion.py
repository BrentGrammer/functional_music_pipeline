import math
import random

import pytest

from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.frost import (
    FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS,
    FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS,
    FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS,
    FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS,
    FROST_ROLE_CENTER,
    FROST_ROLE_SIDE,
    _cents_to_frequency_ratio,
    _first_audible_onset_field,
    _first_audible_onset_time,
    _first_audible_tone_with_onset,
    _find_frost_edge_voices,
    _jitter_frequency_down_within_bounds,
    _jitter_frequency_up_within_bounds,
    frost_effect,
)


CENTS_PER_OCTAVE = 1200.0


def _first_audible_frequency(voice: Voice) -> float | None:
    for tone in voice.tones:
        if tone.frequency > 0 and tone.amplitude > 0 and tone.duration > 0:
            return tone.frequency

    return None


def _event_frequencies(score: Score, event_number: int) -> list[float]:
    frequencies = []

    for voice in score.voices:
        if getattr(voice, "frost_generation", 0) != event_number:
            continue

        frequency = _first_audible_frequency(voice)
        if frequency is not None:
            frequencies.append(frequency)

    return frequencies


def _event_voices(score: Score, event_number: int) -> list[Voice]:
    return [
        voice
        for voice in score.voices
        if getattr(voice, "frost_generation", 0) == event_number
        and _first_audible_frequency(voice) is not None
    ]


def _voice_start_time(voice: Voice) -> float:
    if voice.tones and voice.tones[0].frequency == 0:
        return voice.tones[0].duration

    return 0.0


def _voice_end_time(voice: Voice) -> float:
    return sum(tone.duration for tone in voice.tones)


def _event_relative_start_times_by_frequency(score: Score, event_number: int) -> dict[float, float]:
    event_voices = _event_voices(score, event_number)
    event_start_time = min(_voice_start_time(voice) for voice in event_voices)

    relative_start_times: dict[float, float] = {}
    for voice in event_voices:
        frequency = _first_audible_frequency(voice)
        if frequency is None:
            continue

        relative_start_times[frequency] = _voice_start_time(voice) - event_start_time

    return relative_start_times


def _event_start_times(score: Score, event_number: int) -> list[float]:
    return [_voice_start_time(voice) for voice in _event_voices(score, event_number)]


def _find_event_voice_by_frequency(score: Score, event_number: int, frequency: float) -> Voice:
    matching_voice = next(
        (
            voice
            for voice in _event_voices(score, event_number)
            if (voice_frequency := _first_audible_frequency(voice)) is not None
            and math.isclose(voice_frequency, frequency)
        ),
        None,
    )

    assert matching_voice is not None
    return matching_voice


def _event_voices_with_role(score: Score, event_number: int, role: str) -> list[Voice]:
    return [
        voice
        for voice in _event_voices(score, event_number)
        if getattr(voice, "frost_role", FROST_ROLE_CENTER) == role
    ]


def _assert_event_has_controlled_edge_stagger(score: Score, event_number: int) -> None:
    center_voices = _event_voices_with_role(score, event_number, FROST_ROLE_CENTER)
    side_voices = _event_voices_with_role(score, event_number, FROST_ROLE_SIDE)
    event_anchor_time = min(_voice_start_time(voice) for voice in center_voices)
    latest_start_time = max(_event_start_times(score, event_number))
    earliest_end_time = min(_voice_end_time(voice) for voice in _event_voices(score, event_number))
    side_delays = sorted(_voice_start_time(voice) - event_anchor_time for voice in side_voices)

    assert len({_voice_start_time(voice) for voice in center_voices}) == 1
    assert len(side_delays) == 2

    if len(center_voices) == 1:
        side_separation = side_delays[1] - side_delays[0]

        assert side_delays[0] >= FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS
        assert side_delays[0] <= FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS
        assert side_separation >= FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS
        assert side_separation <= FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS
        assert side_delays[1] <= (
            FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS
            + FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS
        )
    else:
        for side_delay in side_delays:
            assert side_delay >= FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS
            assert side_delay <= FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS

    assert latest_start_time < earliest_end_time


def _assert_new_edges_have_controlled_stagger(
    score: Score,
    previous_event_frequencies: list[float],
    event_number: int,
) -> None:
    event_frequencies = _event_frequencies(score, event_number)
    new_frequencies = _find_frequencies_added_to_next_event(
        previous_event_frequencies,
        event_frequencies,
    )
    replayed_voices = [
        _find_event_voice_by_frequency(score, event_number, frequency)
        for frequency in previous_event_frequencies
    ]
    new_edge_voices = [
        _find_event_voice_by_frequency(score, event_number, frequency)
        for frequency in new_frequencies
    ]
    event_anchor_time = min(_voice_start_time(voice) for voice in replayed_voices)
    latest_start_time = max(_event_start_times(score, event_number))
    earliest_end_time = min(_voice_end_time(voice) for voice in _event_voices(score, event_number))

    assert len(new_frequencies) == 2
    assert len({_voice_start_time(voice) for voice in replayed_voices}) == 1

    for voice in new_edge_voices:
        edge_delay = _voice_start_time(voice) - event_anchor_time

        assert edge_delay >= FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS
        assert edge_delay <= FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS

    assert latest_start_time < earliest_end_time


def _cents_between(lower_frequency: float, upper_frequency: float) -> float:
    """
    Measure the ascending distance from a lower frequency to a higher frequency in cents.

    Lower edge movement is measured as `new_lowest` to `previous_lowest` because
    the new lower edge should be below the previous lower edge.
    """
    return CENTS_PER_OCTAVE * math.log2(upper_frequency / lower_frequency)


def _find_frequencies_added_to_next_event(
    previous_frequencies: list[float],
    event_frequencies: list[float],
) -> list[float]:
    """
    Find the new tones added when a frost event replays and expands the previous event.
    """
    unmatched_frequencies = list(event_frequencies)

    for previous_frequency in previous_frequencies:
        matching_index = next(
            (
                index
                for index, event_frequency in enumerate(unmatched_frequencies)
                if math.isclose(event_frequency, previous_frequency)
            ),
            None,
        )

        assert matching_index is not None
        unmatched_frequencies.pop(matching_index)

    return unmatched_frequencies


def test_cents_to_frequency_ratio_converts_octaves_and_unisons():
    assert _cents_to_frequency_ratio(0.0) == pytest.approx(1.0)
    assert _cents_to_frequency_ratio(1200.0) == pytest.approx(2.0)
    assert _cents_to_frequency_ratio(-1200.0) == pytest.approx(0.5)


def test_frost_generations_map_to_audible_event_numbers():
    random.seed(0)

    score = frost_effect(Score([Voice([Tone(440.0, duration=1.0)])]), iterations=2)

    assert _event_frequencies(score, 0) == [pytest.approx(440.0)]
    assert len(_event_frequencies(score, 1)) == 3
    assert len(_event_frequencies(score, 2)) == 5
    assert len(_event_voices(score, 0)) == 1
    assert len(_event_voices(score, 1)) == 3
    assert len(_event_voices(score, 2)) == 5


def test_first_frost_event_delays_only_new_edge_tones_within_controlled_bounds():
    random.seed(0)

    score = frost_effect(Score([Voice([Tone(440.0, duration=1.0)])]), iterations=1)

    source_event_end_time = max(_voice_end_time(voice) for voice in _event_voices(score, 0))
    center_voices = _event_voices_with_role(score, 1, FROST_ROLE_CENTER)

    assert len(center_voices) == 1
    assert len(_event_voices_with_role(score, 1, FROST_ROLE_SIDE)) == 2
    assert min(_voice_start_time(voice) for voice in center_voices) >= source_event_end_time
    assert _first_audible_frequency(center_voices[0]) == pytest.approx(440.0)
    _assert_event_has_controlled_edge_stagger(score, 1)


def test_first_frost_event_expands_cluster_as_one_simultaneous_event():
    random.seed(0)

    score = frost_effect(
        Score(
            [
                Voice([Tone(330.0, duration=1.0)]),
                Voice([Tone(440.0, duration=1.0)]),
                Voice([Tone(550.0, duration=1.0)]),
            ]
        ),
        iterations=1,
    )

    source_event_end_time = max(_voice_end_time(voice) for voice in _event_voices(score, 0))
    center_voices = _event_voices_with_role(score, 1, FROST_ROLE_CENTER)
    side_voices = _event_voices_with_role(score, 1, FROST_ROLE_SIDE)
    source_frequencies = _event_frequencies(score, 0)
    first_frost_frequencies = _event_frequencies(score, 1)
    new_frequencies = _find_frequencies_added_to_next_event(
        source_frequencies,
        first_frost_frequencies,
    )

    assert source_frequencies == [
        pytest.approx(330.0),
        pytest.approx(440.0),
        pytest.approx(550.0),
    ]
    assert len(first_frost_frequencies) == 5
    assert len(new_frequencies) == 2
    assert sum(frequency < 330.0 for frequency in new_frequencies) == 1
    assert sum(frequency > 550.0 for frequency in new_frequencies) == 1
    assert len(center_voices) == 3
    assert len(side_voices) == 2
    assert len({_voice_start_time(voice) for voice in center_voices}) == 1
    assert min(_voice_start_time(voice) for voice in center_voices) >= source_event_end_time


def test_second_frost_event_replays_previous_event_and_staggers_new_edges():
    random.seed(0)

    score = frost_effect(Score([Voice([Tone(440.0, duration=1.0)])]), iterations=2)

    first_frost_event_frequencies = _event_frequencies(score, 1)
    second_frost_event_frequencies = _event_frequencies(score, 2)
    new_frequencies = _find_frequencies_added_to_next_event(
        first_frost_event_frequencies,
        second_frost_event_frequencies,
    )
    first_frost_event_end_time = max(_voice_end_time(voice) for voice in _event_voices(score, 1))

    assert len(first_frost_event_frequencies) == 3
    assert len(second_frost_event_frequencies) == 5
    assert len(new_frequencies) == 2
    assert sum(frequency < min(first_frost_event_frequencies) for frequency in new_frequencies) == 1
    assert sum(frequency > max(first_frost_event_frequencies) for frequency in new_frequencies) == 1
    assert min(_event_start_times(score, 2)) >= first_frost_event_end_time
    _assert_new_edges_have_controlled_stagger(score, first_frost_event_frequencies, 2)


def test_cluster_frost_events_replay_previous_event_and_add_two_edges():
    random.seed(0)
    requested_iterations = 3

    score = frost_effect(
        Score(
            [
                Voice([Tone(330.0, duration=1.0)]),
                Voice([Tone(440.0, duration=1.0)]),
                Voice([Tone(550.0, duration=1.0)]),
            ]
        ),
        iterations=requested_iterations,
    )

    previous_event_frequencies = _event_frequencies(score, 0)

    assert previous_event_frequencies == [
        pytest.approx(330.0),
        pytest.approx(440.0),
        pytest.approx(550.0),
    ]

    for event_number in range(1, requested_iterations + 1):
        current_event_frequencies = _event_frequencies(score, event_number)
        new_frequencies = _find_frequencies_added_to_next_event(
            previous_event_frequencies,
            current_event_frequencies,
        )

        assert len(current_event_frequencies) == len(previous_event_frequencies) + 2
        assert len(new_frequencies) == 2
        assert sum(frequency < min(previous_event_frequencies) for frequency in new_frequencies) == 1
        assert sum(frequency > max(previous_event_frequencies) for frequency in new_frequencies) == 1
        if event_number == 1:
            _assert_event_has_controlled_edge_stagger(score, event_number)
        else:
            _assert_new_edges_have_controlled_stagger(score, previous_event_frequencies, event_number)

        previous_event_frequencies = current_event_frequencies


def test_repeated_frost_calls_continue_audible_event_sequence():
    random.seed(0)

    score = Score([Voice([Tone(440.0, duration=1.0)])])
    score = frost_effect(score, iterations=1)
    score = frost_effect(score, iterations=1)
    score = frost_effect(score, iterations=1)

    assert len(_event_frequencies(score, 0)) == 1
    assert len(_event_frequencies(score, 1)) == 3
    assert len(_event_frequencies(score, 2)) == 5
    assert len(_event_frequencies(score, 3)) == 7

    for event_number in range(1, 4):
        previous_event_frequencies = _event_frequencies(score, event_number - 1)
        current_event_frequencies = _event_frequencies(score, event_number)
        new_frequencies = _find_frequencies_added_to_next_event(
            previous_event_frequencies,
            current_event_frequencies,
        )

        assert len(new_frequencies) == 2
        assert sum(frequency < min(previous_event_frequencies) for frequency in new_frequencies) == 1
        assert sum(frequency > max(previous_event_frequencies) for frequency in new_frequencies) == 1
        if event_number == 1:
            _assert_event_has_controlled_edge_stagger(score, event_number)
        else:
            _assert_new_edges_have_controlled_stagger(score, previous_event_frequencies, event_number)


def test_first_audible_tone_with_onset_returns_single_seed_at_zero():
    voice = Voice([Tone(440.0, duration=1.0)])

    onset_tone = _first_audible_tone_with_onset(voice)

    assert onset_tone is not None
    assert onset_tone.voice is voice
    assert onset_tone.tone.frequency == pytest.approx(440.0)
    assert onset_tone.onset_time == pytest.approx(0.0)


def test_first_audible_onset_field_collects_simultaneous_cluster_voices():
    score = Score(
        [
            Voice([Tone(330.0, duration=1.0)]),
            Voice([Tone(440.0, duration=1.0)]),
            Voice([Tone(550.0, duration=1.0)]),
        ]
    )

    onset_field = _first_audible_onset_field(score)

    assert _first_audible_onset_time(score) == pytest.approx(0.0)
    assert [onset_tone.tone.frequency for onset_tone in onset_field] == [
        pytest.approx(330.0),
        pytest.approx(440.0),
        pytest.approx(550.0),
    ]


def test_first_audible_onset_field_excludes_later_delayed_voice():
    score = Score(
        [
            Voice([Tone(330.0, duration=1.0)]),
            Voice([Tone(0.0, duration=0.5), Tone(440.0, duration=1.0)]),
        ]
    )

    onset_field = _first_audible_onset_field(score)

    assert [onset_tone.tone.frequency for onset_tone in onset_field] == [
        pytest.approx(330.0),
    ]


def test_first_audible_onset_field_uses_first_tone_of_melodic_line():
    score = Score(
        [
            Voice(
                [
                    Tone(330.0, duration=1.0),
                    Tone(440.0, duration=1.0),
                    Tone(550.0, duration=1.0),
                ]
            )
        ]
    )

    onset_field = _first_audible_onset_field(score)

    assert [onset_tone.tone.frequency for onset_tone in onset_field] == [
        pytest.approx(330.0),
    ]


def test_jitter_frequency_down_within_bounds_moves_down_by_bounded_cents():
    random.seed(0)

    child_frequency = _jitter_frequency_down_within_bounds(440.0)
    outward_cents = _cents_between(child_frequency, 440.0)

    assert child_frequency < 440.0
    assert outward_cents >= FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS
    assert outward_cents <= FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS


def test_jitter_frequency_up_within_bounds_moves_up_by_bounded_cents():
    random.seed(0)

    child_frequency = _jitter_frequency_up_within_bounds(440.0)
    outward_cents = _cents_between(440.0, child_frequency)

    assert child_frequency > 440.0
    assert outward_cents >= FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS
    assert outward_cents <= FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS


def test_find_frost_edge_voices_identifies_lowest_and_highest_voice_in_any_order():
    center_voice = Voice([Tone(440.0, duration=1.0)])
    upper_voice = Voice([Tone(481.0, duration=1.0)])
    lower_voice = Voice([Tone(418.0, duration=1.0)])

    lower_edge_voice, upper_edge_voice = _find_frost_edge_voices(
        [center_voice, upper_voice, lower_voice]
    )

    assert lower_edge_voice is lower_voice
    assert upper_edge_voice is upper_voice


def test_find_frost_edge_voices_ignores_silent_voices():
    silent_low_voice = Voice([Tone(10.0, duration=1.0, amplitude=0.0)])
    silent_high_voice = Voice([Tone(4000.0, duration=1.0, amplitude=0.0)])
    lower_voice = Voice([Tone(430.0, duration=1.0)])
    upper_voice = Voice([Tone(450.0, duration=1.0)])

    lower_edge_voice, upper_edge_voice = _find_frost_edge_voices(
        [silent_low_voice, upper_voice, silent_high_voice, lower_voice]
    )

    assert lower_edge_voice is lower_voice
    assert upper_edge_voice is upper_voice


def test_find_frost_edge_voices_uses_first_audible_tone_in_delayed_voice():
    delayed_lower_voice = Voice([Tone(0.0, duration=0.25), Tone(410.0, duration=1.0)])
    delayed_upper_voice = Voice([Tone(0.0, duration=0.50), Tone(470.0, duration=1.0)])
    center_voice = Voice([Tone(440.0, duration=1.0)])

    lower_edge_voice, upper_edge_voice = _find_frost_edge_voices(
        [center_voice, delayed_upper_voice, delayed_lower_voice]
    )

    assert lower_edge_voice is delayed_lower_voice
    assert upper_edge_voice is delayed_upper_voice


def test_find_frost_edge_voices_returns_none_edges_when_no_audible_voices_exist():
    lower_edge_voice, upper_edge_voice = _find_frost_edge_voices(
        [
            Voice([]),
            Voice([Tone(0.0, duration=1.0)]),
            Voice([Tone(440.0, duration=1.0, amplitude=0.0)]),
        ]
    )

    assert lower_edge_voice is None
    assert upper_edge_voice is None


def test_find_frost_edge_voices_returns_same_voice_for_single_audible_voice():
    only_voice = Voice([Tone(440.0, duration=1.0)])

    lower_edge_voice, upper_edge_voice = _find_frost_edge_voices([only_voice])

    assert lower_edge_voice is only_voice
    assert upper_edge_voice is only_voice


def test_frost_effect_iterations_grow_linearly_by_event():
    random.seed(0)

    score = frost_effect(Score([Voice([Tone(440.0, duration=1.0)])]), iterations=3)

    assert len(_event_frequencies(score, 0)) == 1
    assert len(_event_frequencies(score, 1)) == 3
    assert len(_event_frequencies(score, 2)) == 5
    assert len(_event_frequencies(score, 3)) == 7


def test_first_frost_event_edge_children_respect_per_edge_cent_bounds():
    random.seed(0)

    score = frost_effect(Score([Voice([Tone(440.0, duration=1.0)])]), iterations=1)
    first_event_frequencies = _event_frequencies(score, 1)
    lower_frequency = min(first_event_frequencies)
    upper_frequency = max(first_event_frequencies)

    lower_outward_cents = _cents_between(lower_frequency, 440.0)
    upper_outward_cents = _cents_between(440.0, upper_frequency)

    assert lower_outward_cents >= FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS
    assert lower_outward_cents <= FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS
    assert upper_outward_cents >= FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS
    assert upper_outward_cents <= FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS


def test_multi_voice_input_is_treated_as_one_frost_field():
    random.seed(0)
    seed_frequency_cluster =  [
        Voice([Tone(330.0, duration=1.0)]),
        Voice([Tone(440.0, duration=1.0)]),
        Voice([Tone(550.0, duration=1.0)]),
    ]

    score = frost_effect(
        Score(
            seed_frequency_cluster
        ),
        iterations=1,
    )
    source_frequencies = _event_frequencies(score, 0)
    first_event_frequencies = _event_frequencies(score, 1)
    new_frequencies = _find_frequencies_added_to_next_event(source_frequencies, first_event_frequencies)

    expected_new_fequencies_count = 2
    original_count = len(seed_frequency_cluster)

    assert len(source_frequencies) == original_count
    assert len(first_event_frequencies) == original_count + expected_new_fequencies_count
    assert len(new_frequencies) == expected_new_fequencies_count
    assert sum(frequency < min(source_frequencies) for frequency in new_frequencies) == 1
    assert sum(frequency > max(source_frequencies) for frequency in new_frequencies) == 1


def test_first_frost_event_expands_multi_voice_onset_cluster_as_one_field():
    random.seed(0)
    score = frost_effect(
        Score(
            [
                Voice([Tone(330.0, duration=1.0)]),
                Voice([Tone(440.0, duration=1.0)]),
                Voice([Tone(550.0, duration=1.0)]),
            ]
        ),
        iterations=1,
    )

    source_frequencies = _event_frequencies(score, 0)
    first_event_frequencies = _event_frequencies(score, 1)
    new_frequencies = _find_frequencies_added_to_next_event(
        source_frequencies,
        first_event_frequencies,
    )

    assert source_frequencies == [
        pytest.approx(330.0),
        pytest.approx(440.0),
        pytest.approx(550.0),
    ]
    assert len(first_event_frequencies) == 5
    assert len(new_frequencies) == 2
    assert sum(frequency < 330.0 for frequency in new_frequencies) == 1
    assert sum(frequency > 550.0 for frequency in new_frequencies) == 1


def test_first_frost_event_uses_earliest_onset_not_later_delayed_voice():
    random.seed(0)
    score = frost_effect(
        Score(
            [
                Voice([Tone(330.0, duration=1.0)]),
                Voice([Tone(0.0, duration=0.5), Tone(550.0, duration=1.0)]),
            ]
        ),
        iterations=1,
    )

    first_event_frequencies = _event_frequencies(score, 1)

    assert len(first_event_frequencies) == 3
    assert any(frequency == pytest.approx(330.0) for frequency in first_event_frequencies)
    assert all(frequency != pytest.approx(550.0) for frequency in first_event_frequencies)
    assert min(first_event_frequencies) < 330.0
    assert max(first_event_frequencies) > 330.0


def test_multi_voice_input_keeps_growing_linearly_across_multiple_events():
    random.seed(0)
    seed_frequency_cluster = [
        Voice([Tone(330.0, duration=1.0)]),
        Voice([Tone(440.0, duration=1.0)]),
        Voice([Tone(550.0, duration=1.0)]),
    ]
    expected_new_frequencies_per_iteration = 2
    requested_iterations = 3
    original_count = len(seed_frequency_cluster)

    score = frost_effect(
        Score(seed_frequency_cluster),
        iterations=requested_iterations,
    )

    for generation in range(requested_iterations + 1):
        expected_event_count = original_count + (expected_new_frequencies_per_iteration * generation)

        assert len(_event_frequencies(score, generation)) == expected_event_count


def test_frost_effect_schedules_each_frost_event_after_previous_event():
    random.seed(0)
    requested_iterations = 3
    expected_new_edge_tones_per_iteration = 2

    score = frost_effect(Score([Voice([Tone(440.0, duration=1.0)])]), iterations=requested_iterations)

    for generation in range(1, requested_iterations + 1):
        previous_event_voices = _event_voices(score, generation - 1)
        current_event_voices = _event_voices(score, generation)
        previous_event_end_time = max(_voice_end_time(voice) for voice in previous_event_voices)
        current_event_start_time = min(_voice_start_time(voice) for voice in current_event_voices)
        previous_event_frequencies = _event_frequencies(score, generation - 1)
        current_event_frequencies = _event_frequencies(score, generation)

        assert current_event_start_time >= previous_event_end_time
        if generation == 1:
            _assert_event_has_controlled_edge_stagger(score, generation)
        else:
            _assert_new_edges_have_controlled_stagger(score, previous_event_frequencies, generation)

        new_frequencies = _find_frequencies_added_to_next_event(
            previous_event_frequencies,
            current_event_frequencies,
        )

        assert len(new_frequencies) == expected_new_edge_tones_per_iteration


def test_frost_effect_extends_only_the_current_pitch_edges():
    random.seed(0)

    score = frost_effect(Score([Voice([Tone(440.0, duration=1.0)])]), iterations=3)
    previous_frequencies = _event_frequencies(score, 0)

    for generation in range(1, 4):
        event_frequencies = _event_frequencies(score, generation)

        assert min(event_frequencies) < min(previous_frequencies)
        assert max(event_frequencies) > max(previous_frequencies)

        previous_frequencies = event_frequencies


def test_frost_effect_replays_previous_event_and_adds_two_edge_tones():
    random.seed(0)

    score = frost_effect(Score([Voice([Tone(440.0, duration=1.0)])]), iterations=3)
    previous_frequencies = _event_frequencies(score, 0)

    for generation in range(1, 4):
        event_frequencies = _event_frequencies(score, generation)
        new_frequencies = _find_frequencies_added_to_next_event(previous_frequencies, event_frequencies)

        assert len(new_frequencies) == 2
        assert sum(frequency < min(previous_frequencies) for frequency in new_frequencies) == 1
        assert sum(frequency > max(previous_frequencies) for frequency in new_frequencies) == 1

        previous_frequencies = event_frequencies


def test_frost_effect_edge_children_move_within_bounded_cent_range():
    random.seed(0)

    score = frost_effect(Score([Voice([Tone(440.0, duration=1.0)])]), iterations=3)
    previous_frequencies = _event_frequencies(score, 0)

    for generation in range(1, 4):
        event_frequencies = _event_frequencies(score, generation)
        previous_lowest = min(previous_frequencies)
        previous_highest = max(previous_frequencies)
        new_lowest = min(event_frequencies)
        new_highest = max(event_frequencies)

        lower_edge_movement_cents = _cents_between(new_lowest, previous_lowest)
        upper_edge_movement_cents = _cents_between(previous_highest, new_highest)

        assert lower_edge_movement_cents >= FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS
        assert lower_edge_movement_cents <= FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS
        assert upper_edge_movement_cents >= FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS
        assert upper_edge_movement_cents <= FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS

        previous_frequencies = event_frequencies
