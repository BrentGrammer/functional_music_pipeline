import pytest

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.traversal import flatten_phrase_tones
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import PhraseTransformContext
from transforms.geological.fragment import FRAGMENT_PARAMS_SPEC, FragmentParams, fragment_phrase_transform
from transforms.registry import PHRASE_TRANSFORMS


def test_fragment_is_registered_as_phrase_transform():
    assert "fragment" in PHRASE_TRANSFORMS


def test_fragment_params_accept_omitted_pattern_key():
    params = FRAGMENT_PARAMS_SPEC.parse_params(
        {"damage_pct": 0, "damage_tones_span": 4},
        transform_name="fragment",
    )

    assert params == FragmentParams(damage_pct=0, damage_tones_span=4, damage_pattern_key=None)


def test_fragment_params_accept_string_pattern_key():
    damage_pattern_key = "pattern-key-a"

    params = FRAGMENT_PARAMS_SPEC.parse_params(
        {"damage_pct": 0, "damage_tones_span": 4, "damage_pattern_key": damage_pattern_key},
        transform_name="fragment",
    )

    assert params == FragmentParams(damage_pct=0, damage_tones_span=4, damage_pattern_key=damage_pattern_key)


@pytest.mark.parametrize("invalid_pattern_key", [123, 4.5, True, None, ["string-in-list"]])
def test_fragment_params_reject_invalid_pattern_key_values(invalid_pattern_key: object):
    with pytest.raises(ValueError):
        FRAGMENT_PARAMS_SPEC.parse_params(
            {"damage_pct": 0, "damage_tones_span": 4, "damage_pattern_key": invalid_pattern_key},
            transform_name="fragment",
        )


def test_fragment_damage_pct_zero_returns_equivalent_phrase():
    original_tones = [
        Tone(220.0, duration=0.5, amplitude=0.25),
        Tone(330.0, duration=0.25, amplitude=0.5),
    ]
    phrase = Phrase(motifs=[Motif(name="fragment-target", tones=original_tones)])
    score = Score(voices=[Voice(phrases=[phrase])])
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    result = fragment_phrase_transform(
        context,
        FragmentParams(damage_pct=0, damage_tones_span=4, damage_pattern_key=None),
    )

    result_tones = flatten_phrase_tones(result)
    assert result.motifs[0].name == "<transformed>"
    assert [tone.frequency for tone in result_tones] == pytest.approx([original_tones[0].frequency, original_tones[1].frequency])
    assert [tone.duration for tone in result_tones] == pytest.approx([original_tones[0].duration, original_tones[1].duration])
    assert [tone.amplitude for tone in result_tones] == pytest.approx([original_tones[0].amplitude, original_tones[1].amplitude])
