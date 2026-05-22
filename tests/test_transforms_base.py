from collections.abc import Mapping

import pytest

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import (
    BooleanParam,
    EnumParam,
    FloatParam,
    IntegerParam,
    ParamSchema,
    PhraseTransformContext,
    PhraseTransformDefinition,
    ScoreTransformDefinition,
    StringParam,
    TransformParamFieldSpec,
    TransformParamsSpec,
)


def _scale_duration(tones: list[Tone], multiplier: float, *, preserve_frequency: bool = True) -> list[Tone]:
    scaled_tones = []
    for tone in tones:
        frequency = tone.frequency if preserve_frequency else tone.frequency * multiplier
        scaled_tones.append(Tone(frequency=frequency, duration=tone.duration * multiplier, sample_rate=tone.sample_rate, amplitude=tone.amplitude))
    return scaled_tones


def test_param_schema_base_validate_is_abstract():
    with pytest.raises(NotImplementedError):
        ParamSchema().validate("value", "field")


def test_transform_params_spec_defaults_to_no_fields():
    params_spec = TransformParamsSpec(params_factory=lambda p: p.values)
    assert params_spec.fields == {}


def test_transform_params_spec_parse_params_returns_parsed_values():
    factor_input = 2
    expected_factor = 2.0
    intensity_input = "HIGH"
    expected_intensity = "high"
    params_spec = TransformParamsSpec(
        params_factory=lambda p: p.values,
        fields={
            "factor": TransformParamFieldSpec(schema=FloatParam(), required=True),
            "intensity": TransformParamFieldSpec(schema=EnumParam(allowed_values=("low", "medium", "high")), required=True),
        },
    )
    parsed_params = params_spec.parse_params({"factor": factor_input, "intensity": intensity_input})
    assert parsed_params == {"factor": expected_factor, "intensity": expected_intensity}


def test_transform_params_spec_parse_params_applies_declared_defaults():
    default_factor = 1.5
    params_spec = TransformParamsSpec(params_factory=lambda p: p.values, fields={"factor": TransformParamFieldSpec(schema=FloatParam(), default=default_factor)})
    parsed_params = params_spec.parse_params({})
    assert parsed_params == {"factor": default_factor}


def test_transform_param_field_spec_preserves_schema():
    field_spec = TransformParamFieldSpec(schema=EnumParam(allowed_values=("start", "end")), required=True)
    assert isinstance(field_spec.schema, EnumParam)
    assert field_spec.required is True
    assert field_spec.schema.allowed_values == ("start", "end")


def test_transform_param_field_spec_accepts_union_schemas():
    field_spec = TransformParamFieldSpec(schema=(EnumParam(allowed_values=("low", "medium", "high")), FloatParam()), required=True)
    assert isinstance(field_spec.schema, tuple)
    assert len(field_spec.schema) == 2
    assert field_spec.required is True
    assert isinstance(field_spec.schema[0], EnumParam)
    assert field_spec.schema[0].allowed_values == ("low", "medium", "high")
    assert isinstance(field_spec.schema[1], FloatParam)


def test_transform_params_spec_parse_params_rejects_unknown_fields():
    params_spec = TransformParamsSpec(params_factory=lambda p: p.values, fields={"seconds": TransformParamFieldSpec(schema=FloatParam(), required=True)})
    with pytest.raises(ValueError):
        params_spec.parse_params({"seconds": 1.0, "extra": 2.0}, transform_name="delay")


def test_transform_params_spec_parse_params_rejects_missing_required_fields():
    params_spec = TransformParamsSpec(params_factory=lambda p: p.values, fields={"seconds": TransformParamFieldSpec(schema=FloatParam(), required=True)})
    with pytest.raises(ValueError):
        params_spec.parse_params({}, transform_name="delay")


def test_transform_params_spec_parse_params_accepts_enum_field_case_insensitively():
    params_spec = TransformParamsSpec(
        params_factory=lambda p: p.values,
        fields={"dimension": TransformParamFieldSpec(schema=EnumParam(allowed_values=("frequency", "duration", "amplitude")), required=True)},
    )
    params_spec.parse_params({"dimension": "DURATION"}, transform_name="erosion")


def test_transform_params_spec_parse_params_surfaces_single_schema_error():
    params_spec = TransformParamsSpec(params_factory=lambda p: p.values, fields={"label": TransformParamFieldSpec(schema=StringParam(), required=True)})
    with pytest.raises(ValueError):
        params_spec.parse_params({"label": 123}, transform_name="labeler")


def test_transform_params_spec_parse_params_combines_union_schema_errors():
    params_spec = TransformParamsSpec(
        params_factory=lambda p: p.values, fields={"strength": TransformParamFieldSpec(schema=(StringParam(), FloatParam()), required=True)}
    )
    with pytest.raises(ValueError):
        params_spec.parse_params({"strength": False}, transform_name="union_test")


def test_phrase_transform_context_exposes_current_phrase():
    score = Score([Voice([Phrase([Motif("first-voice", [Tone(440.0, duration=1.0)])])]), Voice([Phrase([Motif("second-voice", [Tone(660.0, duration=0.5)])])])])
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)
    assert context.phrase is score.voices[1].phrases[0]


def test_phrase_transform_definition_transform_parses_params_before_invoking_transform_function():
    factor_input = 2
    expected_factor = 2.0
    captured_params: list[dict[str, object]] = []
    score = Score([Voice([Phrase([Motif("subject", [Tone(440.0)])])])])
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    def transform_function(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
        captured_params.append(dict(params))
        return context.phrase

    phrase_definition = PhraseTransformDefinition(
        name="phrase_scale",
        params_spec=TransformParamsSpec(params_factory=lambda p: p.values, fields={"factor": TransformParamFieldSpec(schema=FloatParam(), required=True)}),
        transform_function=transform_function,
    )
    transformed_phrase = phrase_definition.transform(context, {"factor": factor_input})
    assert transformed_phrase is context.phrase
    assert captured_params == [{"factor": expected_factor}]


def test_score_transform_definition_transform_parses_params_before_invoking_transform_function():
    factor_input = 2
    expected_factor = 2.0
    captured_params: list[dict[str, object]] = []
    score = Score([Voice([Phrase([Motif("subject", [Tone(440.0)])])])])

    def transform_function(score: Score, params: Mapping[str, object]) -> Score:
        captured_params.append(dict(params))
        return score

    score_definition = ScoreTransformDefinition(
        name="score_scale",
        params_spec=TransformParamsSpec(params_factory=lambda p: p.values, fields={"factor": TransformParamFieldSpec(schema=FloatParam(), required=True)}),
        transform_function=transform_function,
    )
    transformed_score = score_definition.transform(score, {"factor": factor_input})
    assert transformed_score is score
    assert captured_params == [{"factor": expected_factor}]


def test_boolean_param_accepts_true():
    BooleanParam().validate(True, "test_field")


def test_string_param_rejects_non_string():
    with pytest.raises(ValueError):
        StringParam().validate(1.0, "test_field")


def test_float_param_rejects_boolean():
    with pytest.raises(ValueError):
        FloatParam().validate(True, "test_field")


def test_integer_param_rejects_float():
    with pytest.raises(ValueError):
        IntegerParam().validate(1.5, "test_field")


def test_enum_param_rejects_unknown_value():
    with pytest.raises(ValueError):
        EnumParam(allowed_values=("low", "medium", "high")).validate("extreme", "test_field")


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
