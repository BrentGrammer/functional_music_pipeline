import pytest

from composition.parser import apply_to_each_voice
from score_model.motif import Motif
from score_model.score import Score
from score_model.phrase import Phrase
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from composition.score_plan import TransformRequest
from transforms.base import (
    BooleanParam,
    EnumParam,
    FloatParam,
    PhraseTransformContext,
    PhraseTransformDefinition,
    PreparedTransform,
    ScoreScope,
    ScoreTransformDefinition,
    ToneDimension,
    TransformDefinition,
    TransformParamFieldSpec,
    TransformParamsSpec,
    validate_transform_params,
    parse_dimension,
)


def _build_score_with_two_voices() -> Score:
    first_voice = Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])
    second_voice = Voice([Phrase([Motif("<test>", [Tone(660.0, duration=0.5)])])])
    return Score([first_voice, second_voice])


def _scale_duration(
    tones: list[Tone],
    multiplier: float,
    *,
    preserve_frequency: bool = True,
) -> list[Tone]:
    scaled_tones = []
    for tone in tones:
        frequency = tone.frequency if preserve_frequency else tone.frequency * multiplier
        scaled_tones.append(
            Tone(
                frequency=frequency,
                duration=tone.duration * multiplier,
                sample_rate=tone.sample_rate,
                amplitude=tone.amplitude,
            )
        )
    return scaled_tones


def test_parse_dimension_returns_same_enum_instance():
    assert parse_dimension(ToneDimension.FREQUENCY) is ToneDimension.FREQUENCY


def test_parse_dimension_accepts_case_insensitive_string():
    assert parse_dimension("duration") is ToneDimension.DURATION


def test_parse_dimension_rejects_unknown_dimension_with_valid_options_in_message():
    invalid_dimension = "tempo"

    with pytest.raises(ValueError, match="Invalid dimension"):
        parse_dimension(invalid_dimension)


def test_transform_params_spec_defaults_to_no_fields():
    params_spec = TransformParamsSpec()

    assert params_spec.fields == {}
    assert params_spec.validator is None


def test_transform_param_field_spec_preserves_schema():
    field_spec = TransformParamFieldSpec(
        schema=EnumParam(allowed_values=("start", "end")),
        required=True,
    )

    assert isinstance(field_spec.schema, EnumParam)
    assert field_spec.required is True
    assert field_spec.schema.allowed_values == ("start", "end")


def test_transform_param_field_spec_accepts_union_schemas():
    field_spec = TransformParamFieldSpec(
        schema=(EnumParam(allowed_values=("low", "medium", "high")), FloatParam()),
        required=True,
    )

    assert isinstance(field_spec.schema, tuple)
    assert len(field_spec.schema) == 2
    assert field_spec.required is True
    assert isinstance(field_spec.schema[0], EnumParam)
    assert field_spec.schema[0].allowed_values == ("low", "medium", "high")
    assert isinstance(field_spec.schema[1], FloatParam)


def test_transform_definition_preserves_explicit_params_spec():
    expected_params_spec = TransformParamsSpec(
        fields={
            "seconds": TransformParamFieldSpec(
                schema=FloatParam(),
                required=True,
            )
        }
    )
    definition = TransformDefinition(
        name="delay",
        transform_func=lambda tones, **_: tones,
        scope=ScoreScope.EACH_VOICE,
        params_spec=expected_params_spec,
    )

    assert definition.params_spec == expected_params_spec
    assert definition.scope is ScoreScope.EACH_VOICE


def test_validate_transform_params_rejects_unknown_fields():
    params_spec = TransformParamsSpec(
        fields={
            "seconds": TransformParamFieldSpec(
                schema=FloatParam(),
                required=True,
            )
        }
    )

    with pytest.raises(ValueError, match="unknown fields"):
        validate_transform_params(params_spec, "delay", {"seconds": 1.0, "extra": 2.0})


def test_phrase_transform_context_exposes_current_phrase():
    score = _build_score_with_two_voices()
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)

    assert context.phrase is score.voices[1].phrases[0]


def test_phrase_transform_definition_validate_params_delegates_to_shared_validator():
    params_spec = TransformParamsSpec(
        fields={
            "seconds": TransformParamFieldSpec(
                schema=FloatParam(),
                required=True,
            )
        }
    )

    phrase_definition = PhraseTransformDefinition(
        name="phrase_delay",
        params_spec=params_spec,
        transform=lambda context, params: context.phrase,
    )
    assert phrase_definition.validate_params({"seconds": 1.5}) is None


def test_score_transform_definition_validate_params_delegates_to_shared_validator():
    params_spec = TransformParamsSpec(
        fields={
            "seconds": TransformParamFieldSpec(
                schema=FloatParam(),
                required=True,
            )
        }
    )

    score_definition = ScoreTransformDefinition(
        name="score_delay",
        params_spec=params_spec,
        transform=lambda score, params: score,
    )

    assert score_definition.validate_params({"seconds": 1.5}) is None


def test_prepared_transform_stores_apply_callable():
    request = TransformRequest(name="delay", params={"seconds": 1.0})
    score = Score()
    definition = ScoreTransformDefinition(
        name="delay",
        params_spec=TransformParamsSpec(),
        transform=lambda score, params: score,
    )
    prepared = PreparedTransform(
        transform_request=request,
        transform_definition=definition,
        apply=lambda score: score,
    )

    assert prepared.transform_request is request
    assert prepared.transform_definition is definition
    assert prepared.apply(score) is score

def test_apply_to_each_voice_updates_every_voice():
    duration_multiplier = 2.0
    score = _build_score_with_two_voices()

    pipeline_step = apply_to_each_voice(_scale_duration, duration_multiplier)
    result = pipeline_step(score)

    assert result is score
    assert flatten_voice_tones(result.voices[0])[0].duration == pytest.approx(2.0)
    assert flatten_voice_tones(result.voices[1])[0].duration == pytest.approx(1.0)


def test_apply_to_each_voice_forwards_keyword_arguments():
    # TODO: the values used here are too opaque. 220 and 330 should be variables, score with two voices is unclear because relavant values are hidden from the reader in this test.
    duration_multiplier = 0.5
    score = _build_score_with_two_voices()

    pipeline_step = apply_to_each_voice(
        _scale_duration,
        duration_multiplier,
        preserve_frequency=False,
    )
    result = pipeline_step(score)

    assert flatten_voice_tones(result.voices[0])[0].frequency == pytest.approx(220.0)
    assert flatten_voice_tones(result.voices[1])[0].frequency == pytest.approx(330.0)


def test_apply_to_each_voice_handles_empty_score():
    empty_score = Score()

    pipeline_step = apply_to_each_voice(_scale_duration, 2.0)
    result = pipeline_step(empty_score)

    assert result is empty_score
    assert len(result.voices) == 0


def test_boolean_param_accepts_true():
    BooleanParam().validate(True, "test_field")


def test_boolean_param_accepts_false():
    BooleanParam().validate(False, "test_field")


def test_boolean_param_rejects_integer():
    with pytest.raises(ValueError):
        BooleanParam().validate(1, "test_field")


def test_boolean_param_rejects_zero():
    with pytest.raises(ValueError):
        BooleanParam().validate(0, "test_field")


def test_boolean_param_rejects_string():
    with pytest.raises(ValueError):
        BooleanParam().validate("true", "test_field")


def test_boolean_param_rejects_none():
    with pytest.raises(ValueError):
        BooleanParam().validate(None, "test_field")
