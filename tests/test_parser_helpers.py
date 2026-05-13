import pytest

from composition.parser import (
    _apply_phrase_transform_spec,
    parse_motifs,
    parse_transform_spec,
    parse_voice,
)
from composition.schema import VoiceConfig
from score_model.tone import Tone
from transforms.base import (
    PhraseRelativeTransform,
    ScoreTransform,
    TransformParamFieldSpec,
    TransformParamsSpec,
    TransformParamType,
)


def test_parse_motifs_rejects_non_string_motif_names():
    numeric_motif_name = 123
    motif_definition = {numeric_motif_name: ["440"]}

    with pytest.raises(ValueError):
        parse_motifs(motif_definition)


def test_parse_transform_spec_rejects_empty_string_name():
    with pytest.raises(ValueError):
        parse_transform_spec({"name": ""}, "Phrase")


def test_parse_voice_uses_first_phrase_as_reference_for_later_relative_phrase_transform():
    seed_frequency = 440.0
    seed_duration = 1.0
    parsed_motifs = {"seed": [Tone(seed_frequency, duration=seed_duration)]}
    voice_config: VoiceConfig = {
        "phrases": [
            {"motifs": ["seed"]},
            {
                "motifs": ["seed"],
                "transforms": [
                    {
                        "name": "phrase_golden_ratio_grow",
                        "params": {"dimension": "DURATION"},
                    }
                ],
            },
        ]
    }
    no_previous_voice_tones: list[Tone] = []

    voice, combined_tones = parse_voice(voice_config, parsed_motifs, no_previous_voice_tones)

    assert len(voice.tones) == 2
    assert len(combined_tones) == 2
    assert voice.tones[0].duration == pytest.approx(seed_duration)
    assert voice.tones[1].duration > seed_duration


def test_parse_voice_uses_previous_voice_as_reference_when_first_phrase_is_relative():
    seed_frequency = 440.0
    seed_duration = 1.0
    parsed_motifs = {"seed": [Tone(seed_frequency, duration=seed_duration)]}
    previous_voice_tones = [Tone(220.0, duration=2.0)]
    voice_config: VoiceConfig = {
        "phrases": [
            {
                "motifs": ["seed"],
                "transforms": [
                    {
                        "name": "phrase_feigenbaum_shrink",
                        "params": {"dimension": "DURATION"},
                    }
                ],
            }
        ]
    }

    voice, combined_tones = parse_voice(voice_config, parsed_motifs, previous_voice_tones)

    assert len(voice.tones) == 1
    assert len(combined_tones) == 1
    assert voice.tones[0].duration < seed_duration


def test_apply_phrase_transform_spec_rejects_non_phrase_scope_descriptor():
    non_phrase_descriptor = ScoreTransform(
        name="score_reverse",
        transform=lambda score: score,
        params_spec=TransformParamsSpec(),
    )
    phrase_tones = [Tone(440.0, duration=1.0)]

    with pytest.raises(ValueError):
        _apply_phrase_transform_spec(
            descriptor=non_phrase_descriptor,
            phrase_tones=phrase_tones,
            transform_params={},
            reference_tones=None,
        )


def test_apply_phrase_transform_spec_relative_scope_forwards_named_params():
    phrase_tones = [Tone(440.0, amplitude=0.5), Tone(660.0, amplitude=0.5)]
    reference_tones = [Tone(330.0, amplitude=0.6)]
    relative_descriptor = PhraseRelativeTransform(
        name="phrase_golden_ratio_shrink",
        transform=lambda tones, previous_tones, dimension="DURATION": [
            Tone(
                frequency=tone.frequency,
                duration=tone.duration,
                sample_rate=tone.sample_rate,
                amplitude=tone.amplitude / 2 if dimension == "AMPLITUDE" else tone.amplitude,
            )
            for tone in tones
        ],
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.STRING,
                ),
            }
        ),
    )
    transform_params = {"dimension": "AMPLITUDE"}

    result = _apply_phrase_transform_spec(
        descriptor=relative_descriptor,
        phrase_tones=phrase_tones,
        transform_params=transform_params,
        reference_tones=reference_tones,
    )

    assert len(result) == len(phrase_tones)
    assert result[0].amplitude == pytest.approx(0.25)
    assert result[1].amplitude == pytest.approx(0.25)
