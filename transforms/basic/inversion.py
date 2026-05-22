from collections.abc import Mapping
from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import MINIMUM_FREQUENCY_HZ, Tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import PhraseTransformContext, ToneDimension, ToneDimensionParam, ToneSequence, TransformParamFieldSpec, TransformParamsSpec


@dataclass(frozen=True)
class InvertParams:
    dimension: ToneDimension


def _create_invert_params(parsed_params: Mapping[str, object]) -> InvertParams:
    dimension = parsed_params.get("dimension")
    if not isinstance(dimension, ToneDimension):
        raise ValueError("Invert params were not parsed before construction.")

    return InvertParams(dimension=dimension)


INVERT_PARAMS_SPEC = TransformParamsSpec[InvertParams](
    params_factory=_create_invert_params,
    fields={
        "dimension": TransformParamFieldSpec(
            schema=ToneDimensionParam(),
            default=ToneDimension.FREQUENCY,
        ),
    }
)


def _copy_tone(tone: Tone) -> Tone:
    return Tone(tone.frequency, tone.duration, tone.sample_rate, tone.amplitude)


def _invert_frequency_tone(tone: Tone, first_tone: Tone) -> Tone:
    interval = tone.frequency / first_tone.frequency if first_tone.frequency != 0 else 1.0
    new_value = first_tone.frequency / interval if interval != 0 else tone.frequency
    return Tone(max(MINIMUM_FREQUENCY_HZ, new_value), tone.duration, tone.sample_rate, tone.amplitude)


def _invert_duration_tone(tone: Tone, first_tone: Tone) -> Tone:
    interval = tone.duration / first_tone.duration if first_tone.duration != 0 else 1.0
    new_value = first_tone.duration / interval if interval != 0 else tone.duration
    return Tone(tone.frequency, max(0.0, new_value), tone.sample_rate, tone.amplitude)


def _invert_amplitude_tone(tone: Tone, first_tone: Tone) -> Tone:
    interval = tone.amplitude / first_tone.amplitude if first_tone.amplitude != 0 else 1.0
    new_value = first_tone.amplitude / interval if interval != 0 else tone.amplitude
    return Tone(tone.frequency, tone.duration, tone.sample_rate, max(0.0, min(1.0, new_value)))


INVERT_TONE_STRATEGIES = {
    ToneDimension.FREQUENCY: _invert_frequency_tone,
    ToneDimension.DURATION: _invert_duration_tone,
    ToneDimension.AMPLITUDE: _invert_amplitude_tone,
}


def invert_tones(tones: ToneSequence, dimension: ToneDimension = ToneDimension.FREQUENCY) -> ToneSequence:
    if len(tones) <= 1:
        return tones[:]

    first_tone = tones[0]
    inverted_tones = [_copy_tone(first_tone)]
    invert_tone = INVERT_TONE_STRATEGIES[dimension]

    for tone in tones[1:]:
        inverted_tones.append(invert_tone(tone, first_tone))

    return inverted_tones


def invert_phrase_transform(context: PhraseTransformContext, params: InvertParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    inverted_tones = invert_tones(phrase_tones, dimension=params.dimension)
    return Phrase(motifs=[Motif(name="<transformed>", tones=inverted_tones)])


def invert_score_transform(score: Score, params: InvertParams) -> Score:
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        inverted_tones = invert_tones(voice_tones, dimension=params.dimension)
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=inverted_tones)])]))

    return Score(voices=new_voices)
