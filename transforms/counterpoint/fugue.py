from dataclasses import dataclass

from score_model.math_constants import FEIGENBAUM_DELTA, GOLDEN_RATIO
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.tone_utils import copy_tones, make_silence_tone
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from transforms.base import (
    EnumParam,
    FloatParam,
    IntegerParam,
    ParsedTransformParams,
    StringParam,
    TransformParamFieldSpec,
    TransformParamsSpec,
)

NAMED_STRETTO_SPACINGS = {
    "golden_ratio": GOLDEN_RATIO,
    "feigenbaum_delta": FEIGENBAUM_DELTA,
}


@dataclass(frozen=True)
class AddPedalToneParams:
    frequency: float


@dataclass(frozen=True)
class StrettoParams:
    motif: str
    num_times: int
    spacing: str | float


def _create_add_pedal_tone_params(parsed_params: ParsedTransformParams) -> AddPedalToneParams:
    return AddPedalToneParams(frequency=parsed_params.required("frequency", float))


def _create_stretto_params(parsed_params: ParsedTransformParams) -> StrettoParams:
    spacing = parsed_params.values["spacing"]
    if not isinstance(spacing, (str, float)):
        raise TypeError("Parsed transform param 'spacing' violated its schema contract.")
    return StrettoParams(
        motif=parsed_params.required("motif", str),
        num_times=parsed_params.required("num_times", int),
        spacing=spacing,
    )


ADD_PEDAL_TONE_PARAMS_SPEC = TransformParamsSpec[AddPedalToneParams](
    params_factory=_create_add_pedal_tone_params,
    fields={
        "frequency": TransformParamFieldSpec(
            schema=FloatParam(),
            required=True,
        ),
    }
)
STRETTO_PARAMS_SPEC = TransformParamsSpec[StrettoParams](
    params_factory=_create_stretto_params,
    fields={
        "motif": TransformParamFieldSpec(
            schema=StringParam(),
            required=True,
        ),
        "num_times": TransformParamFieldSpec(
            schema=IntegerParam(),
            required=True,
        ),
        "spacing": TransformParamFieldSpec(
            required=True,
            schema=(EnumParam(allowed_values=tuple(NAMED_STRETTO_SPACINGS)), FloatParam()),
        ),
    }
)


def find_motif_by_name(score: Score, name: str) -> Motif | None:
    return next((
        motif
        for voice in score.voices
        for phrase in voice.phrases
        for motif in phrase.motifs
        if motif.name == name
    ), None)


def stretto(
    score: Score,
    motif: str,
    num_times: int,
    spacing: object,
) -> Score:
    if num_times < 1:
        raise ValueError("Stretto num_times must be at least 1.")

    target_motif = find_motif_by_name(score, motif)
    if target_motif is None:
        raise ValueError(f"Stretto motif '{motif}' was not found in score.")

    target_motif_tones = target_motif.tones
    target_tones_total_duration = sum(tone.duration for tone in target_motif_tones)
    entry_spacing = _calculate_entry_spacing(spacing, target_tones_total_duration)

    generated_voices = []
    for entry_index in range(num_times):
        offset = entry_spacing * entry_index
        entry_tones = copy_tones(target_motif_tones)
        if offset > 0:
            entry_tones = [make_silence_tone(offset)] + entry_tones
        generated_voices.append(
            Voice(phrases=[Phrase(motifs=[Motif(name=motif, tones=entry_tones)])])
        )

    return Score(score.voices + generated_voices)


def add_pedal_tone(
    score: Score,
    frequency: float,
) -> Score:
    if frequency <= 0:
        raise ValueError("Pedal tone frequency must be greater than 0.")

    duration = 0.0
    for voice in score.voices:
        voice_duration = sum(tone.duration for tone in flatten_voice_tones(voice))
        duration = max(duration, voice_duration)

    if duration <= 0:
        duration = 1.0  # Fallback if score is empty

    amplitude = 0.5  # Fixed sensible default
    pedal_tones = [Tone(frequency=frequency, duration=duration, amplitude=amplitude)]
    return Score(
        score.voices + [Voice(phrases=[Phrase(motifs=[Motif(name="<pedal>", tones=pedal_tones)])])]
    )


def add_pedal_tone_score_transform(score: Score, params: AddPedalToneParams) -> Score:
    return add_pedal_tone(score, frequency=params.frequency)


def stretto_score_transform(score: Score, params: StrettoParams) -> Score:
    if find_motif_by_name(score, params.motif) is None:
        raise ValueError(f"Stretto motif '{params.motif}' was not found in score.")

    return stretto(
        score,
        motif=params.motif,
        num_times=params.num_times,
        spacing=params.spacing,
    )


def stretto_score_transform_adapter(score: Score, params: StrettoParams) -> Score:
    """Adapter kept for registry compatibility; delegates to stretto_score_transform.

    This named adapter gives the registry a stable callable object to reference
    instead of relying on inline lambdas.
    """
    return stretto_score_transform(score, params)


def _calculate_entry_spacing(spacing: object, target_tones_total_duration: float) -> float:
    if isinstance(spacing, (int, float)):
        if spacing <= 0:
            raise ValueError("Stretto spacing must be greater than 0 when provided.")
        return float(spacing)

    if isinstance(spacing, str):
        if not spacing:
            raise ValueError("Stretto spacing must be a non-empty string when provided.")
        try:
            return target_tones_total_duration / NAMED_STRETTO_SPACINGS[spacing]
        except KeyError as exc:
            raise ValueError(
                "Stretto spacing must be 'golden_ratio', 'feigenbaum_delta', or a positive number."
            ) from exc

    raise ValueError("Stretto spacing must be a string or number when provided.")
