from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones
from transforms.base import (
    EnumParam,
    PhraseTransformContext,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
    parse_dimension,
)

EROSION_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
    }
)


def erosion_transform(
    tones: ToneSequence,
    dimension: ToneDimension | str = ToneDimension.DURATION,
) -> ToneSequence:
    """
    Mimics geological erosion, gradually wearing down a musical phrase.
    
    This transform applies a specific decay logic depending on the chosen dimension:
    - DURATION: Iteratively shortens the phrase, removing the last tone and repeating 
      the remainder until only the first tone remains.
    - AMPLITUDE: Applies a linear fade-out, preserving the structure but dissolving 
      the sound into silence.
    - FREQUENCY: Collapses the melody, pulling all pitches towards the first tone 
      until the phrase settles on a single repeated note.
    """
    if not tones:
        return []

    resolved_dimension = parse_dimension(dimension)

    if resolved_dimension == ToneDimension.DURATION:
        return _erode_duration(tones)
    elif resolved_dimension == ToneDimension.AMPLITUDE:
        return _erode_amplitude(tones)
    elif resolved_dimension == ToneDimension.FREQUENCY:
        return _erode_frequency(tones)

    return list(tones)


def erosion_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    dimension = params.get("dimension", ToneDimension.DURATION)
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Erosion dimension must be a string or ToneDimension.")

    phrase_tones = flatten_phrase_tones(context.phrase)
    transformed_tones = erosion_transform(phrase_tones, dimension=dimension)
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def _erode_duration(tones: ToneSequence) -> ToneSequence:
    """
    Performs structural erosion on the duration of the phrase.
    
    Musically, this acts like a "crumbling" structure. It iteratively removes the 
    last tone of the sequence and appends the remaining fragment to the result. 
    This process repeats until only the first tone remains.
    
    Example:
        Input: [A, B, C]
        Pass 1: Remove C -> [A, B]
        Pass 2: Remove B -> [A]
        Result: [A, B, A]
    """
    result: list[Tone] = []
    current_sequence = list(tones)

    while len(current_sequence) > 1:
        current_sequence.pop()
        result.extend(current_sequence)

    return result


def _erode_amplitude(tones: ToneSequence) -> ToneSequence:
    """
    Performs volumetric erosion on the amplitude of the phrase.
    
    Musically, this acts like a "dissipating echo". It applies a linear fade-out 
    across the sequence. The first tone retains its full volume, while the last 
    tone fades to silence.
    
    Example:
        Input: [Loud, Loud, Loud]
        Result: [Loud, Medium, Silence]
    """
    num_tones = len(tones)
    if num_tones == 1:
        return [Tone(tones[0].frequency, tones[0].duration, tones[0].sample_rate, tones[0].amplitude)]

    result: list[Tone] = []
    for i, tone in enumerate(tones):
        # Scale factor: 1.0 at start, 0.0 at end
        scale = 1.0 - (i / (num_tones - 1))
        new_amplitude = tone.amplitude * scale
        result.append(Tone(tone.frequency, tone.duration, tone.sample_rate, new_amplitude))
    
    return result


def _erode_frequency(tones: ToneSequence) -> ToneSequence:
    """
    Performs pitch erosion on the frequency of the phrase.
    
    Musically, this acts like a "settling" pile of sand. It gradually pulls all 
    tones towards the frequency of the first tone. The melody collapses into a 
    unison, with the last tone becoming identical in pitch to the first.
    
    Example:
        Input: [C, E, G]
        Result: [C, D, C] (E and G slide towards C)
    """
    num_tones = len(tones)
    if num_tones == 1:
        return [Tone(tones[0].frequency, tones[0].duration, tones[0].sample_rate, tones[0].amplitude)]

    target_frequency = tones[0].frequency
    result: list[Tone] = []

    for i, tone in enumerate(tones):
        if i == 0:
            result.append(Tone(tone.frequency, tone.duration, tone.sample_rate, tone.amplitude))
            continue

        # Linear interpolation factor: 0.0 at start, 1.0 at end
        factor = i / (num_tones - 1)
        new_frequency = (tone.frequency * (1 - factor)) + (target_frequency * factor)
        
        result.append(Tone(new_frequency, tone.duration, tone.sample_rate, tone.amplitude))

    return result
