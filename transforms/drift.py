from score_model.tone import Tone
from transforms.base import ToneDimension, ToneSequence, parse_dimension


def drift_transform(
    tones: ToneSequence,
    dimension: ToneDimension | str,
    rate: float,
) -> ToneSequence:
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

    resolved_dimension = parse_dimension(dimension)

    if resolved_dimension == ToneDimension.FREQUENCY:
        return _drift_frequency(tones, rate)
    if resolved_dimension == ToneDimension.AMPLITUDE:
        return _drift_amplitude(tones, rate)
    if resolved_dimension == ToneDimension.DURATION:
        return _drift_duration(tones, rate)

    raise ValueError(f"Unsupported dimension for drift: {resolved_dimension}")


def _drift_frequency(tones: ToneSequence, rate: float) -> ToneSequence:
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


def _drift_amplitude(tones: ToneSequence, rate: float) -> ToneSequence:
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


def _drift_duration(tones: ToneSequence, rate: float) -> ToneSequence:
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
