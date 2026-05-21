import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import PhraseTransformContext
from transforms.basic.delay import DelayParams, delay_phrase_transform, delay_score_transform, delay_tones
from transforms.basic.pad_silence import pad_silence_phrase_transform, pad_silence_score_transform, pad_silence_tones


def test_delay_zero():
    """Zero delay should return original tones."""
    tones = [Tone(440.0), Tone(523.25)]
    result = delay_tones(tones, seconds=0)
    assert len(result) == 2
    assert result[0].frequency == pytest.approx(440.0)
    assert result[1].frequency == pytest.approx(523.25)

def test_delay_positive():
    """Positive delay should prepend a silent tone."""
    tones = [Tone(440.0, duration=0.5), Tone(523.25, duration=0.3)]
    delay_time = 0.2
    result = delay_tones(tones, seconds=delay_time)
    
    expected_length = len(tones) + 1
    assert len(result) == expected_length
    
    assert result[0].frequency == 0
    assert result[0].amplitude == 0
    assert result[0].duration == pytest.approx(delay_time)
    
    assert result[1].frequency == pytest.approx(440.0)
    assert result[1].duration == pytest.approx(0.5)
    assert result[2].frequency == pytest.approx(523.25)
    assert result[2].duration == pytest.approx(0.3)

def test_delay_negative():
    """Negative delay should raise ValueError."""
    tones = [Tone(440.0)]
    with pytest.raises(ValueError, match="Delay must be non-negative. Negative offsets are not supported."):
        delay_tones(tones, seconds=-0.5)

def test_delay_preserves_amplitude():
    """Delay should preserve amplitude of original tones."""
    tones = [Tone(440.0, amplitude=0.3), Tone(523.25, amplitude=0.7)]
    result = delay_tones(tones, seconds=0.1)
    
    assert len(result) == 3
    assert result[0].amplitude == 0
    assert result[1].amplitude == pytest.approx(0.3)
    assert result[2].amplitude == pytest.approx(0.7)

def test_delay_generates_silence():
    """The silent tone should generate actual silence (all zeros)."""
    delay_time = 0.1
    silent_tone = Tone(frequency=0, duration=delay_time, amplitude=0)
    wave = silent_tone.generate_tone()
    
    assert np.all(wave == 0)
    expected_length = int(silent_tone.sample_rate * delay_time)
    assert len(wave) == expected_length

def test_delay_empty_list():
    """Delaying an empty tone list should still prepend a silent tone."""
    result = delay_tones([], seconds=0.5)
    assert len(result) == 1
    assert result[0].frequency == 0
    assert result[0].duration == pytest.approx(0.5)


def test_delay_tones_matches_pad_silence_start():
    '''delay is just a convenience wrapper that uses pad silence transform'''
    tones = [Tone(440.0, duration=0.5, amplitude=0.3), Tone(523.25, duration=0.3, amplitude=0.7)]

    delayed_tones = delay_tones(tones, seconds=0.2)
    padded_tones = pad_silence_tones(tones, seconds=0.2, position="start")

    assert len(delayed_tones) == len(padded_tones)
    for delayed_tone, padded_tone in zip(delayed_tones, padded_tones):
        assert delayed_tone.frequency == pytest.approx(padded_tone.frequency)
        assert delayed_tone.duration == pytest.approx(padded_tone.duration)
        assert delayed_tone.amplitude == pytest.approx(padded_tone.amplitude)


def test_delay_phrase_transform_matches_pad_silence_start():
    score = Score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="phrase-target",
                                tones=[Tone(440.0, duration=0.5), Tone(523.25, duration=0.3)],
                            )
                        ]
                    )
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    delay_seconds = 0.2
    delayed_phrase = delay_phrase_transform(context, DelayParams(seconds=delay_seconds))
    padded_phrase = pad_silence_phrase_transform(context, {"seconds": delay_seconds, "position": "start"})

    assert len(delayed_phrase.motifs) == len(padded_phrase.motifs)
    assert len(delayed_phrase.motifs[0].tones) == len(padded_phrase.motifs[0].tones)
    for delayed_tone, padded_tone in zip(delayed_phrase.motifs[0].tones, padded_phrase.motifs[0].tones):
        assert delayed_tone.frequency == pytest.approx(padded_tone.frequency)
        assert delayed_tone.duration == pytest.approx(padded_tone.duration)
        assert delayed_tone.amplitude == pytest.approx(padded_tone.amplitude)


def test_delay_score_transform_matches_pad_silence_start():
    score = Score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="voice-a", tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.25)])])
                ]
            ),
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="voice-b", tones=[Tone(440.0, duration=1.0)])])
                ]
            ),
        ]
    )

    delay_seconds = 0.2
    delayed_score = delay_score_transform(score, DelayParams(seconds=delay_seconds))
    padded_score = pad_silence_score_transform(score, {"seconds": delay_seconds, "position": "start"})

    assert len(delayed_score.voices) == len(padded_score.voices)
    for delayed_voice, padded_voice in zip(delayed_score.voices, padded_score.voices):
        delayed_tones = delayed_voice.phrases[0].motifs[0].tones
        padded_tones = padded_voice.phrases[0].motifs[0].tones
        assert len(delayed_tones) == len(padded_tones)
        for delayed_tone, padded_tone in zip(delayed_tones, padded_tones):
            assert delayed_tone.frequency == pytest.approx(padded_tone.frequency)
            assert delayed_tone.duration == pytest.approx(padded_tone.duration)
            assert delayed_tone.amplitude == pytest.approx(padded_tone.amplitude)
