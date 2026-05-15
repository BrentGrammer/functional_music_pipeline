import pytest

from composition.parser import TRANSFORMS, parse_composition, parse_phrase
from composition.schema import PhraseConfig
from score_model.tone import Tone
from transforms.base import PhraseTransform
from transforms.basic.pad_silence import pad_silence_tones


def test_pad_silence_start_prepends_silence():
    first_frequency = 440.0
    first_duration = 0.5
    second_frequency = 660.0
    second_duration = 0.25
    silence_seconds = 0.2
    tones = [Tone(first_frequency, duration=first_duration), Tone(second_frequency, duration=second_duration)]

    result = pad_silence_tones(tones, seconds=silence_seconds, position="start")

    assert len(result) == 3
    assert result[0].frequency == 0
    assert result[0].amplitude == 0
    assert result[0].duration == pytest.approx(silence_seconds)
    assert result[1].frequency == pytest.approx(first_frequency)
    assert result[2].frequency == pytest.approx(second_frequency)


def test_pad_silence_end_appends_silence():
    first_frequency = 440.0
    first_duration = 0.5
    second_frequency = 660.0
    second_duration = 0.25
    silence_seconds = 0.2
    tones = [Tone(first_frequency, duration=first_duration), Tone(second_frequency, duration=second_duration)]

    result = pad_silence_tones(tones, seconds=silence_seconds, position="end")

    assert len(result) == 3
    assert result[0].frequency == pytest.approx(first_frequency)
    assert result[1].frequency == pytest.approx(second_frequency)
    assert result[2].frequency == 0
    assert result[2].amplitude == 0
    assert result[2].duration == pytest.approx(silence_seconds)


def test_pad_silence_zero_seconds_returns_copy():
    frequency = 440.0
    duration = 0.5
    silence_seconds = 0
    tones = [Tone(frequency, duration=duration)]

    result = pad_silence_tones(tones, seconds=silence_seconds, position="end")

    assert len(result) == 1
    assert result is not tones
    assert result[0].frequency == pytest.approx(frequency)


def test_pad_silence_rejects_negative_seconds():
    frequency = 440.0
    negative_seconds = -0.1

    with pytest.raises(ValueError, match="non-negative"):
        pad_silence_tones([Tone(frequency)], seconds=negative_seconds, position="start")


def test_pad_silence_rejects_invalid_position():
    frequency = 440.0
    silence_seconds = 0.1
    invalid_position = "middle"

    with pytest.raises(ValueError, match="position"):
        pad_silence_tones([Tone(frequency)], seconds=silence_seconds, position=invalid_position)


def test_pad_silence_registered():
    assert "pad_silence" in TRANSFORMS
    descriptor = TRANSFORMS["pad_silence"]
    assert isinstance(descriptor, PhraseTransform)
    assert TRANSFORMS["pad_silence"].transform is pad_silence_tones


def test_parse_phrase_applies_pad_silence():
    subject_frequency = 440.0
    subject_duration = 0.5
    silence_seconds = 0.3
    parsed_motifs = {"subject": [Tone(subject_frequency, duration=subject_duration)]}
    phrase_config: PhraseConfig = {
        "motifs": ["subject"],
        "transforms": [{"name": "pad_silence", "params": {"seconds": silence_seconds, "position": "end"}}],
    }

    result = parse_phrase(phrase_config, parsed_motifs)

    assert len(result) == 2
    assert result[0].frequency == pytest.approx(subject_frequency)
    assert result[1].frequency == 0
    assert result[1].duration == pytest.approx(silence_seconds)


def test_parse_phrase_pad_silence_requires_dict_params():
    subject_frequency = 440.0
    subject_duration = 0.5
    invalid_params = 0.3
    parsed_motifs = {"subject": [Tone(subject_frequency, duration=subject_duration)]}
    phrase_config = {
        "motifs": ["subject"],
        "transforms": [{"name": "pad_silence", "params": invalid_params}],
    }

    with pytest.raises(ValueError):
        parse_phrase(phrase_config, parsed_motifs)


def test_parse_phrase_pad_silence_requires_missing_required_fields():
    subject_frequency = 440.0
    subject_duration = 0.5
    parsed_motifs = {"subject": [Tone(subject_frequency, duration=subject_duration)]}
    descriptor = TRANSFORMS["pad_silence"]
    valid_params = {"seconds": 0.3, "position": "end"}

    for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
        incomplete_params = valid_params.copy()
        incomplete_params.pop(required_field)
        phrase_config: PhraseConfig = {
            "motifs": ["subject"],
            "transforms": [{"name": "pad_silence", "params": incomplete_params}],
        }

        with pytest.raises(ValueError, match="must include"):
            parse_phrase(phrase_config, parsed_motifs)


def test_parse_composition_applies_pad_silence_between_phrases():
    subject_frequency = 261.63
    answer_frequency = 329.63
    phrase_duration = 0.5
    silence_seconds = 0.25
    composition_document = {
        "motifs": {
            "subject": [f"{subject_frequency}:{phrase_duration}"],
            "answer": [f"{answer_frequency}:{phrase_duration}"],
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {
                            "motifs": ["subject"],
                            "transforms": [
                                {"name": "pad_silence", "params": {"seconds": silence_seconds, "position": "end"}}
                            ],
                        },
                        {"motifs": ["answer"]},
                    ]
                }
            ]
        },
    }

    score = parse_composition(composition_document)

    assert len(score.voices) == 1
    assert [tone.frequency for tone in score.voices[0].tones] == pytest.approx([subject_frequency, 0, answer_frequency])
    assert [tone.duration for tone in score.voices[0].tones] == pytest.approx(
        [phrase_duration, silence_seconds, phrase_duration]
    )
