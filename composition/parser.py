from composition.schema import (
    CompositionConfig,
    CompositionDocument,
    MotifsConfigInput,
    PhraseConfig,
    TransformConfig,
    VoiceConfig,
)
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
from transforms.base import parse_dimension


def _parse_tone_string(tone_string: str) -> Tone:
    if ":" in tone_string:
        frequency_value, duration_value = tone_string.split(":", 1)
        return Tone(float(frequency_value), duration=float(duration_value))

    return Tone(float(tone_string))


def parse_motifs(motif_definitions: MotifsConfigInput) -> dict[str, list[Tone]]:
    parsed_motifs: dict[str, list[Tone]] = {}

    for motif_name, tone_strings in motif_definitions.items():
        parsed_motifs[motif_name] = [_parse_tone_string(tone_string) for tone_string in tone_strings]

    return parsed_motifs

def _validate_composition_document(
    composition_document: object,
) -> CompositionDocument:
    """
    Validates the structure of the composition document.

    Raises:
        ValueError: If the document structure is invalid.
    """
    if not isinstance(composition_document, dict):
        raise ValueError("Composition document must be an object.")

    motif_definitions = composition_document.get("motifs")
    if not isinstance(motif_definitions, dict):
        raise ValueError("Composition 'motifs' must be an object mapping motif names to tone lists.")
    for motif_name, tone_strings in motif_definitions.items():
        if not isinstance(motif_name, str):
            raise ValueError("Motif names must be strings.")
        if not isinstance(tone_strings, list):
            raise ValueError(f"Motif '{motif_name}' must map to a list of tone strings.")
        for tone_string in tone_strings:
            if not isinstance(tone_string, str):
                raise ValueError(f"Motif '{motif_name}' tone entries must be strings.")
            if not tone_string:
                raise ValueError(f"Motif '{motif_name}' tone entries must be non-empty strings.")

    composition_config = composition_document.get("composition")
    if not isinstance(composition_config, dict):
        raise ValueError("Composition 'composition' must be an object.")
    if not composition_config:
        raise ValueError("Composition 'composition' must not be empty.")

    voice_config_inputs = composition_config.get("voices", [])
    if not isinstance(voice_config_inputs, list):
        raise ValueError("Composition 'voices' must be a list.")
    validated_voices: list[VoiceConfig] = []
    for voice_config in voice_config_inputs:
        if not isinstance(voice_config, dict):
            raise ValueError("Composition 'voices' entries must be objects.")

        phrase_config_inputs = voice_config.get("phrases")
        if not isinstance(phrase_config_inputs, list):
            raise ValueError("Voice 'phrases' must be a list.")
        validated_phrases: list[PhraseConfig] = []
        for phrase_config in phrase_config_inputs:
            if not isinstance(phrase_config, dict):
                raise ValueError("Voice 'phrases' entries must be objects.")

            motif_names = phrase_config.get("motifs")
            if not isinstance(motif_names, list):
                raise ValueError("Phrase 'motifs' must be a list.")
            if not motif_names:
                raise ValueError("Phrase 'motifs' must be a non-empty list.")
            for motif_name in motif_names:
                if not isinstance(motif_name, str):
                    raise ValueError("Phrase 'motifs' entries must be strings.")
                if not motif_name:
                    raise ValueError("Phrase 'motifs' entries must be non-empty strings.")

            transform_config_inputs = phrase_config.get("transforms", [])
            if not isinstance(transform_config_inputs, list):
                raise ValueError("Phrase 'transforms' must be a list.")
            validated_transforms: list[TransformConfig] = []
            for transform_config in transform_config_inputs:
                if not isinstance(transform_config, dict):
                    raise ValueError("Phrase 'transforms' entries must be objects.")

                transform_name = transform_config.get("name")
                if not isinstance(transform_name, str) or not transform_name:
                    raise ValueError("Transform 'name' must be a non-empty string.")

                transform_params = transform_config.get("params", {})
                if not isinstance(transform_params, dict):
                    raise ValueError("Transform 'params' must be an object.")
                if "dimension" in transform_params:
                    transform_params["dimension"] = parse_dimension(
                        str(transform_params["dimension"])
                    )
                validated_transforms.append(
                    TransformConfig(name=transform_name, params=transform_params)
                )

            validated_phrases.append(
                PhraseConfig(motifs=motif_names, transforms=validated_transforms)
            )

        validated_voices.append(VoiceConfig(phrases=validated_phrases))

    score_transform_inputs = composition_config.get("score_transforms", [])
    if not isinstance(score_transform_inputs, list):
        raise ValueError("Composition 'score_transforms' must be a list.")
    validated_score_transforms: list[TransformConfig] = []
    for score_transform_spec in score_transform_inputs:
        if not isinstance(score_transform_spec, dict):
            raise ValueError("Composition 'score_transforms' entries must be objects.")

        transform_name = score_transform_spec.get("name")
        if not isinstance(transform_name, str) or not transform_name:
            raise ValueError("Transform 'name' must be a non-empty string.")

        transform_params = score_transform_spec.get("params", {})
        if not isinstance(transform_params, dict):
            raise ValueError("Transform 'params' must be an object.")
        if "dimension" in transform_params:
            transform_params["dimension"] = parse_dimension(
                str(transform_params["dimension"])
            )
        validated_score_transforms.append(
            TransformConfig(name=transform_name, params=transform_params)
        )

    validated_composition = CompositionConfig(
        voices=validated_voices,
        score_transforms=validated_score_transforms,
    )

    return CompositionDocument(
        motifs=motif_definitions,
        composition=validated_composition,
    )

def _extract_transform_requests_from_phrase(
    phrase_config: PhraseConfig,
    voice_index: int,
    phrase_index: int,
) -> list[PhraseTransformRequest]:
    return [
        PhraseTransformRequest(
            voice_index=voice_index,
            phrase_index=phrase_index,
            transform_request=TransformRequest(name=spec["name"], params=spec["params"]),
        )
        for spec in phrase_config["transforms"]
    ]


def _extract_requests_from_voice(voice_config: VoiceConfig, voice_index: int) -> list[PhraseTransformRequest]:
    return [
        request
        for phrase_index, phrase_config in enumerate(voice_config["phrases"])
        for request in _extract_transform_requests_from_phrase(
            phrase_config,
            voice_index,
            phrase_index,
        )
    ]


def _extract_phrase_transform_requests(
    voices_section: list[VoiceConfig],
) -> list[PhraseTransformRequest]:
    """
    Extracts all phrase transform requests from the voices section,
    preserving their structural location.
    """
    return [
        request
        for voice_index, voice_config in enumerate(voices_section)
        for request in _extract_requests_from_voice(voice_config, voice_index)
    ]


def _create_score_transform_requests(
    score_transforms_section: list[TransformConfig],
) -> list[ScoreTransformRequest]:
    return [
        ScoreTransformRequest(
            transform_request=TransformRequest(name=spec["name"], params=spec["params"])
        )
        for spec in score_transforms_section
    ]


def _create_voice_plans_from_document(
    voices_section: list[VoiceConfig],
    plan_motifs: dict[str, Motif],
) -> list[VoicePlan]:
    """
    Parses voice and phrase configurations, resolving motif references
    to the corresponding Motif instances defined in the score plan.
    """
    voice_plans: list[VoicePlan] = []

    for voice_config in voices_section:
        phrase_configs = voice_config["phrases"]

        phrase_plans: list[PhrasePlan] = []
        for phrase_config in phrase_configs:
            motif_names = phrase_config["motifs"]
            phrase_plan_motifs: list[Motif] = []
            for name in motif_names:
                if name not in plan_motifs:
                    raise ValueError(f"Motif '{name}' not found in parsed motifs.")
                phrase_plan_motifs.append(plan_motifs[name])
            phrase_plans.append(PhrasePlan(motifs=phrase_plan_motifs))

        voice_plans.append(VoicePlan(phrases=phrase_plans))

    return voice_plans


def generate_score_plan(document: object) -> ScorePlan:
    composition_document = _validate_composition_document(document)
    motifs_section = composition_document["motifs"]
    composition_config = composition_document["composition"]
    voices_section = composition_config["voices"]
    score_transforms_section = composition_config["score_transforms"]

    motifs = parse_motifs(motifs_section)
    plan_motifs = {name: Motif(name=name, tones=copy_tones(tones)) for name, tones in motifs.items()}

    voice_plans = _create_voice_plans_from_document(voices_section, plan_motifs)
    phrase_transform_requests = _extract_phrase_transform_requests(voices_section)
    score_transform_requests = _create_score_transform_requests(score_transforms_section)

    return ScorePlan(
        motifs=plan_motifs,
        voices=voice_plans,
        phrase_transform_requests=phrase_transform_requests,
        score_transform_requests=score_transform_requests,
    )
