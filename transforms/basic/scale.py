from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import MINIMUM_FREQUENCY_HZ, Tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import (
    FloatParam,
    ParsedTransformParams,
    PhraseTransformContext,
    ToneDimension,
    ToneDimensionParam,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
)


@dataclass(frozen=True)
class ScaleParams:
    dimension: ToneDimension
    factor: float


def _create_scale_params(parsed_params: ParsedTransformParams) -> ScaleParams:
    return ScaleParams(
        dimension=parsed_params.required("dimension", ToneDimension),
        factor=parsed_params.required("factor", float),
    )


SCALE_PARAMS_SPEC = TransformParamsSpec[ScaleParams](
    params_factory=_create_scale_params,
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=ToneDimensionParam(),
        ),
        "factor": TransformParamFieldSpec(
            schema=FloatParam(),
            required=True,
        ),
    }
)


def scale_transform(tones: ToneSequence, dimension: ToneDimension, factor: float) -> ToneSequence:
    """
    Scales a specific dimension of a tone sequence by a given factor.
    """
    if not tones:
        return []

    result = []
    for t in tones:
        if dimension == ToneDimension.FREQUENCY:
            new_val = max(MINIMUM_FREQUENCY_HZ, t.frequency * factor)
            result.append(Tone(new_val, t.duration, t.sample_rate, t.amplitude))
        elif dimension == ToneDimension.DURATION:
            new_val = max(0.0, t.duration * factor)
            result.append(Tone(t.frequency, new_val, t.sample_rate, t.amplitude))
        elif dimension == ToneDimension.AMPLITUDE:
            new_val = max(0.0, min(1.0, t.amplitude * factor))
            result.append(Tone(t.frequency, t.duration, t.sample_rate, new_val))
            
    return result


def scale_phrase_transform(context: PhraseTransformContext, params: ScaleParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    scaled_tones = scale_transform(phrase_tones, dimension=params.dimension, factor=params.factor)
    return Phrase(motifs=[Motif(name="<transformed>", tones=scaled_tones)])


def scale_score_transform(score: Score, params: ScaleParams) -> Score:
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        scaled_tones = scale_transform(voice_tones, dimension=params.dimension, factor=params.factor)
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=scaled_tones)])]))

    return Score(voices=new_voices)
