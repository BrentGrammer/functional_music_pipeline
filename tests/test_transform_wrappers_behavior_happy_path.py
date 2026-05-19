import pytest

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import PhraseTransformContext, ToneDimension
from transforms.basic.delay import delay_phrase_transform, delay_score_transform
from transforms.basic.inversion import invert_phrase_transform, invert_score_transform
from transforms.basic.repeat import repeat_phrase_transform, repeat_score_transform
from transforms.basic.transpose import transpose_phrase_transform, transpose_score_transform
from transforms.complexity.cellular_automata import cellular_automata_phrase_transform, cellular_automata_score_transform
from transforms.complexity.random_drop import random_drop_phrase_transform, random_drop_score_transform
from transforms.complexity.weierstrass import weierstrass_phrase_transform, weierstrass_score_transform
from transforms.geological.terraced_drift import terraced_drift_phrase_transform, terraced_drift_score_transform
from transforms.proportion.feigenbaum import feigenbaum_sequence_phrase_transform, feigenbaum_sequence_score_transform
from transforms.proportion.golden_ratio import (
    golden_ratio_phrase_transform,
    golden_ratio_score_transform,
    phrase_golden_ratio_grow_transform,
    phrase_golden_ratio_shrink_transform,
)


def _make_test_score() -> Score:
    return Score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="a", tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)])]),
                    Phrase(motifs=[Motif(name="b", tones=[Tone(440.0, duration=1.0)])]),
                ]
            ),
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="c", tones=[Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)])])
                ]
            ),
        ]
    )


def test_repeat_phrase_and_score_transform_repeat_observable_output():
    score = _make_test_score()
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    repeated_phrase = repeat_phrase_transform(context, {"count": 2})
    assert len(repeated_phrase.motifs[0].tones) == 6

    repeated_score = repeat_score_transform(score, {"count": 1})
    assert len(repeated_score.voices[0].phrases[0].motifs[0].tones) == 6


def test_transpose_phrase_and_score_transform_transpose_observable_output():
    score = _make_test_score()
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    transposed_phrase = transpose_phrase_transform(context, {"semitones": 12})
    assert transposed_phrase.motifs[0].tones[0].frequency == pytest.approx(440.0)

    transposed_score = transpose_score_transform(score, {"semitones": -12.0})
    assert transposed_score.voices[1].phrases[0].motifs[0].tones[0].frequency == pytest.approx(275.0)


def test_delay_phrase_and_score_transform_delay_observable_output():
    score = _make_test_score()
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=1)

    delayed_phrase = delay_phrase_transform(context, {"seconds": 0.25})
    assert delayed_phrase.motifs[0].tones[0].frequency == 0
    assert delayed_phrase.motifs[0].tones[0].duration == pytest.approx(0.25)

    delayed_score = delay_score_transform(score, {"seconds": 0.1})
    assert delayed_score.voices[0].phrases[0].motifs[0].tones[0].frequency == 0


def test_invert_phrase_and_score_transform_bounds_observable_output():
    score = Score(voices=[Voice(phrases=[Phrase(motifs=[Motif(name="x", tones=[Tone(0.0), Tone(10.0)])])])])
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    inverted_phrase = invert_phrase_transform(context, {"dimension": "frequency"})
    assert inverted_phrase.motifs[0].tones[1].frequency >= 1.0

    inverted_score = invert_score_transform(score, {"dimension": ToneDimension.FREQUENCY})
    assert len(inverted_score.voices[0].phrases[0].motifs[0].tones) == 2


def test_cellular_automata_phrase_and_score_transform_observable_output():
    score = _make_test_score()
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)
    params = {"dimension": "duration", "rule": 30, "generations": 2, "max_deviation": 0.3}

    result_phrase = cellular_automata_phrase_transform(context, params)
    assert len(result_phrase.motifs[0].tones) == 2

    result_score = cellular_automata_score_transform(score, params)
    assert len(result_score.voices) == len(score.voices)


def test_random_drop_phrase_and_score_transform_observable_output():
    score = _make_test_score()
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)
    params = {"dimension": "amplitude", "max_drop_pct": 20, "drop_frequency_pct": 80}

    dropped_phrase = random_drop_phrase_transform(context, params)
    assert len(dropped_phrase.motifs[0].tones) == 2

    dropped_score = random_drop_score_transform(score, params)
    assert len(dropped_score.voices) == len(score.voices)


def test_terraced_drift_phrase_and_score_transform_observable_output():
    score = _make_test_score()
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)
    params = {"dimension": "frequency", "max_step_change_pct": 25}

    drifted_phrase = terraced_drift_phrase_transform(context, params)
    assert len(drifted_phrase.motifs[0].tones) == 2

    drifted_score = terraced_drift_score_transform(score, params)
    assert len(drifted_score.voices) == len(score.voices)


def test_weierstrass_phrase_and_score_transform_observable_output():
    score = _make_test_score()
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)
    params = {"dimension": "frequency", "intensity": "medium"}

    transformed_phrase = weierstrass_phrase_transform(context, params)
    assert len(transformed_phrase.motifs[0].tones) == 2

    transformed_score = weierstrass_score_transform(score, params)
    assert len(transformed_score.voices) == len(score.voices)


def test_golden_ratio_phrase_and_score_transform_previous_phrase_paths():
    score = _make_test_score()
    first_context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)
    second_context = PhraseTransformContext(score=score, voice_index=0, phrase_index=1)
    cross_voice_context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)

    golden_phrase = golden_ratio_phrase_transform(first_context, {"dimension": "duration"})
    assert golden_phrase.motifs[0].tones[0].duration < first_context.phrase.motifs[0].tones[0].duration

    grown = phrase_golden_ratio_grow_transform(second_context, {"dimension": "duration"})
    shrunk = phrase_golden_ratio_shrink_transform(cross_voice_context, {"dimension": "duration"})
    assert len(grown.motifs[0].tones) == len(second_context.phrase.motifs[0].tones)
    assert len(shrunk.motifs[0].tones) == len(cross_voice_context.phrase.motifs[0].tones)

    golden_score = golden_ratio_score_transform(score, {"dimension": "duration"})
    assert len(golden_score.voices) == len(score.voices)


def test_feigenbaum_phrase_and_score_transform_previous_phrase_paths():
    score = _make_test_score()
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)

    seq_phrase = feigenbaum_sequence_phrase_transform(context, {"dimension": "duration"})
    assert len(seq_phrase.motifs[0].tones) == len(context.phrase.motifs[0].tones)

    seq_score = feigenbaum_sequence_score_transform(score, {"dimension": "duration"})
    assert len(seq_score.voices) == len(score.voices)
