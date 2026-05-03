from score_model.tone import Tone


def make_silence_tone(duration: float) -> Tone:
    return Tone(frequency=0, duration=duration, amplitude=0)


def copy_tone(tone: Tone) -> Tone:
    return Tone(
        frequency=tone.frequency,
        duration=tone.duration,
        sample_rate=tone.sample_rate,
        amplitude=tone.amplitude,
    )


def copy_tones(tones: list[Tone]) -> list[Tone]:
    return [copy_tone(tone) for tone in tones]
