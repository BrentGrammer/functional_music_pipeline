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


def _build_cluster_frost_composition() -> dict:
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
    score = parse_composition(_build_cluster_frost_composition())

    assert isinstance(score, Score)
    expected_total_voice_count = 35
    expected_source_event_voice_count = 3
    expected_first_event_voice_count = 5
    expected_second_event_voice_count = 7
    expected_third_event_voice_count = 9
    expected_fourth_event_voice_count = 11

    assert len(score.voices) == expected_total_voice_count
    assert len(score.voices[0].tones) == 1
    assert len(score.voices[1].tones) == 1
    assert len(score.voices[2].tones) == 1
    seed_frequency = score.voices[0].tones[0].frequency
    assert seed_frequency == pytest.approx(330.0)

    source_event_voices = score.voices[0:3]
    first_event_voices = score.voices[3:8]
    second_event_voices = score.voices[8:15]
    third_event_voices = score.voices[15:24]
    fourth_event_voices = score.voices[24:35]

    assert len(source_event_voices) == expected_source_event_voice_count
    assert len(first_event_voices) == expected_first_event_voice_count
    assert len(second_event_voices) == expected_second_event_voice_count
    assert len(third_event_voices) == expected_third_event_voice_count
    assert len(fourth_event_voices) == expected_fourth_event_voice_count

    source_event_frequencies = {voice.tones[0].frequency for voice in source_event_voices}
    first_event_frequencies = {voice.tones[1].frequency for voice in first_event_voices}
    second_event_frequencies = {voice.tones[1].frequency for voice in second_event_voices}
    third_event_frequencies = {voice.tones[1].frequency for voice in third_event_voices}
    fourth_event_frequencies = {voice.tones[1].frequency for voice in fourth_event_voices}

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

    _assert_controlled_edge_stagger(first_event_voices)
    _assert_event_follows_and_overlaps(first_event_voices, second_event_voices)
    _assert_event_follows_and_overlaps(second_event_voices, third_event_voices)
    _assert_event_follows_and_overlaps(third_event_voices, fourth_event_voices)
