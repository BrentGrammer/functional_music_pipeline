import math

CENTS_PER_OCTAVE = 1200.0
SEMITONES_PER_OCTAVE = 12.0
CENTS_PER_SEMITONE = CENTS_PER_OCTAVE / SEMITONES_PER_OCTAVE


def cents_to_frequency(reference_frequency: float, cents: float) -> float:
    """Calculates the frequency that is a specific number of cents away from a reference frequency."""
    if reference_frequency <= 0:
        raise ValueError("Reference frequency must be greater than zero.")
    return reference_frequency * (2 ** (cents / CENTS_PER_OCTAVE))


def semitones_to_frequency(reference_frequency: float, semitones: float) -> float:
    """Calculates the frequency that is a specific number of semitones away from a reference frequency."""
    if reference_frequency <= 0:
        raise ValueError("Reference frequency must be greater than zero.")
    return reference_frequency * (2 ** (semitones / SEMITONES_PER_OCTAVE))


def frequency_to_cents(frequency: float, reference_frequency: float) -> float:
    """Calculates the distance in cents between two frequencies."""
    if frequency <= 0 or reference_frequency <= 0:
        raise ValueError("Frequencies must be greater than zero.")
    return CENTS_PER_OCTAVE * math.log2(frequency / reference_frequency)


def frequency_to_semitones(frequency: float, reference_frequency: float) -> float:
    """Calculates the distance in semitones between two frequencies."""
    if frequency <= 0 or reference_frequency <= 0:
        raise ValueError("Frequencies must be greater than zero.")
    return SEMITONES_PER_OCTAVE * math.log2(frequency / reference_frequency)
