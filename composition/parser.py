from collections.abc import Mapping

from composition.score_plan import (
    PhrasePlan,
    PhraseTransformRequest,
    ScorePlan,
    ScoreTransformRequest,
    TransformRequest,
    VoicePlan,
)
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.tone_utils import copy_tones
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from transforms.base import (
    PhraseTransformContext,
    PhraseTransformDefinition,
    ScorePipelineStep,
    TransformLevel,
    ScoreTransformDefinition,
)
from transforms.registry import PHRASE_TRANSFORMS, SCORE_TRANSFORMS


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
    descriptor: PhraseTransformDefinition,
    phrase_tones: list[Tone],
    transform_params: Mapping[str, object],
    reference_tones: list[Tone] | None,
) -> list[Tone]:
    descriptor.validate_params(transform_params)

    if isinstance(descriptor, PhraseTransformDefinition):
        # Build a minimal context where the reference phrase is voice[0].phrases[0]
        # and the current phrase is voice[0].phrases[1]. This mirrors the prior
        # behavior that presented two-phrase contexts to the transform.
        reference_phrase = Phrase(motifs=[Motif(name="<parsed>", tones=copy_tones(reference_tones or []))])
        current_phrase = Phrase(motifs=[Motif(name="<parsed>", tones=copy_tones(phrase_tones))])
        transformed_phrase = descriptor.transform(
            PhraseTransformContext(score=Score(voices=[Voice(phrases=[reference_phrase, current_phrase])]), voice_index=0, phrase_index=1),
            transform_params,
        )
        return [tone for motif in transformed_phrase.motifs for tone in motif.tones]

    raise ValueError(f"Transform '{descriptor.name}' is not a phrase transform.")


def _apply_phrase_transform_specs(
    phrase_tones: list[Tone],
    transform_specs: list[object],
    reference_tones: list[Tone] | None,
) -> list[Tone]:
    for transform_spec in transform_specs:
        transform_name, transform_params = parse_transform_spec(transform_spec, TransformLevel.PHRASE)

        if transform_name in PHRASE_TRANSFORMS:
            descriptor = PHRASE_TRANSFORMS[transform_name]
        elif transform_name in SCORE_TRANSFORMS:
            raise ValueError(f"Transform '{transform_name}' is only available as a score transform.")
        else:
            raise ValueError(f"Unknown transform '{transform_name}'")

        phrase_tones = _apply_phrase_transform_spec(descriptor, phrase_tones, transform_params, reference_tones)

    return phrase_tones


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


def parse_phrase(
    phrase_config: object,
    parsed_motifs: dict[str, list[Tone]],
    reference_tones: list[Tone] | None = None,
) -> list[Tone]:
    if not isinstance(phrase_config, dict):
        raise ValueError("Each phrase must be an object.")

    motif_names = _validate_and_extract_motifs(phrase_config)
    phrase_tones: list[Tone] = []

    for motif_name in motif_names:
        if motif_name not in parsed_motifs:
            raise ValueError(f"Motif '{motif_name}' not found in parsed motifs.")
        phrase_tones.extend(copy_tones(parsed_motifs[motif_name]))

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

    parsed_phrases: list[Phrase] = []
    combined_tones: list[Tone] = []
    for phrase_config in phrase_configs:
        motif_names = _validate_and_extract_motifs(phrase_config)
        transform_specs = phrase_config.get("transforms", [])
        if not isinstance(transform_specs, list):
            raise ValueError("Phrase 'transforms' must be a list.")

        if transform_specs:
            reference_tones = combined_tones if combined_tones else previous_voice_tones
            phrase_tones = parse_phrase(phrase_config, parsed_motifs, reference_tones)
            parsed_phrase = Phrase(motifs=[Motif(name="<transformed>", tones=phrase_tones)])
        else:
            phrase_motifs: list[Motif] = []
            for motif_name in motif_names:
                if motif_name not in parsed_motifs:
                    raise ValueError(f"Motif '{motif_name}' not found in parsed motifs.")

                phrase_motifs.append(Motif(name=motif_name, tones=copy_tones(parsed_motifs[motif_name])))

            parsed_phrase = Phrase(motifs=phrase_motifs)
            phrase_tones = [tone for motif in phrase_motifs for tone in motif.tones]

        parsed_phrases.append(parsed_phrase)
        combined_tones.extend(phrase_tones)

    return Voice(phrases=parsed_phrases), combined_tones


def _validate_composition_structure(
    composition_document: object,
) -> None:
    """
    Validates the structure of the composition document.

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


def _extract_composition_sections(
    composition_document: object,
) -> tuple[dict[object, object], list[object], list[object]]:
    """
    Extracts key sections from the composition document.
    Assumes the structure has already been validated.
    """
    if not isinstance(composition_document, dict):
        return {}, [], []

    motifs_section = composition_document.get("motifs", {})
    if not isinstance(motifs_section, dict):
        motifs_section = {}

    composition_config = composition_document.get("composition", {})
    if not isinstance(composition_config, dict):
        composition_config = {}

    voices_section = composition_config.get("voices", [])
    if not isinstance(voices_section, list):
        voices_section = []

    score_transforms_section = composition_config.get("score_transforms", [])
    if not isinstance(score_transforms_section, list):
        score_transforms_section = []

    return motifs_section, voices_section, score_transforms_section


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
) -> Score:
    transform_name, transform_params = parse_transform_spec(transform_spec, "Score")

    if transform_name in SCORE_TRANSFORMS:
        descriptor = SCORE_TRANSFORMS[transform_name]
    elif transform_name in PHRASE_TRANSFORMS:
        raise ValueError(f"Transform '{transform_name}' is only available as a phrase transform.")
    else:
        raise ValueError(f"Unknown score transform '{transform_name}'")

    # Expect SCORE_TRANSFORMS to contain ScoreTransformDefinition instances only.
    if not isinstance(descriptor, ScoreTransformDefinition):
        raise ValueError(f"Score transform '{transform_name}' must be a ScoreTransformDefinition.")

    descriptor.validate_params(transform_params)
    return descriptor.transform(score, transform_params)


def _extract_requests_from_phrase(phrase_config: object, voice_index: int, phrase_index: int) -> list[PhraseTransformRequest]:
    if not isinstance(phrase_config, dict):
        raise ValueError("Each phrase must be an object.")

    transform_specs = phrase_config.get("transforms", [])
    if not isinstance(transform_specs, list):
        raise ValueError("Phrase 'transforms' must be a list.")

    def build_request(spec: object) -> PhraseTransformRequest:
        name, params = parse_transform_spec(spec, TransformLevel.PHRASE)
        return PhraseTransformRequest(
            voice_index=voice_index,
            phrase_index=phrase_index,
            transform_request=TransformRequest(name=name, params=params),
        )

    return [build_request(spec) for spec in transform_specs]


def _extract_requests_from_voice(voice_config: object, voice_index: int) -> list[PhraseTransformRequest]:
    if not isinstance(voice_config, dict):
        raise ValueError("Each voice must be an object.")

    phrase_configs = voice_config.get("phrases", [])
    if not isinstance(phrase_configs, list):
        raise ValueError("Voice 'phrases' must be a list.")

    return [request for phrase_index, phrase_config in enumerate(phrase_configs) for request in _extract_requests_from_phrase(phrase_config, voice_index, phrase_index)]


def _extract_phrase_transform_requests(
    voices_section: list[object],
) -> list[PhraseTransformRequest]:
    """
    Extracts all phrase transform requests from the voices section,
    preserving their structural location.
    """
    return [request for voice_index, voice_config in enumerate(voices_section) for request in _extract_requests_from_voice(voice_config, voice_index)]


def _create_voice_plans_from_document(voices_section: list[object], plan_motifs: dict[str, Motif]) -> list[VoicePlan]:
    """
    Parses voice and phrase configurations, resolving motif references
    to the corresponding Motif instances defined in the score plan.
    """
    voice_plans = []

    for voice_config in voices_section:
        if not isinstance(voice_config, dict):
            raise ValueError("Each voice must be an object.")

        phrase_configs = voice_config.get("phrases", [])
        if not isinstance(phrase_configs, list):
            raise ValueError("Voice 'phrases' must be a list.")

        phrase_plans = []
        for phrase_config in phrase_configs:
            motif_names = _validate_and_extract_motifs(phrase_config)
            phrase_plan_motifs = []
            for name in motif_names:
                if name not in plan_motifs:
                    raise ValueError(f"Motif '{name}' not found in parsed motifs.")
                phrase_plan_motifs.append(plan_motifs[name])
            phrase_plans.append(PhrasePlan(motifs=phrase_plan_motifs))

        voice_plans.append(VoicePlan(phrases=phrase_plans))

    return voice_plans


def generate_score_plan(composition_document: object) -> ScorePlan:
    _validate_composition_structure(composition_document)
    motifs_section, voices_section, score_transforms_section = _extract_composition_sections(composition_document)

    motifs = parse_motifs(motifs_section)
    plan_motifs = {name: Motif(name=name, tones=copy_tones(tones)) for name, tones in motifs.items()}

    voice_plans = _create_voice_plans_from_document(voices_section, plan_motifs)
    phrase_transform_requests = _extract_phrase_transform_requests(voices_section)

    score_transform_requests = []
    for spec in score_transforms_section:
        name, params = parse_transform_spec(spec, TransformLevel.SCORE)
        score_transform_requests.append(ScoreTransformRequest(transform_request=TransformRequest(name=name, params=params)))

    return ScorePlan(
        motifs=plan_motifs,
        voices=voice_plans,
        phrase_transform_requests=phrase_transform_requests,
        score_transform_requests=score_transform_requests,
    )
