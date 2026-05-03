from score_model.tone import Tone
from score_model.tone_utils import copy_tones


def test_copy_tones_returns_new_tone_objects():
    original_tone = Tone(440.0, duration=0.5, amplitude=0.25)
    original_tones = [original_tone]

    copied_tones = copy_tones(original_tones)

    assert copied_tones is not original_tones
    assert copied_tones[0] is not original_tone
    assert copied_tones[0].frequency == original_tone.frequency
    assert copied_tones[0].duration == original_tone.duration
    assert copied_tones[0].sample_rate == original_tone.sample_rate
    assert copied_tones[0].amplitude == original_tone.amplitude
