import pytest

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import MINIMUM_FREQUENCY_HZ, Tone
from score_model.voice import Voice
from transforms.base import PhraseTransformContext, ToneDimension
from transforms.basic.delay import DelayParams, delay_phrase_transform, delay_score_transform
from transforms.basic.inversion import InvertParams, invert_phrase_transform, invert_score_transform
from transforms.basic.repeat import RepeatParams, repeat_phrase_transform, repeat_score_transform
from transforms.basic.transpose import TransposeParams, transpose_phrase_transform, transpose_score_transform
from transforms.complexity.cellular_automata import CellularAutomataParams, cellular_automata_phrase_transform, cellular_automata_score_transform
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


def _make_test_score(*, voices: list[Voice] | None = None) -> Score:
    if voices is not None:
        return Score(voices=voices)
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
    phrase_tones = [Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)]
    phrase_score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="repeat-target",
                                tones=phrase_tones,
                            )
                        ]
                    )
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=phrase_score, voice_index=0, phrase_index=0)

    phrase_repeat_count = 2
    repeated_phrase = repeat_phrase_transform(context, RepeatParams(count=phrase_repeat_count))
    original_phrase_tone_count_plus_repeats = len(phrase_tones) + (len(phrase_tones) * phrase_repeat_count)
    assert len(repeated_phrase.motifs[0].tones) == original_phrase_tone_count_plus_repeats

    score_repeat_count = 1
    score_tones = [Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)]
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="repeat-target",
                                tones=score_tones,
                            )
                        ]
                    )
                ]
            )
        ]
    )
    repeated_score = repeat_score_transform(score, RepeatParams(count=score_repeat_count))

    original_score_tone_count_plus_repeats = len(score_tones) + (len(score_tones) * score_repeat_count)
    assert len(repeated_score.voices[0].phrases[0].motifs[0].tones) == original_score_tone_count_plus_repeats


def test_transpose_phrase_and_score_transform_transpose_observable_output():
    phrase_starting_frequency = 220.0
    phrase_upper_neighbor_frequency = 330.0
    score_starting_frequency = 550.0
    score_upper_neighbor_frequency = 660.0
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="phrase-target",
                                tones=[
                                    Tone(phrase_starting_frequency, duration=0.5),
                                    Tone(phrase_upper_neighbor_frequency, duration=0.5),
                                ],
                            )
                        ]
                    )
                ]
            ),
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="score-target",
                                tones=[
                                    Tone(score_starting_frequency, duration=0.25),
                                    Tone(score_upper_neighbor_frequency, duration=0.25),
                                ],
                            )
                        ]
                    )
                ]
            ),
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    phrase_octave_up = 12
    transposed_phrase = transpose_phrase_transform(context, TransposeParams(semitones=phrase_octave_up))
    expected_phrase_frequency_one_octave_up = phrase_starting_frequency * 2
    assert transposed_phrase.motifs[0].tones[0].frequency == pytest.approx(expected_phrase_frequency_one_octave_up)

    score_octave_down = -12.0
    transposed_score = transpose_score_transform(score, TransposeParams(semitones=score_octave_down))
    expected_score_frequency_one_octave_down = score_starting_frequency / 2
    assert transposed_score.voices[1].phrases[0].motifs[0].tones[0].frequency == pytest.approx(expected_score_frequency_one_octave_down)


def test_delay_phrase_and_score_transform_delay_observable_output():
    score_target_tones = [Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)]
    phrase_target_tones = [Tone(440.0, duration=1.0)]
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="score-target",
                                tones=score_target_tones,
                            )
                        ]
                    ),
                    Phrase(
                        motifs=[
                            Motif(
                                name="phrase-target",
                                tones=phrase_target_tones,
                            )
                        ]
                    ),
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=1)

    phrase_delay_seconds = 0.25
    delayed_phrase = delay_phrase_transform(context, DelayParams(seconds=phrase_delay_seconds))
    assert delayed_phrase.motifs[0].tones[0].frequency == 0
    assert delayed_phrase.motifs[0].tones[0].duration == pytest.approx(phrase_delay_seconds)

    score_delay_seconds = 0.1
    delayed_score = delay_score_transform(score, DelayParams(seconds=score_delay_seconds))
    assert delayed_score.voices[0].phrases[0].motifs[0].tones[0].frequency == 0


def test_invert_frequency_phrase_transform_allows_zero_hz_floor_for_emergent_pipelines():
    starting_frequencies = [0.0, 10.0]
    score = Score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="x", tones=[Tone(starting_frequencies[0]), Tone(starting_frequencies[1])])])
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    inverted_phrase = invert_phrase_transform(context, InvertParams(dimension=ToneDimension.FREQUENCY))
    assert inverted_phrase.motifs[0].tones[1].frequency == MINIMUM_FREQUENCY_HZ


def test_invert_frequency_score_transform_preserves_tone_count():
    starting_frequencies = [0.0, 10.0]
    score = Score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="x", tones=[Tone(starting_frequencies[0]), Tone(starting_frequencies[1])])])
                ]
            )
        ]
    )

    inverted_score = invert_score_transform(score, InvertParams(dimension=ToneDimension.FREQUENCY))
    assert len(inverted_score.voices[0].phrases[0].motifs[0].tones) == len(starting_frequencies)


def test_cellular_automata_phrase_and_score_transform_observable_output():
    automata_target_tones = [Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)]
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="other-voice", tones=[Tone(220.0, duration=0.5)])])
                ]
            ),
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="automata-target",
                                tones=automata_target_tones,
                            )
                        ]
                    )
                ]
            ),
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)
    params = CellularAutomataParams(dimension=ToneDimension.DURATION, rule=30, generations=2, max_deviation=0.3)

    result_phrase = cellular_automata_phrase_transform(context, params)
    assert len(result_phrase.motifs[0].tones) == len(automata_target_tones)

    result_score = cellular_automata_score_transform(score, params)
    assert len(result_score.voices) == len(score.voices)


def test_random_drop_phrase_and_score_transform_observable_output():
    drop_target_tones = [Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)]
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="drop-target",
                                tones=drop_target_tones,
                            )
                        ]
                    )
                ]
            ),
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="other-voice", tones=[Tone(550.0, duration=0.25)])])
                ]
            ),
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)
    params = {"dimension": "amplitude", "max_drop_pct": 20, "drop_frequency_pct": 80}

    dropped_phrase = random_drop_phrase_transform(context, params)
    assert len(dropped_phrase.motifs[0].tones) == len(drop_target_tones)

    dropped_score = random_drop_score_transform(score, params)
    assert len(dropped_score.voices) == len(score.voices)


def test_terraced_drift_phrase_and_score_transform_observable_output():
    drift_target_tones = [Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)]
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="drift-target",
                                tones=drift_target_tones,
                            )
                        ]
                    )
                ]
            ),
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="other-voice", tones=[Tone(550.0, duration=0.25)])])
                ]
            ),
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)
    params = {"dimension": "frequency", "max_step_change_pct": 25}

    drifted_phrase = terraced_drift_phrase_transform(context, params)
    assert len(drifted_phrase.motifs[0].tones) == len(drift_target_tones)

    drifted_score = terraced_drift_score_transform(score, params)
    assert len(drifted_score.voices) == len(score.voices)


def test_weierstrass_phrase_and_score_transform_observable_output():
    weierstrass_target_tones = [Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)]
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="weierstrass-target",
                                tones=weierstrass_target_tones,
                            )
                        ]
                    )
                ]
            ),
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="other-voice", tones=[Tone(550.0, duration=0.25)])])
                ]
            ),
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)
    params = {"dimension": "frequency", "intensity": "medium"}

    transformed_phrase = weierstrass_phrase_transform(context, params)
    assert len(transformed_phrase.motifs[0].tones) == len(weierstrass_target_tones)

    transformed_score = weierstrass_score_transform(score, params)
    assert len(transformed_score.voices) == len(score.voices)


def test_golden_ratio_phrase_and_score_transform_previous_phrase_paths():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="first-phrase",
                                tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)],
                            )
                        ]
                    ),
                    Phrase(
                        motifs=[
                            Motif(
                                name="second-phrase",
                                tones=[Tone(440.0, duration=1.0)],
                            )
                        ]
                    ),
                ]
            ),
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="cross-voice-phrase",
                                tones=[Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)],
                            )
                        ]
                    )
                ]
            ),
        ]
    )
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
    feigenbaum_target_tones = [Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)]
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="other-voice", tones=[Tone(220.0, duration=0.5)])])
                ]
            ),
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="feigenbaum-target",
                                tones=feigenbaum_target_tones,
                            )
                        ]
                    )
                ]
            ),
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)

    seq_phrase = feigenbaum_sequence_phrase_transform(context, {"dimension": "duration"})
    assert len(seq_phrase.motifs[0].tones) == len(feigenbaum_target_tones)

    seq_score = feigenbaum_sequence_score_transform(score, {"dimension": "duration"})
    assert len(seq_score.voices) == len(score.voices)
