import pytest

from composition.parser import generate_score_plan
from composition.schema import CompositionDocumentInput
from composition.transformer import transform_score
from score_model.score import Score
from score_model.traversal import flatten_voice_tones
from transforms.geological.frost_effect import FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS


def _voice_start_time(voice):
    voice_tones = flatten_voice_tones(voice)
    if voice_tones and voice_tones[0].frequency == 0:
        return voice_tones[0].duration
    return 0.0


def _voice_end_time(voice):
    return sum(tone.duration for tone in flatten_voice_tones(voice))


def _audible_frequency(voice):
    voice_tones = flatten_voice_tones(voice)
    if len(voice_tones) == 1:
        return voice_tones[0].frequency
    return voice_tones[1].frequency


def _find_new_edge_voices(event_voices, previous_event_frequencies):
    remaining_frequencies = list(previous_event_frequencies)
    replayed_voices = []
    new_edge_voices = []

    for voice in event_voices:
        frequency = _audible_frequency(voice)
        matching_index = next(
            (
                index
                for index, previous_frequency in enumerate(remaining_frequencies)
                if frequency == pytest.approx(previous_frequency)
            ),
            None,
        )
        if matching_index is None:
            new_edge_voices.append(voice)
        else:
            replayed_voices.append(voice)
            remaining_frequencies.pop(matching_index)

    return replayed_voices, new_edge_voices


def _assert_controlled_edge_stagger(event_voices, previous_event_frequencies):
    replayed_voices, new_edge_voices = _find_new_edge_voices(event_voices, previous_event_frequencies)
    replayed_start_times = sorted(_voice_start_time(voice) for voice in replayed_voices)
    new_edge_start_times = sorted(_voice_start_time(voice) for voice in new_edge_voices)

    assert len(new_edge_start_times) == 2
    assert new_edge_start_times[0] >= replayed_start_times[-1]
    assert new_edge_start_times[0] - replayed_start_times[0] >= FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS


def _assert_event_follows(previous_event_voices, event_voices):
    previous_event_end_time = max(_voice_end_time(voice) for voice in previous_event_voices)
    event_start_time = min(_voice_start_time(voice) for voice in event_voices)

    assert event_start_time >= previous_event_end_time


def _build_cluster_frost_composition() -> CompositionDocumentInput:
    return {
        "description": "A frost demo that starts from a three-tone cluster and renders four frost events.",
        "motifs": {
            "seed_low": ["330:1.0"],
            "seed_mid": ["440:1.0"],
            "seed_high": ["550:1.0"],
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {
                            "motifs": ["seed_low"],
                        }
                    ]
                },
                {
                    "phrases": [
                        {
                            "motifs": ["seed_mid"],
                        }
                    ]
                },
                {
                    "phrases": [
                        {
                            "motifs": ["seed_high"],
                        }
                    ]
                }
            ],
            "score_transforms": [
                {
                    "name": "frost_effect",
                    "params": {
                        "iterations": 4,
                    },
                }
            ],
        },
    }


def test_frost_cluster_demo_grows_by_audible_events():
    score = transform_score(generate_score_plan(_build_cluster_frost_composition()))

    assert isinstance(score, Score)

    source_event_voices = score.voices[0:3]
    first_event_voices = score.voices[3:8]
    second_event_voices = score.voices[8:15]
    third_event_voices = score.voices[15:24]
    fourth_event_voices = score.voices[24:35]

    assert len(score.voices) == 35
    assert len(source_event_voices) == 3
    assert len(first_event_voices) == 5
    assert len(second_event_voices) == 7
    assert len(third_event_voices) == 9
    assert len(fourth_event_voices) == 11

    source_event_frequencies = {_audible_frequency(voice) for voice in source_event_voices}
    first_event_frequencies = {_audible_frequency(voice) for voice in first_event_voices}
    second_event_frequencies = {_audible_frequency(voice) for voice in second_event_voices}
    third_event_frequencies = {_audible_frequency(voice) for voice in third_event_voices}
    fourth_event_frequencies = {_audible_frequency(voice) for voice in fourth_event_voices}

    assert sorted(source_event_frequencies) == [
        pytest.approx(330.0),
        pytest.approx(440.0),
        pytest.approx(550.0),
    ]
    assert source_event_frequencies.issubset(first_event_frequencies)
    assert any(frequency < min(source_event_frequencies) for frequency in first_event_frequencies)
    assert any(frequency > max(source_event_frequencies) for frequency in first_event_frequencies)
    assert first_event_frequencies.issubset(second_event_frequencies)
    assert second_event_frequencies.issubset(third_event_frequencies)
    assert third_event_frequencies.issubset(fourth_event_frequencies)

    _assert_controlled_edge_stagger(first_event_voices, list(source_event_frequencies))
    _assert_event_follows(first_event_voices, second_event_voices)
    _assert_event_follows(second_event_voices, third_event_voices)
    _assert_event_follows(third_event_voices, fourth_event_voices)
