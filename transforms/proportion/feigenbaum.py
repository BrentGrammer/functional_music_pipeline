from score_model.math_constants import FEIGENBAUM_DELTA as FEIGENBAUM_RATIO
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from transforms.base import (
    EnumParam,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
    parse_dimension,
)
from transforms.basic.scale import scale_transform

FEIGENBAUM_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
    }
)


def _cumulative_dimension(tones: ToneSequence, dim: ToneDimension) -> float:
    dimension = dim.value
    return float(sum(getattr(t, dimension) for t in tones))


def feigenbaum_sequence(tones: ToneSequence, dimension: ToneDimension | str = ToneDimension.DURATION) -> ToneSequence:
    if not tones:
        return []

    dim = parse_dimension(dimension)
    dim_attr = dim.name.lower()
    new_tones = [tones[0]]

    for tone in tones[1:]:
        previous = getattr(new_tones[-1], dim_attr)
        new_val = previous / FEIGENBAUM_RATIO

        freq = tone.frequency
        dur = tone.duration
        amp = tone.amplitude

        if dim == ToneDimension.FREQUENCY:
            freq = max(1.0, new_val)
        elif dim == ToneDimension.DURATION:
            dur = max(0.0, new_val)
        elif dim == ToneDimension.AMPLITUDE:
            amp = max(0.0, min(1.0, new_val))

        new_tones.append(Tone(frequency=freq, duration=dur, sample_rate=tone.sample_rate, amplitude=amp))

    return new_tones


def phrase_feigenbaum_shrink(
    tones: ToneSequence, previous_tones: ToneSequence, dimension: ToneDimension | str = ToneDimension.DURATION
) -> ToneSequence:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-feigenbaum-shrink: no preceding phrases exist to relate to.")

    dim = parse_dimension(dimension)
    previous = _cumulative_dimension(previous_tones, dim)
    current = _cumulative_dimension(tones, dim)

    if current == 0 or previous == 0:
        return tones

    scale_factor = (previous / FEIGENBAUM_RATIO) / current
    return scale_transform(tones, dim, scale_factor)


def phrase_feigenbaum_grow(
    tones: ToneSequence, previous_tones: ToneSequence, dimension: ToneDimension | str = ToneDimension.DURATION
) -> ToneSequence:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-feigenbaum-grow: no preceding phrases exist to relate to.")

    dim = parse_dimension(dimension)
    previous = _cumulative_dimension(previous_tones, dim)
    current = _cumulative_dimension(tones, dim)

    if current == 0 or previous == 0:
        return tones

    scale_factor = (previous * FEIGENBAUM_RATIO) / current
    return scale_transform(tones, dim, scale_factor)


def score_feigenbaum_sequence(score: Score, dimension: ToneDimension | str = ToneDimension.DURATION) -> Score:
    if not score.voices:
        return score

    if len(score.voices) < 2:
        raise ValueError("score_feigenbaum_sequence requires at least 2 voices to apply a sequence.")

    dim = parse_dimension(dimension)
    new_voices = []
    for i, voice in enumerate(score.voices):
        scale_factor = 1.0 / (FEIGENBAUM_RATIO ** i)
        new_tones = scale_transform(flatten_voice_tones(voice), dim, scale_factor)
        new_voices.append(
            Voice(phrases=[Phrase(motifs=[Motif(name="<feigenbaum>", tones=new_tones)])])
        )

    return Score(new_voices)
