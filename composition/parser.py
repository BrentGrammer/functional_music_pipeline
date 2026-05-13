from collections.abc import Callable
from typing import cast

from composition.profile_factory import build_profile
from composition.schema import (
    CompositionDocument,
    PhraseConfig,
    ProfileConfig,
    TransformSpec,
    VoiceConfig,
)
from composition.transform_params_validation import (
    validate_add_pedal_point_params,
    validate_geological_params,
)
from score_model.score import Score
from score_model.tone import Tone
from score_model.tone_utils import copy_tones
from score_model.voice import Voice
from transforms.base import (
    AllVoicesTransform,
    PhraseRelativeTransform,
    PhraseTransform,
    ScoreTargetMotifsTransform,
    ScoreTransform,
    ToneDimension,
    ToneSequence,
    TransformDescriptor,
    TransformParamFieldSpec,
    TransformParamsSpec,
    TransformParamType,
    apply_to_all_voices,
)
from transforms.delay import delay_tones
from transforms.drift import drift_transform
from transforms.duration import (
    INTENSITY_LEVELS,
    accelerando_transform,
    feigenbaum_sequence,
    phrase_feigenbaum_grow,
    phrase_feigenbaum_shrink,
    ritardando_transform,
    score_feigenbaum_sequence,
)
from transforms.erosion import erosion_transform
from transforms.frost import frost_effect
from transforms.fugue import NAMED_STRETTO_SPACINGS, add_pedal_point, stretto
from transforms.geological import (
    apply_geological_transform,
)
from transforms.golden_ratio import (
    golden_ratio_transform,
    phrase_golden_ratio_grow,
    phrase_golden_ratio_shrink,
)
from transforms.inversion import invert_tones
from transforms.pad_silence import pad_silence_tones
from transforms.repeat import repeat_tones
from transforms.reversal import reverse_tones
from transforms.scale import scale_transform
from transforms.transpose import transpose_tones


def resolve_profile_in_params(
    transform_params: dict[str, object],
) -> dict[str, object]:
    """
    If transform_params contains a 'profile' key with a dict value,
    it resolves it into a StochasticProfile instance using the factory.
    Otherwise, it returns the params unchanged.
    """
    if "profile" not in transform_params:
        return transform_params

    profile_config = transform_params.get("profile")
    if not isinstance(profile_config, dict):
        # Allow pre-resolved profiles to pass through without modification.
        return transform_params

    # but build_profile will validate its structure at runtime.
    resolved_profile = build_profile(cast(ProfileConfig, profile_config))

    # Return a new dictionary with the 'profile' value replaced by the instance.
    new_params = transform_params.copy()
    new_params["profile"] = resolved_profile
    return new_params


def _parse_tone_string(tone_string: str) -> Tone:
    normalized_tone_string = str(tone_string)

    if ":" in normalized_tone_string:
        frequency_value, duration_value = normalized_tone_string.split(":", 1)
        return Tone(float(frequency_value), duration=float(duration_value))

    return Tone(float(normalized_tone_string))

def _apply_phrase_transform(
    transform_func: Callable[..., ToneSequence],
    tones: ToneSequence,
    transform_params: dict[str, object],
) -> ToneSequence:
    resolved_transform_params = resolve_profile_in_params(transform_params)
    return cast(ToneSequence, transform_func(tones, **resolved_transform_params))



def _apply_score_transform(
    score: Score,
    descriptor: TransformDescriptor,
    transform_params: dict[str, object],
) -> Score:
    _validate_transform_params(descriptor, transform_params)
    resolved_transform_params = resolve_profile_in_params(transform_params)
    return cast(Score, descriptor.transform(score, **resolved_transform_params))


def _apply_all_voices_transform_with_optional_params(
    transform_func: Callable[..., ToneSequence],
    score: Score,
    transform_params: dict[str, object],
) -> Score:
    resolved_transform_params = resolve_profile_in_params(transform_params)
    return apply_to_all_voices(transform_func, **resolved_transform_params)(score)


def _require_list(value: object, error_message: str) -> list:
    if not isinstance(value, list):
        raise ValueError(error_message)

    return value


def _require_non_empty_string_list(value: object, error_message: str) -> list[str]:
    string_values = _require_list(value, error_message)
    if not string_values:
        raise ValueError(error_message)

    for string_value in string_values:
        if not isinstance(string_value, str) or not string_value:
            raise ValueError("Phrase 'motifs' entries must be non-empty strings.")

    return string_values


def _parse_motif_definition(motif_name: object, tone_strings: object) -> tuple[str, list[Tone]]:
    if not isinstance(motif_name, str):
        raise ValueError("Motif names must be strings.")
    if not isinstance(tone_strings, list):
        raise ValueError(f"Motif '{motif_name}' must map to a list of tone strings.")

    return motif_name, [_parse_tone_string(tone_string) for tone_string in tone_strings]


def _validate_transform_params(
    descriptor: TransformDescriptor,
    transform_params: dict[str, object],
) -> None:
    field_specs = descriptor.params_spec.fields
    required_fields = tuple(field_name for field_name, field_spec in field_specs.items() if field_spec.required)

    unknown_fields = tuple(field_name for field_name in transform_params if field_name not in field_specs)
    if unknown_fields:
        unknown_fields_description = ", ".join(f"'{field}'" for field in unknown_fields)
        raise ValueError(
            f"The '{descriptor.name}' transform params include unknown fields: {unknown_fields_description}."
        )

    missing_fields = tuple(field for field in required_fields if field not in transform_params)
    if missing_fields:
        missing_fields_description = ", ".join(f"'{field}'" for field in missing_fields)
        raise ValueError(
            f"The '{descriptor.name}' transform params must include {missing_fields_description}."
        )

    for field_name, field_value in transform_params.items():
        field_spec = field_specs[field_name]
        if not _is_valid_transform_param_field(field_value, field_spec):
            raise ValueError(
                f"The '{descriptor.name}' transform param '{field_name}' has an invalid type."
            )

    if descriptor.params_spec.validator is not None:
        descriptor.params_spec.validator(transform_params)


def _is_valid_transform_param_field(
    field_value: object,
    field_spec: TransformParamFieldSpec,
) -> bool:
    param_types = field_spec.param_type
    if not isinstance(param_types, tuple):
        param_types = (param_types,)

    return any(
        _is_valid_transform_param_type(field_value, param_type, field_spec)
        for param_type in param_types
    )


def _is_valid_transform_param_type(
    field_value: object,
    param_type: TransformParamType,
    field_spec: TransformParamFieldSpec,
) -> bool:
    match param_type:
        case TransformParamType.FLOAT:
            # Python treats bool as an int subclass, but JSON booleans are not numeric params.
            return isinstance(field_value, (float, int)) and not isinstance(field_value, bool)
        case TransformParamType.INTEGER:
            # Python treats bool as an int subclass, but JSON booleans are not numeric params.
            return isinstance(field_value, int) and not isinstance(field_value, bool)
        case TransformParamType.STRING:
            return isinstance(field_value, str)
        case TransformParamType.BOOLEAN:
            return isinstance(field_value, bool)
        case TransformParamType.ENUM:
            if isinstance(field_value, str):
                return any(
                    isinstance(v, str) and v.lower() == field_value.lower()
                    for v in field_spec.allowed_enum_values
                )
            return False
        case TransformParamType.OBJECT:
            return isinstance(field_value, dict) or hasattr(field_value, "__dict__")

    raise AssertionError(f"Unsupported transform param type: {param_type}")


TRANSFORMS: dict[str, TransformDescriptor] = {
    "reverse": PhraseTransform(
        "reverse",
        reverse_tones,
        params_spec=TransformParamsSpec(),
    ),
    "golden_ratio": PhraseTransform(
        "golden_ratio",
        golden_ratio_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    allowed_enum_values=tuple(ToneDimension),
                ),
            }
        ),
    ),
    "invert": PhraseTransform(
        "invert",
        invert_tones,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    allowed_enum_values=tuple(ToneDimension),
                ),
            }
        ),
    ),
    "feigenbaum_sequence": PhraseTransform(
        "feigenbaum_sequence",
        feigenbaum_sequence,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    allowed_enum_values=tuple(ToneDimension),
                ),
            }
        ),
    ),
    "transpose": PhraseTransform(
        "transpose",
        transpose_tones,
        params_spec=TransformParamsSpec(
            fields={
                "semitones": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                )
            }
        ),
    ),
    "scale": PhraseTransform(
        "scale",
        scale_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    required=True,
                    allowed_enum_values=tuple(ToneDimension),
                ),
                "factor": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                ),
            }
        ),
    ),
    "pad_silence": PhraseTransform(
        "pad_silence",
        pad_silence_tones,
        params_spec=TransformParamsSpec(
            fields={
                "seconds": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                ),
                "position": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    required=True,
                    allowed_enum_values=("start", "end"),
                ),
            }
        ),
    ),
    "delay": PhraseTransform(
        "delay",
        delay_tones,
        params_spec=TransformParamsSpec(
            fields={
                "seconds": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                )
            }
        ),
    ),
    "repeat": PhraseTransform(
        "repeat",
        repeat_tones,
        params_spec=TransformParamsSpec(
            fields={
                "count": TransformParamFieldSpec(
                    param_type=TransformParamType.INTEGER,
                    required=True,
                )
            }
        ),
    ),
    "erosion": PhraseTransform(
        "erosion",
        erosion_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    allowed_enum_values=tuple(ToneDimension),
                ),
            }
        ),
    ),
    "drift": PhraseTransform(
        "drift",
        drift_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    required=True,
                    allowed_enum_values=tuple(ToneDimension),
                ),
                "rate": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                ),
            }
        ),
    ),
    "phrase_feigenbaum_shrink": PhraseRelativeTransform(
        "phrase_feigenbaum_shrink",
        phrase_feigenbaum_shrink,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    allowed_enum_values=tuple(ToneDimension),
                ),
            }
        ),
    ),
    "phrase_feigenbaum_grow": PhraseRelativeTransform(
        "phrase_feigenbaum_grow",
        phrase_feigenbaum_grow,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    allowed_enum_values=tuple(ToneDimension),
                ),
            }
        ),
    ),
    "phrase_golden_ratio_shrink": PhraseRelativeTransform(
        "phrase_golden_ratio_shrink",
        phrase_golden_ratio_shrink,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    allowed_enum_values=tuple(ToneDimension),
                ),
            }
        ),
    ),
    "phrase_golden_ratio_grow": PhraseRelativeTransform(
        "phrase_golden_ratio_grow",
        phrase_golden_ratio_grow,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    allowed_enum_values=tuple(ToneDimension),
                ),
            }
        ),
    ),
    "score_feigenbaum_sequence": ScoreTransform(
        "score_feigenbaum_sequence",
        score_feigenbaum_sequence,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    allowed_enum_values=tuple(ToneDimension),
                ),
            }
        ),
    ),
    "score_reverse": AllVoicesTransform(
        "score_reverse",
        reverse_tones,
        params_spec=TransformParamsSpec(),
    ),
    "score_golden_ratio": AllVoicesTransform(
        "score_golden_ratio",
        golden_ratio_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    allowed_enum_values=tuple(ToneDimension),
                ),
            }
        ),
    ),
    "score_invert": AllVoicesTransform(
        "score_invert",
        invert_tones,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    allowed_enum_values=tuple(ToneDimension),
                ),
            }
        ),
    ),
    "score_transpose": AllVoicesTransform(
        "score_transpose",
        transpose_tones,
        params_spec=TransformParamsSpec(
            fields={
                "semitones": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                )
            }
        ),
    ),
    "score_scale": AllVoicesTransform(
        "score_scale",
        scale_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    required=True,
                    allowed_enum_values=tuple(ToneDimension),
                ),
                "factor": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                ),
            }
        ),
    ),
    "score_delay": AllVoicesTransform(
        "score_delay",
        delay_tones,
        params_spec=TransformParamsSpec(
            fields={
                "seconds": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                )
            }
        ),
    ),
    "score_repeat": AllVoicesTransform(
        "score_repeat",
        repeat_tones,
        params_spec=TransformParamsSpec(
            fields={
                "count": TransformParamFieldSpec(
                    param_type=TransformParamType.INTEGER,
                    required=True,
                )
            }
        ),
    ),
    "score_drift": AllVoicesTransform(
        "score_drift",
        drift_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    required=True,
                    allowed_enum_values=tuple(ToneDimension),
                ),
                "rate": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                ),
            }
        ),
    ),
    "add_pedal_point": ScoreTransform(
        "add_pedal_point",
        add_pedal_point,
        params_spec=TransformParamsSpec(
            fields={
                "frequency": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                ),
                "duration": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                ),
                "amplitude": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                ),
                "mode": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    allowed_enum_values=("sustain", "repeat"),
                ),
                "pulse_duration": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                ),
            },
            validator=validate_add_pedal_point_params,
        ),
    ),
    "stretto": ScoreTargetMotifsTransform(
        "stretto",
        stretto,
        params_spec=TransformParamsSpec(
            fields={
                "motif": TransformParamFieldSpec(
                    param_type=TransformParamType.STRING,
                    required=True,
                ),
                "num_times": TransformParamFieldSpec(
                    param_type=TransformParamType.INTEGER,
                    required=True,
                ),
                "spacing": TransformParamFieldSpec(
                    param_type=(TransformParamType.ENUM, TransformParamType.FLOAT),
                    required=True,
                    allowed_enum_values=tuple(NAMED_STRETTO_SPACINGS),
                ),
            }
        ),
    ),
    "geological": PhraseTransform(
        "geological",
        apply_geological_transform,
        params_spec=TransformParamsSpec(
            fields={
                "profile": TransformParamFieldSpec(
                    param_type=TransformParamType.OBJECT,
                    required=True,
                ),
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    required=True,
                    allowed_enum_values=tuple(ToneDimension),
                ),
                "max_deviation": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                ),
            }
        ),
    ),
    "frost_effect": ScoreTransform(
        "frost_effect",
        frost_effect,
        params_spec=TransformParamsSpec(
            fields={
                "iterations": TransformParamFieldSpec(
                    param_type=TransformParamType.INTEGER,
                )
            }
        ),
    ),
    "score_geological": AllVoicesTransform(
        "score_geological",
        apply_geological_transform,
        params_spec=TransformParamsSpec(
            fields={
                "profile": TransformParamFieldSpec(
                    param_type=TransformParamType.OBJECT,
                    required=True,
                ),
                "dimension": TransformParamFieldSpec(
                    param_type=TransformParamType.ENUM,
                    required=True,
                    allowed_enum_values=tuple(ToneDimension),
                ),
                "max_deviation": TransformParamFieldSpec(
                    param_type=TransformParamType.FLOAT,
                    required=True,
                ),
            },
            validator=validate_geological_params,
        ),
    ),
    "accelerando": PhraseTransform(
        "accelerando",
        accelerando_transform,
        params_spec=TransformParamsSpec(
            fields={
                "strength": TransformParamFieldSpec(
                    param_type=(TransformParamType.ENUM, TransformParamType.FLOAT),
                    required=True,
                    allowed_enum_values=tuple(INTENSITY_LEVELS),
                ),
                "jaggedness": TransformParamFieldSpec(
                    param_type=(TransformParamType.ENUM, TransformParamType.FLOAT),
                    allowed_enum_values=tuple(INTENSITY_LEVELS),
                ),
                "seed": TransformParamFieldSpec(
                    param_type=TransformParamType.INTEGER,
                ),
            }
        ),
    ),
    "ritardando": PhraseTransform(
        "ritardando",
        ritardando_transform,
        params_spec=TransformParamsSpec(
            fields={
                "strength": TransformParamFieldSpec(
                    param_type=(TransformParamType.ENUM, TransformParamType.FLOAT),
                    required=True,
                    allowed_enum_values=tuple(INTENSITY_LEVELS),
                ),
                "jaggedness": TransformParamFieldSpec(
                    param_type=(TransformParamType.ENUM, TransformParamType.FLOAT),
                    allowed_enum_values=tuple(INTENSITY_LEVELS),
                ),
                "seed": TransformParamFieldSpec(
                    param_type=TransformParamType.INTEGER,
                ),
            }
        ),
    ),
}


def parse_motifs(motif_definitions: dict[str, list[str]]) -> dict[str, list[Tone]]:
    if not isinstance(motif_definitions, dict):
        raise ValueError("Composition 'motifs' must be an object mapping motif names to tone lists.")

    parsed_motifs: dict[str, list[Tone]] = {}

    for motif_name, tone_strings in motif_definitions.items():
        parsed_motif_name, motif_tones = _parse_motif_definition(motif_name, tone_strings)
        parsed_motifs[parsed_motif_name] = motif_tones

    return parsed_motifs


def parse_transform_spec(
    transform_spec: TransformSpec,
    transform_scope: str,
) -> tuple[str, dict[str, object]]:
    if not isinstance(transform_spec, dict):
        raise ValueError(f"{transform_scope} transforms must be objects with a 'name' field.")

    transform_name = transform_spec.get("name")
    if not isinstance(transform_name, str) or not transform_name:
        raise ValueError(f"{transform_scope} transform objects must include a non-empty 'name' string.")

    transform_params = transform_spec.get("params", {})
    if not isinstance(transform_params, dict):
        raise ValueError(f"{transform_scope} transform params must be an object with named fields.")

    return transform_name, transform_params


def _apply_phrase_transform_spec(
    descriptor: TransformDescriptor,
    phrase_tones: list[Tone],
    transform_params: dict[str, object],
    reference_tones: list[Tone] | None,
) -> list[Tone]:
    _validate_transform_params(descriptor, transform_params)

    if isinstance(descriptor, PhraseTransform):
        return _apply_phrase_transform(descriptor.transform, phrase_tones, transform_params)

    if isinstance(descriptor, PhraseRelativeTransform):
        phrase_reference_tones = reference_tones if reference_tones else []
        resolved_transform_params = resolve_profile_in_params(transform_params)
        return descriptor.transform(phrase_tones, phrase_reference_tones, **resolved_transform_params)

    raise ValueError(f"Transform '{descriptor.name}' is not a phrase transform.")


def _apply_phrase_transform_specs(
    phrase_tones: list[Tone],
    transform_specs: list[TransformSpec],
    reference_tones: list[Tone] | None,
) -> list[Tone]:
    for transform_spec in transform_specs:
        transform_name, transform_params = parse_transform_spec(transform_spec, "Phrase")

        if transform_name not in TRANSFORMS:
            raise ValueError(f"Unknown transform '{transform_name}'")

        descriptor = TRANSFORMS[transform_name]
        phrase_tones = _apply_phrase_transform_spec(descriptor, phrase_tones, transform_params, reference_tones)

    return phrase_tones


def _build_voice_tones(
    phrase_configs: list[PhraseConfig],
    parsed_motifs: dict[str, list[Tone]],
    previous_voice_tones: list[Tone],
) -> list[Tone]:
    combined_tones: list[Tone] = []

    for phrase_config in phrase_configs:
        reference_tones = combined_tones if combined_tones else previous_voice_tones
        phrase_tones = parse_phrase(phrase_config, parsed_motifs, reference_tones)
        combined_tones.extend(phrase_tones)

    return combined_tones


def _validate_and_extract_motifs(phrase_config: PhraseConfig) -> list[str]:
    """
    Validates the phrase config structure and extracts the motif names.
    
    Raises:
        ValueError: If the structure is invalid or motifs are missing/empty.
    """
    if not isinstance(phrase_config, dict):
        raise ValueError("Each phrase must be an object.")

    if "motifs" not in phrase_config:
        raise ValueError("Phrase definitions must include 'motifs'.")

    motif_names = _require_non_empty_string_list(phrase_config["motifs"], "Phrase 'motifs' must be a non-empty list.")

    return motif_names


def _build_base_phrase_tones(
    phrase_config: PhraseConfig,
    parsed_motifs: dict[str, list[Tone]],
) -> list[Tone]:
    motif_names = _validate_and_extract_motifs(phrase_config)

    phrase_tones: list[Tone] = []

    for motif_name in motif_names:
        if motif_name not in parsed_motifs:
            raise ValueError(f"Motif '{motif_name}' not found in parsed motifs.")

        phrase_tones.extend(copy_tones(parsed_motifs[motif_name]))

    return phrase_tones


def parse_phrase(
    phrase_config: PhraseConfig,
    parsed_motifs: dict[str, list[Tone]],
    reference_tones: list[Tone] | None = None,
) -> list[Tone]:
    phrase_tones = _build_base_phrase_tones(phrase_config, parsed_motifs)

    transform_specs = phrase_config.get("transforms", [])
    if not isinstance(transform_specs, list):
        raise ValueError("Phrase 'transforms' must be a list.")

    return _apply_phrase_transform_specs(phrase_tones, transform_specs, reference_tones)


def parse_voice(
    voice_config: VoiceConfig,
    parsed_motifs: dict[str, list[Tone]],
    previous_voice_tones: list[Tone],
) -> tuple[Voice, list[Tone]]:
    if not isinstance(voice_config, dict):
        raise ValueError("Each voice must be an object.")

    phrase_configs = voice_config.get("phrases", [])
    if not isinstance(phrase_configs, list):
        raise ValueError("Voice 'phrases' must be a list.")

    combined_tones = _build_voice_tones(phrase_configs, parsed_motifs, previous_voice_tones)

    return Voice(combined_tones), combined_tones


def _validate_composition_structure(composition_document: CompositionDocument) -> tuple[dict, list, list]:
    """
    Validates the structure of the composition document and extracts key sections.
    
    Raises:
        ValueError: If the document structure is invalid.
    """
    if not isinstance(composition_document, dict):
        raise ValueError("Composition document must be an object.")

    motif_definitions = composition_document.get("motifs", {})
    if not isinstance(motif_definitions, dict):
        raise ValueError("Composition 'motifs' must be an object mapping motif names to tone lists.")

    composition_config = composition_document.get("composition", {})
    if not isinstance(composition_config, dict):
        raise ValueError("Composition 'composition' must be an object.")

    voice_configs = _require_list(composition_config.get("voices", []), "Composition 'voices' must be a list.")

    score_transform_specs = _require_list(
        composition_config.get("score_transforms", []),
        "Composition 'score_transforms' must be a list.",
    )

    return motif_definitions, voice_configs, score_transform_specs


def _apply_all_voices_transform(
    score: Score,
    descriptor: TransformDescriptor,
    transform_params: dict[str, object]
) -> Score:
    _validate_transform_params(descriptor, transform_params)
    return _apply_all_voices_transform_with_optional_params(descriptor.transform, score, transform_params)


def _apply_score_target_motifs_transform(
    score: Score,
    descriptor: TransformDescriptor,
    transform_params: dict[str, object],
    parsed_motifs: dict[str, list[Tone]],
) -> Score:
    _validate_transform_params(descriptor, transform_params)

    resolved_transform_params = resolve_profile_in_params(transform_params)
    return cast(Score, descriptor.transform(score, parsed_motifs, **resolved_transform_params))


def _build_score_voices(voice_configs: list[VoiceConfig], parsed_motifs: dict[str, list[Tone]]) -> list[Voice]:
    voices: list[Voice] = []
    previous_voice_tones: list[Tone] = []

    for voice_config in voice_configs:
        voice, previous_voice_tones = parse_voice(voice_config, parsed_motifs, previous_voice_tones)
        voices.append(voice)

    return voices


def _apply_score_transform_spec(
    score: Score,
    transform_spec: TransformSpec,
    parsed_motifs: dict[str, list[Tone]],
) -> Score:
    transform_name, transform_params = parse_transform_spec(transform_spec, "Score")

    if transform_name not in TRANSFORMS:
        raise ValueError(f"Unknown score transform '{transform_name}'")

    descriptor = TRANSFORMS[transform_name]

    if isinstance(descriptor, ScoreTargetMotifsTransform):
        return _apply_score_target_motifs_transform(score, descriptor, transform_params, parsed_motifs)

    if isinstance(descriptor, ScoreTransform):
        return _apply_score_transform(score, descriptor, transform_params)

    if isinstance(descriptor, AllVoicesTransform):
        return _apply_all_voices_transform(score, descriptor, transform_params)

    raise ValueError(f"Transform '{transform_name}' is not a score transform.")


def parse_composition(composition_document: CompositionDocument) -> Score:
    motif_definitions, voice_configs, score_transform_specs = _validate_composition_structure(composition_document)

    parsed_motifs = parse_motifs(motif_definitions)
    score = Score(_build_score_voices(voice_configs, parsed_motifs))

    for transform_spec in score_transform_specs:
        score = _apply_score_transform_spec(score, transform_spec, parsed_motifs)

    return score
