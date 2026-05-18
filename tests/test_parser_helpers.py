import pytest

from composition.parser import (
    _apply_phrase_transform_spec,
    parse_motifs,
    parse_transform_spec,
    parse_voice,
)
from composition.schema import VoiceConfig
from typing import cast
from score_model.tone import Tone
from score_model.traversal import iter_voice_tones
from transforms.base import (
    PhraseScope,
    ScoreScope,
    TransformDefinition,
    TransformParamsSpec,
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

    assert len(iter_voice_tones(voice)) == 2
    assert len(combined_tones) == 2
    assert voice.phrases[0].motifs[0].tones[0].duration == pytest.approx(seed_duration)
    assert voice.phrases[1].motifs[0].tones[0].duration > seed_duration


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

    assert len(iter_voice_tones(voice)) == 1
    assert len(combined_tones) == 1
    assert voice.phrases[0].motifs[0].tones[0].duration < seed_duration


def test_apply_phrase_transform_spec_rejects_non_phrase_scope_descriptor():
    non_phrase_descriptor = TransformDefinition(
        name="reverse",
        transform_func=lambda score: score,
        scope=ScoreScope.SCORE_AWARE,
        params_spec=TransformParamsSpec(),
    )
    phrase_tones = [Tone(440.0, duration=1.0)]

    with pytest.raises(ValueError):
        _apply_phrase_transform_spec(
            descriptor=cast(TransformDefinition[PhraseScope], non_phrase_descriptor),
            phrase_tones=phrase_tones,
            transform_params={},
            reference_tones=None,
        )
