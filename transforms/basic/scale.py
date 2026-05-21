from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import (
    EnumParam,
    FloatParam,
    PhraseTransformContext,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
)

SCALE_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
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
            new_val = max(1.0, t.frequency * factor)
            result.append(Tone(new_val, t.duration, t.sample_rate, t.amplitude))
        elif dimension == ToneDimension.DURATION:
            new_val = max(0.0, t.duration * factor)
            result.append(Tone(t.frequency, new_val, t.sample_rate, t.amplitude))
        elif dimension == ToneDimension.AMPLITUDE:
            new_val = max(0.0, min(1.0, t.amplitude * factor))
            result.append(Tone(t.frequency, t.duration, t.sample_rate, new_val))
            
    return result


def scale_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    dimension = params["dimension"]

    factor = params["factor"]
    if isinstance(factor, bool) or not isinstance(factor, (int, float)):
        raise ValueError("Param 'factor' must be a float.")

    phrase_tones = flatten_phrase_tones(context.phrase)
    scaled_tones = scale_transform(phrase_tones, dimension=dimension, factor=float(factor))
    return Phrase(motifs=[Motif(name="<transformed>", tones=scaled_tones)])


def scale_score_transform(score: Score, params: Mapping[str, object]) -> Score:
    dimension = params["dimension"]

    factor = params["factor"]
    if isinstance(factor, bool) or not isinstance(factor, (int, float)):
        raise ValueError("Param 'factor' must be a float.")

    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        scaled_tones = scale_transform(voice_tones, dimension=dimension, factor=float(factor))
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=scaled_tones)])]))

    return Score(voices=new_voices)
