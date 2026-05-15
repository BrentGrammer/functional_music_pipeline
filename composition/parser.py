from collections.abc import Callable, Mapping

from score_model.score import Score
from score_model.tone import Tone
from score_model.tone_utils import copy_tones
from score_model.voice import Voice
from transforms.base import (
    EachVoiceTransform,
    PhraseRelativeTransform,
    PhraseTransform,
    ScoreTargetMotifsTransform,
    ScoreTransform,
    ToneSequence,
    TransformWithCallable,
    ScorePipelineStep
)
from transforms.registry import TRANSFORMS


def apply_to_each_voice(
    transform_func: Callable[..., ToneSequence],
    *args: int | float,
    **kwargs: object,
) -> ScorePipelineStep:
    def wrapper(score: Score) -> Score:
        for i, voice in enumerate(score.voices):
            modified_tones = transform_func(voice.tones, *args, **kwargs)
            score.voices[i] = Voice(modified_tones)
        return score

    return wrapper


def _parse_tone_string(tone_string: str) -> Tone:
    normalized_tone_string = str(tone_string)

    if ":" in normalized_tone_string:
        frequency_value, duration_value = normalized_tone_string.split(":", 1)
        return Tone(float(frequency_value), duration=float(duration_value))

    return Tone(float(normalized_tone_string))

def _parse_motif_definition(motif_name: object, tone_strings: object) -> tuple[str, list[Tone]]:
    if not isinstance(motif_name, str):
        raise ValueError("Motif names must be strings.")
    if not isinstance(tone_strings, list):
        raise ValueError(f"Motif '{motif_name}' must map to a list of tone strings.")

    return motif_name, [_parse_tone_string(tone_string) for tone_string in tone_strings]


def parse_motifs(motif_definitions: object) -> dict[str, list[Tone]]:
    if not isinstance(motif_definitions, dict):
        raise ValueError("Composition 'motifs' must be an object mapping motif names to tone lists.")

    parsed_motifs: dict[str, list[Tone]] = {}

    for motif_name, tone_strings in motif_definitions.items():
        parsed_motif_name, motif_tones = _parse_motif_definition(motif_name, tone_strings)
        parsed_motifs[parsed_motif_name] = motif_tones

    return parsed_motifs


def parse_transform_spec(
    transform_spec: object,
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
    descriptor: TransformWithCallable,
    phrase_tones: list[Tone],
    transform_params: Mapping[str, object],
    reference_tones: list[Tone] | None,
) -> list[Tone]:
    descriptor.validate_params(transform_params)

    if isinstance(descriptor, PhraseTransform):
        return descriptor.transform(phrase_tones, **transform_params)

    if isinstance(descriptor, PhraseRelativeTransform):
        phrase_reference_tones = reference_tones if reference_tones else []
        return descriptor.transform(phrase_tones, phrase_reference_tones, **transform_params)

    raise ValueError(f"Transform '{descriptor.name}' is not a phrase transform.")


def _apply_phrase_transform_specs(
    phrase_tones: list[Tone],
    transform_specs: list[object],
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
    phrase_configs: list[object],
    parsed_motifs: dict[str, list[Tone]],
    previous_voice_tones: list[Tone],
) -> list[Tone]:
    combined_tones: list[Tone] = []

    for phrase_config in phrase_configs:
        reference_tones = combined_tones if combined_tones else previous_voice_tones
        phrase_tones = parse_phrase(phrase_config, parsed_motifs, reference_tones)
        combined_tones.extend(phrase_tones)

    return combined_tones


def _validate_and_extract_motifs(phrase_config: object) -> list[str]:
    """
    Validates the phrase config structure and extracts the motif names.
    
    Raises:
        ValueError: If the structure is invalid or motifs are missing/empty.
    """
    if not isinstance(phrase_config, dict):
        raise ValueError("Each phrase must be an object.")

    if "motifs" not in phrase_config:
        raise ValueError("Phrase definitions must include 'motifs'.")

    motif_names = phrase_config["motifs"]
    if not isinstance(motif_names, list) or not motif_names:
        raise ValueError("Phrase 'motifs' must be a non-empty list.")

    for string_value in motif_names:
        if not isinstance(string_value, str) or not string_value:
            raise ValueError("Phrase 'motifs' entries must be non-empty strings.")

    return motif_names


def _build_base_phrase_tones(
    phrase_config: object,
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
    phrase_config: object,
    parsed_motifs: dict[str, list[Tone]],
    reference_tones: list[Tone] | None = None,
) -> list[Tone]:
    if not isinstance(phrase_config, dict):
        raise ValueError("Each phrase must be an object.")

    phrase_tones = _build_base_phrase_tones(phrase_config, parsed_motifs)

    transform_specs = phrase_config.get("transforms", [])
    if not isinstance(transform_specs, list):
        raise ValueError("Phrase 'transforms' must be a list.")

    return _apply_phrase_transform_specs(phrase_tones, transform_specs, reference_tones)


def parse_voice(
    voice_config: object,
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


def _validate_composition_structure(
    composition_document: object,
) -> tuple[dict[object, object], list[object], list[object]]:
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

    voice_configs = composition_config.get("voices", [])
    if not isinstance(voice_configs, list):
        raise ValueError("Composition 'voices' must be a list.")

    score_transform_specs = composition_config.get("score_transforms", [])
    if not isinstance(score_transform_specs, list):
        raise ValueError("Composition 'score_transforms' must be a list.")

    return motif_definitions, voice_configs, score_transform_specs

def _build_score_voices(voice_configs: list[object], parsed_motifs: dict[str, list[Tone]]) -> list[Voice]:
    voices: list[Voice] = []
    previous_voice_tones: list[Tone] = []

    for voice_config in voice_configs:
        voice, previous_voice_tones = parse_voice(voice_config, parsed_motifs, previous_voice_tones)
        voices.append(voice)

    return voices


def _apply_score_transform_spec(
    score: Score,
    transform_spec: object,
    parsed_motifs: dict[str, list[Tone]],
) -> Score:
    transform_name, transform_params = parse_transform_spec(transform_spec, "Score")

    if transform_name not in TRANSFORMS:
        raise ValueError(f"Unknown score transform '{transform_name}'")

    descriptor = TRANSFORMS[transform_name]

    descriptor.validate_params(transform_params)

    if isinstance(descriptor, ScoreTargetMotifsTransform):
        return descriptor.transform(score, parsed_motifs, **transform_params)

    if isinstance(descriptor, ScoreTransform):
        return descriptor.transform(score, **transform_params)

    if isinstance(descriptor, EachVoiceTransform):
        return apply_to_each_voice(descriptor.transform, **transform_params)(score)

    raise ValueError(f"Transform '{transform_name}' is not a score transform.")


def parse_composition(composition_document: object) -> Score:
    motif_definitions, voice_configs, score_transform_specs = _validate_composition_structure(composition_document)

    parsed_motifs = parse_motifs(motif_definitions)
    score = Score(_build_score_voices(voice_configs, parsed_motifs))

    for transform_spec in score_transform_specs:
        score = _apply_score_transform_spec(score, transform_spec, parsed_motifs)

    return score
