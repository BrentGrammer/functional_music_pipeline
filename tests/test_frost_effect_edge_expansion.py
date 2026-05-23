import math

import pytest

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from transforms.geological.frost_effect import (
    FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS,
    FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS,
    FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS,
    _cents_to_frequency_ratio,
    _find_frost_edge_voices,
    _first_audible_start_time_voices,
    _first_audible_tone_with_start_time,
    _jitter_frequency_down_within_bounds,
    _jitter_frequency_up_within_bounds,
    frost_effect,
)

CENTS_PER_OCTAVE = 1200.0

#### TEST HELPERS #####
def _first_audible_frequency(voice: Voice) -> float | None:
    for tone in flatten_voice_tones(voice):
        if tone.frequency > 0 and tone.amplitude > 0 and tone.duration > 0:
            return tone.frequency

    return None


def _event_frequencies(score: Score, event_number: int) -> list[float]:
    frequencies = []

    for voice in score.voices:
        if getattr(voice, "frost_generation_index", 0) != event_number:
            continue

        frequency = _first_audible_frequency(voice)
        if frequency is not None:
            frequencies.append(frequency)

    return frequencies


def _event_voices(score: Score, event_number: int) -> list[Voice]:
    return [
        voice
        for voice in score.voices
        if getattr(voice, "frost_generation_index", 0) == event_number
        and _first_audible_frequency(voice) is not None
    ]


def _voice_start_time(voice: Voice) -> float:
    voice_tones = flatten_voice_tones(voice)
    if voice_tones and voice_tones[0].frequency == 0:
        return voice_tones[0].duration

    return 0.0


def _voice_end_time(voice: Voice) -> float:
    return sum(tone.duration for tone in flatten_voice_tones(voice))


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


def _assert_event_has_controlled_edge_stagger(
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
    replayed_start_times = sorted(_voice_start_time(voice) for voice in replayed_voices)
    new_edge_start_times = sorted(_voice_start_time(voice) for voice in new_edge_voices)

    assert len(new_frequencies) == 2
    assert len(replayed_start_times) == len(replayed_voices)
    assert len(set(replayed_start_times)) == len(replayed_start_times)
    assert len(new_edge_start_times) == 2

    assert new_edge_start_times[0] >= replayed_start_times[-1]
    assert new_edge_start_times[0] - replayed_start_times[0] >= FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS

    if len(previous_event_frequencies) == 1:
        side_separation = new_edge_start_times[1] - new_edge_start_times[0]

        assert side_separation >= FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS
        assert side_separation <= FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS

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
####### END TEST HELPERS ########

def test_cents_to_frequency_ratio_converts_octaves_and_unisons():
    assert _cents_to_frequency_ratio(0.0) == pytest.approx(1.0)
    assert _cents_to_frequency_ratio(1200.0) == pytest.approx(2.0)
    assert _cents_to_frequency_ratio(-1200.0) == pytest.approx(0.5)


def test_frost_generation_indices_map_to_audible_event_count():
    score = frost_effect(Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])]), iterations=2)

    assert _event_frequencies(score, 0) == [pytest.approx(440.0)]
    assert len(_event_frequencies(score, 1)) == 3
    assert len(_event_frequencies(score, 2)) == 5
    assert len(_event_voices(score, 0)) == 1
    assert len(_event_voices(score, 1)) == 3
    assert len(_event_voices(score, 2)) == 5


def test_first_frost_event_delays_only_new_edge_tones_within_controlled_bounds():
    score = frost_effect(Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])]), iterations=1)

    source_event_end_time = max(_voice_end_time(voice) for voice in _event_voices(score, 0))
    first_event_frequencies = _event_frequencies(score, 1)
    replayed_voice = _find_event_voice_by_frequency(score, 1, 440.0)

    assert len(first_event_frequencies) == 3
    assert _voice_start_time(replayed_voice) >= source_event_end_time
    _assert_event_has_controlled_edge_stagger(score, [440.0], 1)


def test_first_frost_event_expands_each_cluster_tone_as_its_own_local_seed():
    low_frequency = 330.0
    middle_frequency = 440.0
    high_frequency = 550.0
    seed_duration_seconds = 1.0
    source_frequencies = [
        pytest.approx(low_frequency),
        pytest.approx(middle_frequency),
        pytest.approx(high_frequency),
    ]

    score = frost_effect(
        Score(
            [
                Voice([Phrase([Motif("<test>", [Tone(low_frequency, duration=seed_duration_seconds)])])]),
                Voice([Phrase([Motif("<test>", [Tone(middle_frequency, duration=seed_duration_seconds)])])]),
                Voice([Phrase([Motif("<test>", [Tone(high_frequency, duration=seed_duration_seconds)])])]),
            ]
        ),
        iterations=1,
    )

    source_event_end_time = max(_voice_end_time(voice) for voice in _event_voices(score, 0))
    first_frost_frequencies = _event_frequencies(score, 1)
    new_frequencies = _find_frequencies_added_to_next_event(
        _event_frequencies(score, 0),
        first_frost_frequencies,
    )

    assert _event_frequencies(score, 0) == source_frequencies
    assert len(first_frost_frequencies) == 9
    assert len(new_frequencies) == 6
    assert sum(frequency == pytest.approx(low_frequency) for frequency in first_frost_frequencies) == 1
    assert sum(frequency == pytest.approx(middle_frequency) for frequency in first_frost_frequencies) == 1
    assert sum(frequency == pytest.approx(high_frequency) for frequency in first_frost_frequencies) == 1
    assert min(_event_start_times(score, 1)) >= source_event_end_time


def test_second_frost_event_replays_previous_event_and_staggers_new_edges():
    score = frost_effect(Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])]), iterations=2)

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
    _assert_event_has_controlled_edge_stagger(score, first_frost_event_frequencies, 2)


def test_cluster_frost_events_replay_previous_event_and_add_two_edges_per_seed():
    low_frequency = 330.0
    middle_frequency = 440.0
    high_frequency = 550.0
    seed_duration_seconds = 1.0
    requested_iterations = 3
    new_voices_per_generation = 6

    score = frost_effect(
        Score(
            [
                Voice([Phrase([Motif("<test>", [Tone(low_frequency, duration=seed_duration_seconds)])])]),
                Voice([Phrase([Motif("<test>", [Tone(middle_frequency, duration=seed_duration_seconds)])])]),
                Voice([Phrase([Motif("<test>", [Tone(high_frequency, duration=seed_duration_seconds)])])]),
            ]
        ),
        iterations=requested_iterations,
    )

    previous_event_frequencies = _event_frequencies(score, 0)

    assert previous_event_frequencies == [
        pytest.approx(low_frequency),
        pytest.approx(middle_frequency),
        pytest.approx(high_frequency),
    ]

    for event_number in range(1, requested_iterations + 1):
        current_event_frequencies = _event_frequencies(score, event_number)
        new_frequencies = _find_frequencies_added_to_next_event(
            previous_event_frequencies,
            current_event_frequencies,
        )

        assert len(current_event_frequencies) == len(previous_event_frequencies) + new_voices_per_generation
        assert len(new_frequencies) == new_voices_per_generation
        assert all(frequency in current_event_frequencies for frequency in previous_event_frequencies)
        assert min(new_frequencies) < min(previous_event_frequencies)
        assert max(new_frequencies) > max(previous_event_frequencies)

        previous_event_frequencies = current_event_frequencies


def test_repeated_frost_calls_expand_every_existing_audible_seed():
    seed_frequency = 440.0
    seed_duration_seconds = 1.0
    generated_voices_per_seed = 3
    source_event_count = 1
    first_event_count = generated_voices_per_seed
    second_call_seed_count = source_event_count + first_event_count
    second_event_count = second_call_seed_count * generated_voices_per_seed
    third_call_seed_count = source_event_count + first_event_count + second_event_count
    third_event_count = third_call_seed_count * generated_voices_per_seed

    score = Score([Voice([Phrase([Motif("<test>", [Tone(seed_frequency, duration=seed_duration_seconds)])])])])
    score = frost_effect(score, iterations=1)
    score = frost_effect(score, iterations=1)
    score = frost_effect(score, iterations=1)

    assert len(_event_frequencies(score, 0)) == source_event_count
    assert len(_event_frequencies(score, 1)) == first_event_count
    assert len(_event_frequencies(score, 2)) == second_event_count
    assert len(_event_frequencies(score, 3)) == third_event_count


def test_first_audible_tone_with_start_time_returns_single_seed_at_zero():
    voice = Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])

    start_tone = _first_audible_tone_with_start_time(voice)

    assert start_tone is not None
    tone, start_time = start_tone
    assert tone.frequency == pytest.approx(440.0)
    assert start_time == pytest.approx(0.0)


def test_voice_start_time_uses_leading_silence_duration():
    leading_silence_duration = 0.5
    voice = Voice([Phrase([Motif("<test>", [Tone(0.0, duration=leading_silence_duration), Tone(440.0, duration=1.0)])])])

    assert _voice_start_time(voice) == pytest.approx(leading_silence_duration)


def test_first_audible_start_time_voices_collect_simultaneous_cluster_voices():
    score = Score(
        [
            Voice([Phrase([Motif("<test>", [Tone(330.0, duration=1.0)])])]),
            Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])]),
            Voice([Phrase([Motif("<test>", [Tone(550.0, duration=1.0)])])]),
        ]
    )

    start_time_voices = _first_audible_start_time_voices(score)

    assert [_voice_start_time(voice) for voice in start_time_voices] == [pytest.approx(0.0)] * 3
    assert [_first_audible_frequency(voice) for voice in start_time_voices] == [
        pytest.approx(330.0),
        pytest.approx(440.0),
        pytest.approx(550.0),
    ]


def test_first_audible_start_time_voices_exclude_later_delayed_voice():
    score = Score(
        [
            Voice([Phrase([Motif("<test>", [Tone(330.0, duration=1.0)])])]),
            Voice([Phrase([Motif("<test>", [Tone(0.0, duration=0.5), Tone(440.0, duration=1.0)])])]),
        ]
    )

    start_time_voices = _first_audible_start_time_voices(score)

    assert [_first_audible_frequency(voice) for voice in start_time_voices] == [
        pytest.approx(330.0),
    ]


def test_first_audible_start_time_voices_skip_voice_with_no_audible_tone():
    audible_frequency = 330.0
    score = Score(
        [
            Voice([Phrase([Motif("<test>", [Tone(audible_frequency, duration=1.0)])])]),
            Voice([Phrase([Motif("<test>", [Tone(0.0, duration=0.5), Tone(440.0, duration=1.0, amplitude=0.0)])])]),
        ]
    )

    start_time_voices = _first_audible_start_time_voices(score)

    assert [_first_audible_frequency(voice) for voice in start_time_voices] == [
        pytest.approx(audible_frequency),
    ]


def test_first_audible_start_time_voices_use_first_tone_of_melodic_line():
    score = Score(
        [
            Voice(
                [
                    Phrase(
                        [
                            Motif(
                                "<test>",
                                [
                                    Tone(330.0, duration=1.0),
                                    Tone(440.0, duration=1.0),
                                    Tone(550.0, duration=1.0),
                                ],
                            )
                        ]
                    )
                ]
            )
        ]
    )

    start_time_voices = _first_audible_start_time_voices(score)

    assert [_first_audible_frequency(voice) for voice in start_time_voices] == [
        pytest.approx(330.0),
    ]


def test_jitter_frequency_down_within_bounds_moves_down_by_bounded_cents():
    child_frequency = _jitter_frequency_down_within_bounds(440.0)
    outward_cents = _cents_between(child_frequency, 440.0)

    assert child_frequency < 440.0
    assert outward_cents >= FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS
    assert outward_cents <= FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS


def test_jitter_frequency_up_within_bounds_moves_up_by_bounded_cents():
    child_frequency = _jitter_frequency_up_within_bounds(440.0)
    outward_cents = _cents_between(440.0, child_frequency)

    assert child_frequency > 440.0
    assert outward_cents >= FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS
    assert outward_cents <= FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS


def test_find_frost_edge_voices_identifies_lowest_and_highest_voice_in_any_order():
    upper_frequency = 481.0
    lower_frequency = 418.0
    center_voice = Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])
    upper_voice = Voice([Phrase([Motif("<test>", [Tone(upper_frequency, duration=1.0)])])])
    lower_voice = Voice([Phrase([Motif("<test>", [Tone(lower_frequency, duration=1.0)])])])

    lower_edge_voice, upper_edge_voice = _find_frost_edge_voices([center_voice, upper_voice, lower_voice])

    assert lower_edge_voice is not None
    assert upper_edge_voice is not None
    assert lower_edge_voice is lower_voice
    assert upper_edge_voice is upper_voice


def test_find_frost_edge_voices_ignores_silent_voices():
    silence = 0.0
    silent_low_voice = Voice([Phrase([Motif("<test>", [Tone(10.0, duration=1.0, amplitude=silence)])])])
    silent_high_voice = Voice([Phrase([Motif("<test>", [Tone(4000.0, duration=1.0, amplitude=silence)])])])
    lower_voice = Voice([Phrase([Motif("<test>", [Tone(430.0, duration=1.0, amplitude=silence + 1.0)])])])
    upper_voice = Voice([Phrase([Motif("<test>", [Tone(450.0, duration=1.0, amplitude=silence + 1.0)])])])

    lower_edge_voice, upper_edge_voice = _find_frost_edge_voices([silent_low_voice, upper_voice, silent_high_voice, lower_voice])

    assert lower_edge_voice is not None
    assert upper_edge_voice is not None
    assert lower_edge_voice is lower_voice
    assert upper_edge_voice is upper_voice


def test_find_frost_edge_voices_uses_first_audible_tone_in_delayed_voice():
    lower_voice_silence_duration = 0.25
    lower_voice_first_audible_frequency = 410.0
    upper_voice_silence_duration = 0.50
    upper_voice_first_audible_frequency = 470.0
    center_voice_frequency = 440.0

    delayed_lower_voice = Voice(
        [Phrase([Motif("<test>", [Tone(0.0, duration=lower_voice_silence_duration), Tone(lower_voice_first_audible_frequency, duration=1.0)])])]
    )
    delayed_upper_voice = Voice(
        [Phrase([Motif("<test>", [Tone(0.0, duration=upper_voice_silence_duration), Tone(upper_voice_first_audible_frequency, duration=1.0)])])]
    )
    center_voice = Voice([Phrase([Motif("<test>", [Tone(center_voice_frequency, duration=1.0)])])])

    lower_edge_voice, upper_edge_voice = _find_frost_edge_voices([center_voice, delayed_upper_voice, delayed_lower_voice])

    assert lower_edge_voice is not None
    assert upper_edge_voice is not None
    assert lower_edge_voice is delayed_lower_voice
    assert upper_edge_voice is delayed_upper_voice


def test_find_frost_edge_voices_returns_none_edges_when_no_audible_voices_exist():
    lower_edge_voice, upper_edge_voice = _find_frost_edge_voices(
        [
            Voice([]),
            Voice([Phrase([Motif("<test>", [Tone(0.0, duration=1.0)])])]),
            Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0, amplitude=0.0)])])]),
        ]
    )

    assert lower_edge_voice is None
    assert upper_edge_voice is None


def test_find_frost_edge_voices_returns_same_voice_for_single_audible_voice():
    frequency = 440.0
    voice = Voice([Phrase([Motif("<test>", [Tone(frequency, duration=1.0)])])])

    lower_edge_voice, upper_edge_voice = _find_frost_edge_voices([voice])

    assert lower_edge_voice is not None
    assert upper_edge_voice is not None
    assert lower_edge_voice is voice
    assert upper_edge_voice is voice


def test_frost_effect_iterations_grow_linearly_by_event():
    score = frost_effect(Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])]), iterations=3)

    assert len(_event_frequencies(score, 0)) == 1
    assert len(_event_frequencies(score, 1)) == 3
    assert len(_event_frequencies(score, 2)) == 5
    assert len(_event_frequencies(score, 3)) == 7


def test_first_frost_event_edge_children_respect_per_edge_cent_bounds():
    score = frost_effect(Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])]), iterations=1)
    first_event_frequencies = _event_frequencies(score, 1)
    lower_frequency = min(first_event_frequencies)
    upper_frequency = max(first_event_frequencies)

    lower_outward_cents = _cents_between(lower_frequency, 440.0)
    upper_outward_cents = _cents_between(440.0, upper_frequency)

    assert lower_outward_cents >= FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS
    assert lower_outward_cents <= FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS
    assert upper_outward_cents >= FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS
    assert upper_outward_cents <= FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS


def test_multi_note_melodic_line_expands_every_audible_note():
    low_frequency = 330.0
    middle_frequency = 440.0
    high_frequency = 550.0
    source_frequencies = [low_frequency, middle_frequency, high_frequency]
    seed_duration_seconds = 1.0
    generated_voice_count = 9

    melodic_line = Voice(
        [
            Phrase(
                [
                    Motif(
                        "<test>",
                        [
                            Tone(low_frequency, duration=seed_duration_seconds),
                            Tone(middle_frequency, duration=seed_duration_seconds),
                            Tone(high_frequency, duration=seed_duration_seconds),
                        ],
                    )
                ]
            )
        ]
    )

    score = frost_effect(
        Score([melodic_line]),
        iterations=1,
    )
    first_event_frequencies = _event_frequencies(score, 1)
    first_event_start_times = _event_start_times(score, 1)

    assert source_frequencies == [
        pytest.approx(low_frequency),
        pytest.approx(middle_frequency),
        pytest.approx(high_frequency),
    ]
    assert len(first_event_frequencies) == generated_voice_count
    assert sum(frequency == pytest.approx(low_frequency) for frequency in first_event_frequencies) == 1
    assert sum(frequency == pytest.approx(middle_frequency) for frequency in first_event_frequencies) == 1
    assert sum(frequency == pytest.approx(high_frequency) for frequency in first_event_frequencies) == 1
    assert min(first_event_start_times) >= 1.0
    assert max(first_event_start_times) >= 3.0


def test_first_frost_event_replays_every_voice_in_multi_voice_cluster():
    low_frequency = 330.0
    middle_frequency = 440.0
    high_frequency = 550.0
    seed_duration_seconds = 1.0
    source_frequencies = [
        pytest.approx(low_frequency),
        pytest.approx(middle_frequency),
        pytest.approx(high_frequency),
    ]

    score = frost_effect(
        Score(
            [
                Voice([Phrase([Motif("<test>", [Tone(low_frequency, duration=seed_duration_seconds)])])]),
                Voice([Phrase([Motif("<test>", [Tone(middle_frequency, duration=seed_duration_seconds)])])]),
                Voice([Phrase([Motif("<test>", [Tone(high_frequency, duration=seed_duration_seconds)])])]),
            ]
        ),
        iterations=1,
    )

    first_event_frequencies = _event_frequencies(score, 1)
    new_frequencies = _find_frequencies_added_to_next_event(
        _event_frequencies(score, 0),
        first_event_frequencies,
    )

    assert _event_frequencies(score, 0) == source_frequencies
    assert len(first_event_frequencies) == 9
    assert len(new_frequencies) == 6
    assert sum(frequency == pytest.approx(low_frequency) for frequency in first_event_frequencies) == 1
    assert sum(frequency == pytest.approx(middle_frequency) for frequency in first_event_frequencies) == 1
    assert sum(frequency == pytest.approx(high_frequency) for frequency in first_event_frequencies) == 1


def test_first_frost_event_includes_later_delayed_voice_as_its_own_seed():
    early_frequency = 330.0
    delayed_frequency = 550.0
    leading_silence_seconds = 0.5
    seed_duration_seconds = 1.0

    score = frost_effect(
        Score(
            [
                Voice([Phrase([Motif("<test>", [Tone(early_frequency, duration=seed_duration_seconds)])])]),
                Voice([Phrase([Motif("<test>", [Tone(0.0, duration=leading_silence_seconds), Tone(delayed_frequency, duration=seed_duration_seconds)])])]),
            ]
        ),
        iterations=1,
    )

    first_event_frequencies = _event_frequencies(score, 1)
    first_event_start_times = _event_start_times(score, 1)

    assert len(first_event_frequencies) == 6
    assert any(frequency == pytest.approx(early_frequency) for frequency in first_event_frequencies)
    assert any(frequency == pytest.approx(delayed_frequency) for frequency in first_event_frequencies)
    assert min(first_event_frequencies) < early_frequency
    assert max(first_event_frequencies) > delayed_frequency
    assert min(first_event_start_times) >= seed_duration_seconds
    assert max(first_event_start_times) >= leading_silence_seconds + seed_duration_seconds


def test_multi_voice_input_keeps_growing_linearly_across_multiple_events():
    low_frequency = 330.0
    middle_frequency = 440.0
    high_frequency = 550.0
    seed_duration_seconds = 1.0
    seed_frequency_cluster = [
        Voice([Phrase([Motif("<test>", [Tone(low_frequency, duration=seed_duration_seconds)])])]),
        Voice([Phrase([Motif("<test>", [Tone(middle_frequency, duration=seed_duration_seconds)])])]),
        Voice([Phrase([Motif("<test>", [Tone(high_frequency, duration=seed_duration_seconds)])])]),
    ]
    expected_new_frequencies_per_iteration = 6
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
    requested_iterations = 3
    expected_new_edge_tones_per_iteration = 2

    score = frost_effect(Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])]), iterations=requested_iterations)

    for generation in range(1, requested_iterations + 1):
        previous_event_voices = _event_voices(score, generation - 1)
        current_event_voices = _event_voices(score, generation)
        previous_event_end_time = max(_voice_end_time(voice) for voice in previous_event_voices)
        current_event_start_time = min(_voice_start_time(voice) for voice in current_event_voices)
        previous_event_frequencies = _event_frequencies(score, generation - 1)
        current_event_frequencies = _event_frequencies(score, generation)

        assert current_event_start_time >= previous_event_end_time
        _assert_event_has_controlled_edge_stagger(score, previous_event_frequencies, generation)

        new_frequencies = _find_frequencies_added_to_next_event(
            previous_event_frequencies,
            current_event_frequencies,
        )

        assert len(new_frequencies) == expected_new_edge_tones_per_iteration


def test_frost_effect_extends_only_the_current_pitch_edges():
    score = frost_effect(Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])]), iterations=3)
    previous_frequencies = _event_frequencies(score, 0)

    for generation in range(1, 4):
        event_frequencies = _event_frequencies(score, generation)

        assert min(event_frequencies) < min(previous_frequencies)
        assert max(event_frequencies) > max(previous_frequencies)

        previous_frequencies = event_frequencies


def test_frost_effect_replays_previous_event_and_adds_two_edge_tones():
    score = frost_effect(Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])]), iterations=3)
    previous_frequencies = _event_frequencies(score, 0)

    for generation in range(1, 4):
        event_frequencies = _event_frequencies(score, generation)
        new_frequencies = _find_frequencies_added_to_next_event(previous_frequencies, event_frequencies)

        assert len(new_frequencies) == 2
        assert sum(frequency < min(previous_frequencies) for frequency in new_frequencies) == 1
        assert sum(frequency > max(previous_frequencies) for frequency in new_frequencies) == 1

        previous_frequencies = event_frequencies


def test_frost_effect_edge_children_move_within_bounded_cent_range():
    score = frost_effect(Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])]), iterations=3)
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
