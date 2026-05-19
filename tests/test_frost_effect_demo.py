import pytest

from composition.parser import generate_score_plan
from composition.schema import CompositionDocumentInput
from composition.transformer import transform_score
from score_model.score import Score
from score_model.traversal import flatten_voice_tones
from transforms.geological.frost_effect import (
    FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS,
)


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

    if len(previous_event_frequencies) == 1:
        side_separation = new_edge_start_times[1] - new_edge_start_times[0]
        assert side_separation >= FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS
        assert side_separation <= FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS


def _assert_event_follows(previous_event_voices, event_voices):
    previous_event_end_time = max(_voice_end_time(voice) for voice in previous_event_voices)
    event_start_time = min(_voice_start_time(voice) for voice in event_voices)

    assert event_start_time >= previous_event_end_time


def _build_single_seed_frost_composition() -> CompositionDocumentInput:
    return {
        "description": "A frost demo that starts from a single seed tone and renders three frost events.",
        "motifs": {
            "seed_tone": ["440:1.0"],
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {
                            "motifs": ["seed_tone"],
                        }
                    ]
                }
            ],
            "score_transforms": [
                {
                    "name": "frost_effect",
                    "params": {
                        "iterations": 3,
                    },
                }
            ],
        },
    }


def test_frost_single_seed_demo_loads_and_sequences_original_then_frost():
    score = transform_score(generate_score_plan(_build_single_seed_frost_composition()))

    assert isinstance(score, Score)
    assert len(score.voices) == 16
    assert flatten_voice_tones(score.voices[0])[0].frequency == pytest.approx(440.0)

    source_event_voices = score.voices[0:1]
    first_event_voices = score.voices[1:4]
    second_event_voices = score.voices[4:9]
    third_event_voices = score.voices[9:16]
    source_event_frequencies = [_audible_frequency(voice) for voice in source_event_voices]
    first_event_frequencies = {_audible_frequency(voice) for voice in first_event_voices}

    assert any(frequency == pytest.approx(440.0) for frequency in first_event_frequencies)
    assert any(frequency < 440.0 for frequency in first_event_frequencies)
    assert any(frequency > 440.0 for frequency in first_event_frequencies)
    assert len(second_event_voices) == 5
    assert len(third_event_voices) == 7

    source_event_end_time = max(_voice_end_time(voice) for voice in source_event_voices)
    assert min(_voice_start_time(voice) for voice in first_event_voices) >= source_event_end_time
    _assert_controlled_edge_stagger(first_event_voices, source_event_frequencies)
    _assert_event_follows(second_event_voices, third_event_voices)
