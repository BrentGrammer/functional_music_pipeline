from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import (
    FloatParam,
    ParsedTransformParams,
    PhraseTransformContext,
    ToneDimension,
    ToneDimensionParam,
    TransformParamFieldSpec,
    TransformParamsSpec,
)


@dataclass(frozen=True)
class DriftParams:
    dimension: ToneDimension
    rate: float


def _create_drift_params(parsed_params: ParsedTransformParams) -> DriftParams:
    return DriftParams(
        dimension=parsed_params.required("dimension", ToneDimension),
        rate=parsed_params.required("rate", float),
    )


DRIFT_PARAMS_SPEC = TransformParamsSpec[DriftParams](
    params_factory=_create_drift_params,
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=ToneDimensionParam(),
        ),
        "rate": TransformParamFieldSpec(
            schema=FloatParam(),
            required=True,
        ),
    }
)


def drift_transform(
    tones: list[Tone],
    dimension: ToneDimension,
    rate: float,
) -> list[Tone]:
    """
    Applies a progressive, linear drift to a specific dimension of the phrase.

    This transform shifts the entire phrase by a calculated step, creating a
    "tilt" or "slope". The first tone serves as the reference for the step size.

    Note on timing: The drift is applied immediately starting from the first
    tone (i.e., the first output tone is already shifted by one step). This
    produces a pronounced pitch, volume, or duration shift from the very start
    of the phrase, rather than easing into the effect.

    Rate direction by dimension:
    - FREQUENCY: Positive = upward glissando; Negative = downward glissando.
    - AMPLITUDE: Positive = Crescendo (growing louder); Negative = Diminuendo (fading).
    - DURATION:  Positive = Ritardando (slowing, tones grow longer);
                 Negative = Accelerando (quickening, tones grow shorter).
    - Zero rate on any dimension is an identity (no change).

    Example (Frequency, Rate = 0.1):
        Input: [440, 440, 440]
        Step: 44
        Result: [484, 528, 572]
    """
    if not tones:
        return []

    if dimension == ToneDimension.FREQUENCY:
        return _drift_frequency(tones, rate)
    if dimension == ToneDimension.AMPLITUDE:
        return _drift_amplitude(tones, rate)
    if dimension == ToneDimension.DURATION:
        return _drift_duration(tones, rate)

    raise ValueError(f"Invalid dimension: {dimension}. Must be one of {', '.join(d.value for d in ToneDimension)}")


def drift_phrase_transform(context: PhraseTransformContext, params: DriftParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    drifted_tones = drift_transform(phrase_tones, dimension=params.dimension, rate=params.rate)
    return Phrase(motifs=[Motif(name="<transformed>", tones=drifted_tones)])


def drift_score_transform(score: Score, params: DriftParams) -> Score:
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        drifted_tones = drift_transform(voice_tones, dimension=params.dimension, rate=params.rate)
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=drifted_tones)])]))

    return Score(voices=new_voices)


def _drift_frequency(tones: list[Tone], rate: float) -> list[Tone]:
    """
    Applies a progressive drift to frequency (Glissando).
    """
    base_frequency = tones[0].frequency
    step = base_frequency * rate
    result: list[Tone] = []

    for i, tone in enumerate(tones):
        new_frequency = tone.frequency + (step * (i + 1))
        result.append(Tone(new_frequency, tone.duration, tone.sample_rate, tone.amplitude))

    return result


def _drift_amplitude(tones: list[Tone], rate: float) -> list[Tone]:
    """
    Applies a progressive drift to amplitude (Crescendo/Diminuendo).
    """
    base_amplitude = tones[0].amplitude
    step = base_amplitude * rate
    result: list[Tone] = []

    for i, tone in enumerate(tones):
        new_amplitude = tone.amplitude + (step * (i + 1))
        clamped_amplitude = max(0.0, min(1.0, new_amplitude))
        result.append(Tone(tone.frequency, tone.duration, tone.sample_rate, clamped_amplitude))

    return result


def _drift_duration(tones: list[Tone], rate: float) -> list[Tone]:
    """
    Applies a progressive drift to duration.

    Positive rate = Ritardando (each tone grows longer, music slows down).
    Negative rate = Accelerando (each tone grows shorter, music speeds up).
    """
    base_duration = tones[0].duration
    step = base_duration * rate
    result: list[Tone] = []

    for i, tone in enumerate(tones):
        new_duration = tone.duration + (step * (i + 1))
        safe_duration = max(0.0, new_duration)
        result.append(Tone(tone.frequency, safe_duration, tone.sample_rate, tone.amplitude))

    return result
