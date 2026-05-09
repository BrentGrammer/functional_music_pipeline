from collections.abc import Callable

from composition.profile_factory import build_profile
from composition.schema import (
    CompositionDocument,
    PhraseConfig,
    TransformSpec,
    TransformParams,
    VoiceConfig,
)
from score_model.score import Score
from score_model.tone import Tone
from score_model.tone_utils import copy_tones
from score_model.voice import Voice
from transforms.base import (
    ToneSequence,
    TransformDescriptor,
    TransformParamsSpec,
    TransformScope,
    apply_to_all_voices,
)
from transforms.delay import delay_tones
from transforms.duration import (
    accelerando_transform,
    feigenbaum_sequence,
    phrase_feigenbaum_grow,
    phrase_feigenbaum_shrink,
    ritardando_transform,
    score_feigenbaum_sequence,
)
from transforms.drift import drift_transform
from transforms.erosion import erosion_transform
from transforms.fugue import add_pedal_point, stretto
from transforms.golden_ratio import (
    golden_ratio_transform,
    phrase_golden_ratio_grow,
    phrase_golden_ratio_shrink,
)
from transforms.inversion import invert_tones
from transforms.repeat import repeat_tones
from transforms.reversal import reverse_tones
from transforms.pad_silence import pad_silence_tones
from transforms.scale import scale_transform
from transforms.frost import frost_effect
from transforms.transpose import transpose_tones
from transforms.geological import (
    apply_geological_transform,
)


def resolve_profile_in_params(
    transform_params: TransformParams | None,
) -> TransformParams | None:
    """
    If transform_params contains a 'profile' key with a dict value,
    it resolves it into a StochasticProfile instance using the factory.
    Otherwise, it returns the params unchanged.
    """
    if not isinstance(transform_params, dict) or "profile" not in transform_params:
        return transform_params

    profile_config = transform_params.get("profile")
    if not isinstance(profile_config, dict):
        # Allow pre-resolved profiles to pass through without modification.
        return transform_params

    # The type system doesn't know profile_config is ProfileConfig here,
    # but build_profile will validate its structure at runtime.
    resolved_profile = build_profile(profile_config)  # type: ignore

    # Return a new dictionary with the 'profile' value replaced by the instance.
    new_params = transform_params.copy()
    # Mypy cannot follow the type transformation here. The function's guards
    # ensure `transform_params` is a `GeologicalTransformParams` dict, but `copy()`
    # loses this specific type info. Mypy falls back to the broader `dict[str, primitive]`
    # type from the `TransformParams` union, causing a false positive error.
    new_params["profile"] = resolved_profile  # type: ignore
    return new_params


def _parse_tone_string(tone_string: str) -> Tone:
    normalized_tone_string = str(tone_string)

    if ":" in normalized_tone_string:
        frequency_value, duration_value = normalized_tone_string.split(":", 1)
        return Tone(float(frequency_value), duration=float(duration_value))

    return Tone(float(normalized_tone_string))


def _validate_transform_name(transform_name: object, transform_scope: str) -> str:
    if not isinstance(transform_name, str) or not transform_name:
        raise ValueError(f"{transform_scope} transform objects must include a non-empty 'name' string.")

    return transform_name


def _validate_transform_params(transform_params: object, transform_scope: str) -> TransformParams | None:
    if transform_params is not None and not isinstance(transform_params, dict):
        raise ValueError(f"{transform_scope} transform params must be an object with named fields.")

    return transform_params


def _apply_transform_with_optional_params(
    transform_func: Callable[..., ToneSequence],
    tones: ToneSequence,
    transform_params: TransformParams | None,
) -> ToneSequence:
    if transform_params is None:
        return transform_func(tones)

    if isinstance(transform_params, dict):
        return transform_func(tones, **transform_params)

    raise AssertionError("Unreachable: transform_params must be None or a dict.")


def _apply_score_transform(
    score: Score,
    descriptor: TransformDescriptor,
    transform_params: TransformParams | None,
) -> Score:
    if transform_params is None:
        return descriptor.transform(score)

    if isinstance(transform_params, dict):
        return descriptor.transform(score, **transform_params)

    raise AssertionError("Unreachable: transform_params must be None or a dict.")


def _apply_all_voices_transform_with_optional_params(
    transform_func: Callable[..., ToneSequence],
    score: Score,
    transform_params: TransformParams | None,
) -> Score:
    if transform_params is None:
        return apply_to_all_voices(transform_func)(score)

    if isinstance(transform_params, dict):
        return apply_to_all_voices(transform_func, **transform_params)(score)

    raise AssertionError("Unreachable: transform_params must be None or a dict.")


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


def _require_params_for_descriptor(
    descriptor: TransformDescriptor,
    transform_params: TransformParams | None,
) -> None:
    required_fields = descriptor.params_spec.required_fields
    if not required_fields:
        return

    required_fields_description = ", ".join(f"'{field}'" for field in required_fields)
    error_message = (
        f"The '{descriptor.name}' transform requires an object with named fields specifying "
        f"{required_fields_description}."
    )
    if not isinstance(transform_params, dict):
        raise ValueError(error_message)

    missing_fields = tuple(field for field in required_fields if field not in transform_params)
    if missing_fields:
        missing_fields_description = ", ".join(f"'{field}'" for field in missing_fields)
        raise ValueError(
            f"The '{descriptor.name}' transform params must include {missing_fields_description}."
        )


TRANSFORMS: dict[str, TransformDescriptor] = {
    "reverse": TransformDescriptor("reverse", TransformScope.PHRASE, reverse_tones),
    "golden_ratio": TransformDescriptor("golden_ratio", TransformScope.PHRASE, golden_ratio_transform),
    "invert": TransformDescriptor("invert", TransformScope.PHRASE, invert_tones),
    "feigenbaum_sequence": TransformDescriptor("feigenbaum_sequence", TransformScope.PHRASE, feigenbaum_sequence),
    "transpose": TransformDescriptor(
        "transpose",
        TransformScope.PHRASE,
        transpose_tones,
        params_spec=TransformParamsSpec(required_fields=("semitones",)),
    ),
    "scale": TransformDescriptor(
        "scale",
        TransformScope.PHRASE,
        scale_transform,
        params_spec=TransformParamsSpec(required_fields=("dimension", "factor")),
    ),
    "pad_silence": TransformDescriptor(
        "pad_silence",
        TransformScope.PHRASE,
        pad_silence_tones,
        params_spec=TransformParamsSpec(required_fields=("seconds", "position")),
    ),
    "delay": TransformDescriptor(
        "delay",
        TransformScope.PHRASE,
        delay_tones,
        params_spec=TransformParamsSpec(required_fields=("seconds",)),
    ),
    "repeat": TransformDescriptor(
        "repeat",
        TransformScope.PHRASE,
        repeat_tones,
        params_spec=TransformParamsSpec(required_fields=("count",)),
    ),
    "erosion": TransformDescriptor("erosion", TransformScope.PHRASE, erosion_transform),
    "drift": TransformDescriptor("drift", TransformScope.PHRASE, drift_transform),
    "phrase_feigenbaum_shrink": TransformDescriptor("phrase_feigenbaum_shrink", TransformScope.PHRASE_RELATIVE, phrase_feigenbaum_shrink),
    "phrase_feigenbaum_grow": TransformDescriptor("phrase_feigenbaum_grow", TransformScope.PHRASE_RELATIVE, phrase_feigenbaum_grow),
    "phrase_golden_ratio_shrink": TransformDescriptor("phrase_golden_ratio_shrink", TransformScope.PHRASE_RELATIVE, phrase_golden_ratio_shrink),
    "phrase_golden_ratio_grow": TransformDescriptor("phrase_golden_ratio_grow", TransformScope.PHRASE_RELATIVE, phrase_golden_ratio_grow),
    "score_feigenbaum_sequence": TransformDescriptor("score_feigenbaum_sequence", TransformScope.SCORE, score_feigenbaum_sequence),
    "score_reverse": TransformDescriptor("score_reverse", TransformScope.ALL_VOICES, reverse_tones),
    "score_golden_ratio": TransformDescriptor("score_golden_ratio", TransformScope.ALL_VOICES, golden_ratio_transform),
    "score_invert": TransformDescriptor("score_invert", TransformScope.ALL_VOICES, invert_tones),
    "score_transpose": TransformDescriptor(
        "score_transpose",
        TransformScope.ALL_VOICES,
        transpose_tones,
        params_spec=TransformParamsSpec(required_fields=("semitones",)),
    ),
    "score_scale": TransformDescriptor(
        "score_scale",
        TransformScope.ALL_VOICES,
        scale_transform,
        params_spec=TransformParamsSpec(required_fields=("dimension", "factor")),
    ),
    "score_delay": TransformDescriptor(
        "score_delay",
        TransformScope.ALL_VOICES,
        delay_tones,
        params_spec=TransformParamsSpec(required_fields=("seconds",)),
    ),
    "score_repeat": TransformDescriptor(
        "score_repeat",
        TransformScope.ALL_VOICES,
        repeat_tones,
        params_spec=TransformParamsSpec(required_fields=("count",)),
    ),
    "score_drift": TransformDescriptor("score_drift", TransformScope.ALL_VOICES, drift_transform),
    "add_pedal_point": TransformDescriptor("add_pedal_point", TransformScope.SCORE, add_pedal_point),
    "stretto": TransformDescriptor(
        "stretto",
        TransformScope.SCORE_TARGET_MOTIFS,
        stretto,
        params_spec=TransformParamsSpec(required_fields=("motif", "num_times", "spacing")),
    ),
    "geological": TransformDescriptor("geological", TransformScope.PHRASE, apply_geological_transform),
    "frost_effect": TransformDescriptor("frost_effect", TransformScope.SCORE, frost_effect),
    "score_geological": TransformDescriptor("score_geological", TransformScope.ALL_VOICES, apply_geological_transform),
    "accelerando": TransformDescriptor(
        "accelerando",
        TransformScope.PHRASE,
        accelerando_transform,
        params_spec=TransformParamsSpec(required_fields=("strength",)),
    ),
    "ritardando": TransformDescriptor(
        "ritardando",
        TransformScope.PHRASE,
        ritardando_transform,
        params_spec=TransformParamsSpec(required_fields=("strength",)),
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
) -> tuple[str, TransformParams | None]:
    if isinstance(transform_spec, str):
        if not transform_spec:
            raise ValueError(f"{transform_scope} transform names must be non-empty strings.")
        return transform_spec, None

    if not isinstance(transform_spec, dict):
        raise ValueError(f"{transform_scope} transforms must be strings or objects with a 'name' field.")

    transform_name = _validate_transform_name(transform_spec.get("name"), transform_scope)
    transform_params = _validate_transform_params(transform_spec.get("params"), transform_scope)

    return transform_name, transform_params


def _apply_phrase_transform_spec(
    descriptor: TransformDescriptor,
    phrase_tones: list[Tone],
    transform_params: TransformParams | None,
    reference_tones: list[Tone] | None,
) -> list[Tone]:
    if descriptor.scope == TransformScope.PHRASE:
        _require_params_for_descriptor(descriptor, transform_params)
        return _apply_transform_with_optional_params(descriptor.transform, phrase_tones, transform_params)

    if descriptor.scope == TransformScope.PHRASE_RELATIVE:
        phrase_reference_tones = reference_tones if reference_tones else []
        if transform_params is None:
            return descriptor.transform(phrase_tones, phrase_reference_tones)
        if isinstance(transform_params, dict):
            return descriptor.transform(phrase_tones, phrase_reference_tones, **transform_params)
        raise AssertionError("Unreachable: transform_params must be None or a dict.")

    raise ValueError(f"Transform '{descriptor.name}' is not a phrase transform.")


def _apply_phrase_transform_specs(
    phrase_tones: list[Tone],
    transform_specs: list[TransformSpec],
    reference_tones: list[Tone] | None,
) -> list[Tone]:
    for transform_spec in transform_specs:
        transform_name, transform_params = parse_transform_spec(transform_spec, "Phrase")
        transform_params = resolve_profile_in_params(transform_params)

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
    transform_params: TransformParams | None
) -> Score:
    _require_params_for_descriptor(descriptor, transform_params)
    return _apply_all_voices_transform_with_optional_params(descriptor.transform, score, transform_params)


def _apply_score_target_motifs_transform(
    score: Score,
    descriptor: TransformDescriptor,
    transform_params: TransformParams | None,
    parsed_motifs: dict[str, list[Tone]],
) -> Score:
    _require_params_for_descriptor(descriptor, transform_params)
    if transform_params is None:
        raise ValueError(f"The '{descriptor.name}' transform requires an object with named fields.")

    return descriptor.transform(score, parsed_motifs, **transform_params)


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
    transform_params = resolve_profile_in_params(transform_params)

    if transform_name not in TRANSFORMS:
        raise ValueError(f"Unknown score transform '{transform_name}'")

    descriptor = TRANSFORMS[transform_name]

    if descriptor.scope == TransformScope.SCORE_TARGET_MOTIFS:
        return _apply_score_target_motifs_transform(score, descriptor, transform_params, parsed_motifs)

    if descriptor.scope == TransformScope.SCORE:
        return _apply_score_transform(score, descriptor, transform_params)

    if descriptor.scope == TransformScope.ALL_VOICES:
        return _apply_all_voices_transform(score, descriptor, transform_params)

    raise ValueError(f"Transform '{transform_name}' is not a score transform.")


def parse_composition(composition_document: CompositionDocument) -> Score:
    motif_definitions, voice_configs, score_transform_specs = _validate_composition_structure(composition_document)

    parsed_motifs = parse_motifs(motif_definitions)
    score = Score(_build_score_voices(voice_configs, parsed_motifs))

    for transform_spec in score_transform_specs:
        score = _apply_score_transform_spec(score, transform_spec, parsed_motifs)

    return score
