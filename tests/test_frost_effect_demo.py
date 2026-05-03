import pytest

from composition.parser import parse_composition
from score_model.score import Score
from transforms.frost import (
    FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS,
    FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS,
    FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS,
    FROST_ROLE_CENTER,
    FROST_ROLE_SIDE,
)


def _voice_start_time(voice):
    if voice.tones and voice.tones[0].frequency == 0:
        return voice.tones[0].duration

    return 0.0


def _voice_end_time(voice):
    return sum(tone.duration for tone in voice.tones)


def _voices_with_role(voices, role):
    return [
        voice
        for voice in voices
        if getattr(voice, "frost_role", FROST_ROLE_CENTER) == role
    ]


def _assert_controlled_edge_stagger(voices):
    center_voices = _voices_with_role(voices, FROST_ROLE_CENTER)
    side_voices = _voices_with_role(voices, FROST_ROLE_SIDE)
    event_anchor_time = min(_voice_start_time(voice) for voice in center_voices)
    latest_start_time = max(_voice_start_time(voice) for voice in voices)
    earliest_end_time = min(_voice_end_time(voice) for voice in voices)
    side_delays = sorted(_voice_start_time(voice) - event_anchor_time for voice in side_voices)

    assert len({_voice_start_time(voice) for voice in center_voices}) == 1
    assert len(side_delays) == 2

    if len(center_voices) == 1:
        side_separation = side_delays[1] - side_delays[0]

        assert side_delays[0] >= FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS
        assert side_delays[0] <= FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS
        assert side_separation >= FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS
        assert side_separation <= FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS
    else:
        for side_delay in side_delays:
            assert side_delay >= FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS
            assert side_delay <= FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS

    assert latest_start_time < earliest_end_time


def _assert_event_follows_and_overlaps(previous_event_voices, event_voices):
    previous_event_end_time = max(_voice_end_time(voice) for voice in previous_event_voices)
    event_start_time = min(_voice_start_time(voice) for voice in event_voices)
    latest_start_time = max(_voice_start_time(voice) for voice in event_voices)
    earliest_end_time = min(_voice_end_time(voice) for voice in event_voices)

    assert event_start_time >= previous_event_end_time
    assert latest_start_time < earliest_end_time


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
    assert len(score.voices[0].tones) == 1
    assert len(score.voices[1].tones) == 2
    assert len(score.voices[2].tones) == 2
    assert len(score.voices[3].tones) == 2
    assert len(score.voices[4].tones) == 2
    assert len(score.voices[5].tones) == 2
    assert len(score.voices[6].tones) == 2
    assert len(score.voices[7].tones) == 2
    assert len(score.voices[8].tones) == 2
    assert len(score.voices[9].tones) == 2
    assert len(score.voices[10].tones) == 2
    assert len(score.voices[11].tones) == 2
    assert len(score.voices[12].tones) == 2
    assert len(score.voices[13].tones) == 2
    assert len(score.voices[14].tones) == 2
    assert len(score.voices[15].tones) == 2
    assert score.voices[0].tones[0].frequency == pytest.approx(440.0)

    source_event_voices = score.voices[0:1]
    first_event_voices = score.voices[1:4]
    second_event_voices = score.voices[4:9]
    third_event_voices = score.voices[9:16]
    first_event_frequencies = {voice.tones[1].frequency for voice in first_event_voices}

    assert score.voices[1].tones[0].frequency == 0
    assert score.voices[1].tones[0].duration == pytest.approx(score.voices[0].tones[0].duration)
    assert any(frequency == pytest.approx(440.0) for frequency in first_event_frequencies)
    assert any(frequency < 440.0 for frequency in first_event_frequencies)
    assert any(frequency > 440.0 for frequency in first_event_frequencies)
    assert len(second_event_voices) == 5
    assert len(third_event_voices) == 7

    source_event_end_time = max(_voice_end_time(voice) for voice in source_event_voices)
    _assert_controlled_edge_stagger(first_event_voices)
    assert min(_voice_start_time(voice) for voice in first_event_voices) >= source_event_end_time
    _assert_event_follows_and_overlaps(first_event_voices, second_event_voices)
    _assert_event_follows_and_overlaps(second_event_voices, third_event_voices)
