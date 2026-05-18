import pytest

from composition.parser import parse_composition
from score_model.score import Score
from score_model.traversal import iter_voice_tones
from transforms.geological.frost_effect import (
    FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS,
    FROST_ROLE_CENTER,
    FROST_ROLE_SIDE,
)


def _voice_start_time(voice):
    voice_tones = iter_voice_tones(voice)
    if voice_tones and voice_tones[0].frequency == 0:
        return voice_tones[0].duration

    return 0.0


def _voice_end_time(voice):
    return sum(tone.duration for tone in iter_voice_tones(voice))


def _voices_with_role(voices, role):
    return [
        voice
        for voice in voices
        if getattr(voice, "frost_role", FROST_ROLE_CENTER) == role
    ]


def _assert_controlled_edge_stagger(voices):
    center_voices = _voices_with_role(voices, FROST_ROLE_CENTER)
    side_voices = _voices_with_role(voices, FROST_ROLE_SIDE)
    center_start_times = sorted(_voice_start_time(voice) for voice in center_voices)
    side_start_times = sorted(_voice_start_time(voice) for voice in side_voices)

    assert len(center_start_times) == len(center_voices)
    assert len(set(center_start_times)) == len(center_start_times)
    assert len(side_start_times) == 2

    if len(center_voices) == 1:
        side_separation = side_start_times[1] - side_start_times[0]

        assert side_separation >= FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS
        assert side_separation <= FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS
    else:
        assert side_start_times[0] - center_start_times[0] >= FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS


def _assert_event_follows_and_overlaps(previous_event_voices, event_voices):
    previous_event_end_time = max(_voice_end_time(voice) for voice in previous_event_voices)
    event_start_time = min(_voice_start_time(voice) for voice in event_voices)

    assert event_start_time >= previous_event_end_time


def _build_single_seed_frost_composition() -> dict:
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
    score = parse_composition(_build_single_seed_frost_composition())

    assert isinstance(score, Score)
    assert len(score.voices) == 16
    assert len(iter_voice_tones(score.voices[0])) == 1
    assert len(iter_voice_tones(score.voices[1])) == 2
    assert len(iter_voice_tones(score.voices[2])) == 2
    assert len(iter_voice_tones(score.voices[3])) == 2
    assert len(iter_voice_tones(score.voices[4])) == 2
    assert len(iter_voice_tones(score.voices[5])) == 2
    assert len(iter_voice_tones(score.voices[6])) == 2
    assert len(iter_voice_tones(score.voices[7])) == 2
    assert len(iter_voice_tones(score.voices[8])) == 2
    assert len(iter_voice_tones(score.voices[9])) == 2
    assert len(iter_voice_tones(score.voices[10])) == 2
    assert len(iter_voice_tones(score.voices[11])) == 2
    assert len(iter_voice_tones(score.voices[12])) == 2
    assert len(iter_voice_tones(score.voices[13])) == 2
    assert len(iter_voice_tones(score.voices[14])) == 2
    assert len(iter_voice_tones(score.voices[15])) == 2
    assert iter_voice_tones(score.voices[0])[0].frequency == pytest.approx(440.0)

    source_event_voices = score.voices[0:1]
    first_event_voices = score.voices[1:4]
    second_event_voices = score.voices[4:9]
    third_event_voices = score.voices[9:16]
    first_event_frequencies = {iter_voice_tones(voice)[1].frequency for voice in first_event_voices}

    assert iter_voice_tones(score.voices[1])[0].frequency == 0
    assert iter_voice_tones(score.voices[1])[1].duration == pytest.approx(
        iter_voice_tones(score.voices[0])[0].duration
    )
    assert any(frequency == pytest.approx(440.0) for frequency in first_event_frequencies)
    assert any(frequency < 440.0 for frequency in first_event_frequencies)
    assert any(frequency > 440.0 for frequency in first_event_frequencies)
    assert len(second_event_voices) == 5
    assert len(third_event_voices) == 7

    source_event_end_time = max(_voice_end_time(voice) for voice in source_event_voices)
    _assert_controlled_edge_stagger(first_event_voices)
    assert min(_voice_start_time(voice) for voice in first_event_voices) >= source_event_end_time
    _assert_event_follows_and_overlaps(second_event_voices, third_event_voices)
