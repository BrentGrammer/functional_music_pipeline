from composition.transform_params_validation import validate_add_pedal_point_params
from score_model.math_constants import FEIGENBAUM_DELTA, GOLDEN_RATIO
from score_model.score import Score
from score_model.tone import Tone
from score_model.tone_utils import copy_tones, make_silence_tone
from score_model.voice import Voice
from transforms.base import (
    EnumParam,
    FloatParam,
    IntegerParam,
    StringParam,
    TransformParamFieldSpec,
    TransformParamsSpec,
)

NAMED_STRETTO_SPACINGS = {
    "golden_ratio": GOLDEN_RATIO,
    "feigenbaum_delta": FEIGENBAUM_DELTA,
}

ADD_PEDAL_POINT_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "frequency": TransformParamFieldSpec(
            schema=FloatParam(),
            required=True,
        ),
        "duration": TransformParamFieldSpec(
            schema=FloatParam(),
            required=True,
        ),
        "amplitude": TransformParamFieldSpec(
            schema=FloatParam(),
        ),
        "mode": TransformParamFieldSpec(
            schema=EnumParam(allowed_values=("sustain", "repeat")),
        ),
        "pulse_duration": TransformParamFieldSpec(
            schema=FloatParam(),
        ),
    },
    validator=validate_add_pedal_point_params,
)
STRETTO_PARAMS_SPEC = TransformParamsSpec(
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


def stretto(
    score: Score,
    parsed_motifs: dict[str, list[Tone]],
    motif: str,
    num_times: int,
    spacing: object,
) -> Score:
    if motif not in parsed_motifs:
        raise ValueError(f"Stretto motif '{motif}' was not found.")
    if num_times < 1:
        raise ValueError("Stretto num_times must be at least 1.")
    motif_duration = _get_motif_duration(parsed_motifs[motif])
    entry_spacing = _resolve_stretto_spacing(spacing, motif_duration)

    generated_voices = []
    for entry_index in range(num_times):
        offset = entry_spacing * entry_index
        entry_tones = copy_tones(parsed_motifs[motif])
        if offset > 0:
            entry_tones = [make_silence_tone(offset)] + entry_tones
        generated_voices.append(Voice(entry_tones))

    return Score(score.voices + generated_voices)


def add_pedal_point(
    score: Score,
    frequency: float,
    duration: float,
    amplitude: float = 0.5,
    mode: str = "sustain",
    pulse_duration: float | None = None,
) -> Score:
    if frequency <= 0:
        raise ValueError("Pedal point frequency must be greater than 0.")
    if duration <= 0:
        raise ValueError("Pedal point duration must be greater than 0.")
    if not 0.0 <= amplitude <= 1.0:
        raise ValueError("Pedal point amplitude must be between 0.0 and 1.0.")

    normalized_mode = mode.lower()
    if normalized_mode == "sustain":
        pedal_tones = [Tone(frequency=frequency, duration=duration, amplitude=amplitude)]
    elif normalized_mode == "repeat":
        pedal_tones = _build_repeated_pedal_tones(frequency, duration, amplitude, pulse_duration)
    else:
        raise ValueError("Pedal point mode must be 'sustain' or 'repeat'.")

    return Score(score.voices + [Voice(pedal_tones)])


def _resolve_stretto_spacing(spacing: object, motif_duration: float) -> float:
    if isinstance(spacing, (int, float)):
        if spacing <= 0:
            raise ValueError("Stretto spacing must be greater than 0 when provided.")
        return float(spacing)

    if isinstance(spacing, str):
        if not spacing:
            raise ValueError("Stretto spacing must be a non-empty string when provided.")
        try:
            return motif_duration / NAMED_STRETTO_SPACINGS[spacing]
        except KeyError as exc:
            raise ValueError(
                "Stretto spacing must be 'golden_ratio', 'feigenbaum_delta', or a positive number."
            ) from exc

    raise ValueError("Stretto spacing must be a string or number when provided.")


def _get_motif_duration(tones: list[Tone]) -> float:
    return sum(tone.duration for tone in tones)


def _build_repeated_pedal_tones(
    frequency: float,
    duration: float,
    amplitude: float,
    pulse_duration: float | None,
) -> list[Tone]:
    if pulse_duration is None:
        raise ValueError("Repeated pedal points require pulse_duration.")
    if pulse_duration <= 0:
        raise ValueError("Pedal point pulse_duration must be greater than 0.")

    pedal_tones: list[Tone] = []
    remaining_duration = duration

    while remaining_duration > 1e-9:
        tone_duration = min(pulse_duration, remaining_duration)
        pedal_tones.append(Tone(frequency=frequency, duration=tone_duration, amplitude=amplitude))
        remaining_duration -= tone_duration

    return pedal_tones
