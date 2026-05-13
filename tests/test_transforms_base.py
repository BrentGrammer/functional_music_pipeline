import pytest

from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import (
    ToneDimension,
    TransformDescriptor,
    TransformParamFieldSpec,
    TransformParamsSpec,
    TransformParamType,
    TransformScope,
    apply_to_all_voices,
    apply_to_voice,
    parse_dimension,
)


def _build_score_with_two_voices() -> Score:
    first_voice = Voice([Tone(440.0, duration=1.0)])
    second_voice = Voice([Tone(660.0, duration=0.5)])
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


def test_transform_param_field_spec_preserves_parameter_type_and_allowed_enum_values():
    field_spec = TransformParamFieldSpec(
        param_type=TransformParamType.ENUM,
        required=True,
        allowed_enum_values=("start", "end"),
    )

    assert field_spec.param_type is TransformParamType.ENUM
    assert field_spec.required is True
    assert field_spec.allowed_enum_values == ("start", "end")


def test_transform_param_field_spec_accepts_union_parameter_types():
    field_spec = TransformParamFieldSpec(
        param_type=(TransformParamType.ENUM, TransformParamType.FLOAT),
        required=True,
        allowed_enum_values=("low", "medium", "high"),
    )

    assert field_spec.param_type == (TransformParamType.ENUM, TransformParamType.FLOAT)
    assert field_spec.required is True
    assert field_spec.allowed_enum_values == ("low", "medium", "high")


def test_transform_descriptor_defaults_to_empty_params_spec():
    descriptor = TransformDescriptor(
        name="reverse",
        scope=TransformScope.PHRASE,
        transform=lambda tones: list(reversed(tones)),
    )

    assert descriptor.params_spec == TransformParamsSpec()


def test_transform_descriptor_preserves_explicit_params_spec():
    expected_params_spec = TransformParamsSpec(
        fields={
            "seconds": TransformParamFieldSpec(
                param_type=TransformParamType.FLOAT,
                required=True,
            )
        }
    )
    descriptor = TransformDescriptor(
        name="delay",
        scope=TransformScope.PHRASE,
        transform=lambda tones, **_: tones,
        params_spec=expected_params_spec,
    )

    assert descriptor.params_spec is expected_params_spec


def test_transform_params_spec_identifies_required_fields_from_metadata():
    params_spec = TransformParamsSpec(
        fields={
            "seconds": TransformParamFieldSpec(
                param_type=TransformParamType.FLOAT,
                required=True,
            ),
            "position": TransformParamFieldSpec(
                param_type=TransformParamType.STRING,
                required=False,
            ),
        }
    )

    required_fields = tuple(f for f, s in params_spec.fields.items() if s.required)
    assert required_fields == ("seconds",)


def test_apply_to_voice_updates_only_target_voice_and_preserves_others():
    target_voice_index = 1
    duration_multiplier = 2.0
    score = _build_score_with_two_voices()
    original_first_voice_tones = score.voices[0].tones

    pipeline_step = apply_to_voice(target_voice_index, _scale_duration, duration_multiplier)
    result = pipeline_step(score)

    assert result is score
    assert score.voices[0].tones is original_first_voice_tones
    assert score.voices[1].tones[0].duration == pytest.approx(1.0)


def test_apply_to_voice_ignores_negative_index():
    negative_voice_index = -1
    score = _build_score_with_two_voices()
    original_first_duration = score.voices[0].tones[0].duration
    original_second_duration = score.voices[1].tones[0].duration

    pipeline_step = apply_to_voice(negative_voice_index, _scale_duration, 3.0)
    result = pipeline_step(score)

    assert result is score
    assert score.voices[0].tones[0].duration == pytest.approx(original_first_duration)
    assert score.voices[1].tones[0].duration == pytest.approx(original_second_duration)


def test_apply_to_voice_ignores_out_of_range_index():
    out_of_range_voice_index = 5
    score = _build_score_with_two_voices()
    original_first_duration = score.voices[0].tones[0].duration
    original_second_duration = score.voices[1].tones[0].duration

    pipeline_step = apply_to_voice(out_of_range_voice_index, _scale_duration, 3.0)
    result = pipeline_step(score)

    assert result is score
    assert score.voices[0].tones[0].duration == pytest.approx(original_first_duration)
    assert score.voices[1].tones[0].duration == pytest.approx(original_second_duration)


def test_apply_to_voice_forwards_keyword_arguments():
    target_voice_index = 0
    duration_multiplier = 2.0
    score = _build_score_with_two_voices()

    pipeline_step = apply_to_voice(
        target_voice_index,
        _scale_duration,
        duration_multiplier,
        preserve_frequency=False,
    )
    result = pipeline_step(score)

    assert result.voices[0].tones[0].frequency == pytest.approx(880.0)
    assert result.voices[0].tones[0].duration == pytest.approx(2.0)


def test_apply_to_all_voices_updates_every_voice():
    duration_multiplier = 2.0
    score = _build_score_with_two_voices()

    pipeline_step = apply_to_all_voices(_scale_duration, duration_multiplier)
    result = pipeline_step(score)

    assert result is score
    assert result.voices[0].tones[0].duration == pytest.approx(2.0)
    assert result.voices[1].tones[0].duration == pytest.approx(1.0)


def test_apply_to_all_voices_forwards_keyword_arguments():
    duration_multiplier = 0.5
    score = _build_score_with_two_voices()

    pipeline_step = apply_to_all_voices(
        _scale_duration,
        duration_multiplier,
        preserve_frequency=False,
    )
    result = pipeline_step(score)

    assert result.voices[0].tones[0].frequency == pytest.approx(220.0)
    assert result.voices[1].tones[0].frequency == pytest.approx(330.0)


def test_apply_to_all_voices_handles_empty_score():
    empty_score = Score()

    pipeline_step = apply_to_all_voices(_scale_duration, 2.0)
    result = pipeline_step(empty_score)

    assert result is empty_score
    assert len(result.voices) == 0
