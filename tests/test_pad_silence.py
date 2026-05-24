import pytest

from composition.parser import generate_score_plan
from composition.schema import MotifsConfigInput, PhraseConfigInput
from composition.transformer import transform_score
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from transforms.base import PhraseTransformContext
from transforms.basic.pad_silence import PAD_SILENCE_PARAMS_SPEC, PadSilenceParams, pad_silence_phrase_transform, pad_silence_score_transform, pad_silence_tones
from transforms.registry import PHRASE_TRANSFORMS, SCORE_TRANSFORMS


def render_phrase_from_config(
    phrase_config: object,
    parsed_motifs: dict[str, list[Tone]],
) -> list[Tone]:
    motifs_section: MotifsConfigInput = {
        name: [f"{tone.frequency}:{tone.duration}" for tone in tones]
        for name, tones in parsed_motifs.items()
    }
    composition_document: object = {
        "name": "Pad Silence Phrase Example",
        "score": {
            "motifs": motifs_section,
            "voices": [{"phrases": [phrase_config]}],
        },
    }
    score = transform_score(generate_score_plan(composition_document))
    return flatten_voice_tones(score.voices[0])


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



def test_parse_phrase_applies_pad_silence():
    subject_frequency = 440.0
    subject_duration = 0.5
    silence_seconds = 0.3
    parsed_motifs = {"subject": [Tone(subject_frequency, duration=subject_duration)]}
    phrase_config: PhraseConfigInput = {
        "motifs": ["subject"],
        "transforms": [{"name": "pad_silence", "params": {"seconds": silence_seconds, "position": "end"}}],
    }

    result = render_phrase_from_config(phrase_config, parsed_motifs)

    assert len(result) == 2
    assert result[0].frequency == pytest.approx(subject_frequency)
    assert result[1].frequency == 0
    assert result[1].duration == pytest.approx(silence_seconds)


def test_parse_score_applies_pad_silence_at_start():
    subject_frequency = 440.0
    subject_duration = 0.5
    silence_seconds = 0.3
    composition_document = {
        "name": "Pad Silence Score Start",
        "score": {
            "motifs": {
                "subject": [f"{subject_frequency}:{subject_duration}"],
            },
            "voices": [{"phrases": [{"motifs": ["subject"]}]}],
            "score_transforms": [{"name": "pad_silence", "params": {"seconds": silence_seconds, "position": "start"}}],
        },
    }

    score = transform_score(generate_score_plan(composition_document))

    assert [tone.frequency for tone in flatten_voice_tones(score.voices[0])] == pytest.approx([0, subject_frequency])
    assert [tone.duration for tone in flatten_voice_tones(score.voices[0])] == pytest.approx([silence_seconds, subject_duration])


def test_parse_score_applies_pad_silence_at_end():
    subject_frequency = 440.0
    subject_duration = 0.5
    silence_seconds = 0.3
    composition_document = {
        "name": "Pad Silence Score End",
        "score": {
            "motifs": {
                "subject": [f"{subject_frequency}:{subject_duration}"],
            },
            "voices": [{"phrases": [{"motifs": ["subject"]}]}],
            "score_transforms": [{"name": "pad_silence", "params": {"seconds": silence_seconds, "position": "end"}}],
        },
    }

    score = transform_score(generate_score_plan(composition_document))

    assert [tone.frequency for tone in flatten_voice_tones(score.voices[0])] == pytest.approx([subject_frequency, 0])
    assert [tone.duration for tone in flatten_voice_tones(score.voices[0])] == pytest.approx([subject_duration, silence_seconds])


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
        render_phrase_from_config(phrase_config, parsed_motifs)


def test_parse_phrase_pad_silence_requires_missing_required_fields():
    subject_frequency = 440.0
    subject_duration = 0.5
    parsed_motifs = {"subject": [Tone(subject_frequency, duration=subject_duration)]}
    descriptor = PHRASE_TRANSFORMS["pad_silence"]
    valid_params = {"seconds": 0.3, "position": "end"}

    for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
        incomplete_params = valid_params.copy()
        incomplete_params.pop(required_field)
        phrase_config: PhraseConfigInput = {
            "motifs": ["subject"],
            "transforms": [{"name": "pad_silence", "params": incomplete_params}],
        }

        with pytest.raises(ValueError, match="must include"):
            render_phrase_from_config(phrase_config, parsed_motifs)


def test_parse_score_pad_silence_requires_missing_required_fields():
    subject_frequency = 440.0
    subject_duration = 0.5
    descriptor = SCORE_TRANSFORMS["pad_silence"]
    valid_params = {"seconds": 0.3, "position": "end"}

    for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
        incomplete_params = valid_params.copy()
        incomplete_params.pop(required_field)
        composition_document = {
            "name": "Pad Silence Missing Required Fields",
            "score": {
                "motifs": {
                    "subject": [f"{subject_frequency}:{subject_duration}"],
                },
                "voices": [{"phrases": [{"motifs": ["subject"]}]}],
                "score_transforms": [{"name": "pad_silence", "params": incomplete_params}],
            },
        }

        with pytest.raises(ValueError, match="must include"):
            transform_score(generate_score_plan(composition_document))


def test_applies_pad_silence_between_phrases():
    subject_frequency = 261.63
    answer_frequency = 329.63
    phrase_duration = 0.5
    silence_seconds = 0.25
    composition_document = {
        "name": "Pad Silence Between Phrases",
        "score": {
            "motifs": {
                "subject": [f"{subject_frequency}:{phrase_duration}"],
                "answer": [f"{answer_frequency}:{phrase_duration}"],
            },
            "voices": [
                {
                    "phrases": [
                        {
                            "motifs": ["subject"],
                            "transforms": [{"name": "pad_silence", "params": {"seconds": silence_seconds, "position": "end"}}],
                        },
                        {"motifs": ["answer"]},
                    ]
                }
            ]
        },
    }

    score = transform_score(generate_score_plan(composition_document))

    assert len(score.voices) == 1
    assert [tone.frequency for tone in flatten_voice_tones(score.voices[0])] == pytest.approx([subject_frequency, 0, answer_frequency])
    assert [tone.duration for tone in flatten_voice_tones(score.voices[0])] == pytest.approx([phrase_duration, silence_seconds, phrase_duration])


def test_pad_silence_params_rejects_non_numeric_seconds():
    with pytest.raises(ValueError):
        PAD_SILENCE_PARAMS_SPEC.parse_params({"seconds": True, "position": "end"}, transform_name="pad_silence")


def test_pad_silence_params_rejects_non_string_position():
    with pytest.raises(ValueError):
        PAD_SILENCE_PARAMS_SPEC.parse_params({"seconds": 0.2, "position": None}, transform_name="pad_silence")


def test_pad_silence_phrase_transform_accepts_typed_params():
    silence_seconds = 0.3
    score = Score(voices=[Voice(phrases=[Phrase(motifs=[Motif(name="m", tones=[Tone(440.0, duration=0.5)])])])])
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)
    params = PadSilenceParams(seconds=silence_seconds, position="end")

    result = pad_silence_phrase_transform(context, params)

    assert len(result.motifs[0].tones) == 2
    assert result.motifs[0].tones[1].frequency == 0
    assert result.motifs[0].tones[1].duration == pytest.approx(silence_seconds)


def test_pad_silence_score_transform_accepts_typed_params():
    silence_seconds = 0.3
    score = Score(voices=[Voice(phrases=[Phrase(motifs=[Motif(name="m", tones=[Tone(440.0, duration=0.5)])])])])
    params = PadSilenceParams(seconds=silence_seconds, position="start")

    result = pad_silence_score_transform(score, params)

    assert len(result.voices[0].phrases[0].motifs[0].tones) == 2
    assert result.voices[0].phrases[0].motifs[0].tones[0].frequency == 0
    assert result.voices[0].phrases[0].motifs[0].tones[0].duration == pytest.approx(silence_seconds)
