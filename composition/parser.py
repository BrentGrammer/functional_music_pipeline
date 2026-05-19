from composition.schema import CompositionDocument
from composition.score_plan import (
    PhrasePlan,
    PhraseTransformRequest,
    ScorePlan,
    ScoreTransformRequest,
    TransformRequest,
    VoicePlan,
)
from score_model.motif import Motif
from score_model.tone import Tone
from score_model.tone_utils import copy_tones
from transforms.base import (
    TransformLevel,
)


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


def _validate_composition_structure(
    composition_document: object,
) -> CompositionDocument:
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
    for voice_config in voice_configs:
        if not isinstance(voice_config, dict):
            raise ValueError("Composition 'voices' entries must be objects.")

        phrase_configs = voice_config.get("phrases")
        if not isinstance(phrase_configs, list):
            raise ValueError("Voice 'phrases' must be a list.")
        for phrase_config in phrase_configs:
            if not isinstance(phrase_config, dict):
                raise ValueError("Voice 'phrases' entries must be objects.")

            motif_names = phrase_config.get("motifs")
            if not isinstance(motif_names, list):
                raise ValueError("Phrase 'motifs' must be a list.")
            for motif_name in motif_names:
                if not isinstance(motif_name, str):
                    raise ValueError("Phrase 'motifs' entries must be strings.")
                if not motif_name:
                    raise ValueError("Phrase 'motifs' entries must be non-empty strings.")

            transform_configs = phrase_config.get("transforms", [])
            if not isinstance(transform_configs, list):
                raise ValueError("Phrase 'transforms' must be a list.")
            for transform_config in transform_configs:
                if not isinstance(transform_config, dict):
                    raise ValueError("Phrase 'transforms' entries must be objects.")

                transform_name = transform_config.get("name")
                if not isinstance(transform_name, str):
                    raise ValueError("Transform 'name' must be a string.")

                transform_params = transform_config.get("params", {})
                if not isinstance(transform_params, dict):
                    raise ValueError("Transform 'params' must be an object.")

    score_transform_specs = composition_config.get("score_transforms", [])
    if not isinstance(score_transform_specs, list):
        raise ValueError("Composition 'score_transforms' must be a list.")
    for score_transform_spec in score_transform_specs:
        if not isinstance(score_transform_spec, dict):
            raise ValueError("Composition 'score_transforms' entries must be objects.")

        transform_name = score_transform_spec.get("name")
        if not isinstance(transform_name, str):
            raise ValueError("Transform 'name' must be a string.")

        transform_params = score_transform_spec.get("params", {})
        if not isinstance(transform_params, dict):
            raise ValueError("Transform 'params' must be an object.")

    return composition_document


def _extract_composition_sections(
    composition_document: CompositionDocument,
) -> tuple[dict[str, list[str]], list[object], list[object]]:
    """
    Extracts key sections from the composition document.
    Assumes the structure has already been validated.
    """
    motifs_section = composition_document.get("motifs", {})
    composition_config = composition_document.get("composition", {})

    voices_section = composition_config.get("voices", [])
    score_transforms_section = composition_config.get("score_transforms", [])

    return motifs_section, voices_section, score_transforms_section


def _extract_requests_from_phrase(
    phrase_config: object,
    voice_index: int,
    phrase_index: int,
) -> list[PhraseTransformRequest]:
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
    voices_section: object,
) -> list[PhraseTransformRequest]:
    """
    Extracts all phrase transform requests from the voices section,
    preserving their structural location.
    """
    if not isinstance(voices_section, list):
        raise ValueError("Composition 'voices' must be a list.")
    return [request for voice_index, voice_config in enumerate(voices_section) for request in _extract_requests_from_voice(voice_config, voice_index)]


def _create_voice_plans_from_document(voices_section: object, plan_motifs: dict[str, Motif]) -> list[VoicePlan]:
    """
    Parses voice and phrase configurations, resolving motif references
    to the corresponding Motif instances defined in the score plan.
    """
    voice_plans = []

    if not isinstance(voices_section, list):
        raise ValueError("Composition 'voices' must be a list.")

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


def generate_score_plan(document: object) -> ScorePlan:
    composition_document = _validate_composition_structure(document)
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
