from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import EnumParam, PhraseTransformContext, ToneDimension, ToneSequence, TransformParamFieldSpec, TransformParamsSpec, parse_dimension

INVERT_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
    }
)


def _copy_tone(tone: Tone) -> Tone:
    return Tone(tone.frequency, tone.duration, tone.sample_rate, tone.amplitude)


def _invert_frequency_tone(tone: Tone, first_tone: Tone) -> Tone:
    interval = tone.frequency / first_tone.frequency if first_tone.frequency != 0 else 1.0
    new_value = first_tone.frequency / interval if interval != 0 else tone.frequency
    return Tone(max(1.0, new_value), tone.duration, tone.sample_rate, tone.amplitude)


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


def invert_tones(tones: ToneSequence, dimension: ToneDimension | str = ToneDimension.FREQUENCY) -> ToneSequence:
    if len(tones) <= 1:
        return tones[:]

    dim = parse_dimension(dimension)
    first_tone = tones[0]
    inverted_tones = [_copy_tone(first_tone)]
    invert_tone = INVERT_TONE_STRATEGIES[dim]

    for tone in tones[1:]:
        inverted_tones.append(invert_tone(tone, first_tone))

    return inverted_tones


def invert_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    del params # TODO: come back to this - this is a smell.

    phrase_tones = flatten_phrase_tones(context.phrase)
    inverted_tones = invert_tones(phrase_tones)
    return Phrase(motifs=[Motif(name="<transformed>", tones=inverted_tones)])


def invert_score_transform(score: Score, params: Mapping[str, object]) -> Score:
    del params

    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        inverted_tones = invert_tones(voice_tones)
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=inverted_tones)])]))

    return Score(voices=new_voices)
