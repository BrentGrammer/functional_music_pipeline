import pytest

from score_model.math_constants import GOLDEN_RATIO
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
from transforms.complexity.random_drop import RandomDropParams, random_drop_phrase_transform, random_drop_score_transform
from transforms.complexity.weierstrass import WeierstrassParams, weierstrass_phrase_transform, weierstrass_score_transform
from transforms.geological.terraced_drift import TerracedDriftParams, terraced_drift_phrase_transform, terraced_drift_score_transform
from transforms.proportion.feigenbaum import FeigenbaumParams, feigenbaum_sequence_phrase_transform, feigenbaum_sequence_score_transform
from transforms.proportion.golden_ratio import (
    GoldenRatioParams,
    phrase_relative_golden_ratio_shrink_transform,
)


def test_repeat_phrase_and_score_transform_repeat_observable_output():
    phrase_tones = [Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)]
    phrase_score = Score(
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
    score = Score(
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
    score = Score(
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
    score = Score(
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
    score = Score(
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
    score = Score(
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
    params = RandomDropParams(dimension=ToneDimension.AMPLITUDE, max_drop_pct=20, drop_frequency_pct=80)

    dropped_phrase = random_drop_phrase_transform(context, params)
    assert len(dropped_phrase.motifs[0].tones) == len(drop_target_tones)

    dropped_score = random_drop_score_transform(score, params)
    assert len(dropped_score.voices) == len(score.voices)


def test_terraced_drift_phrase_and_score_transform_observable_output():
    drift_target_tones = [Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)]
    score = Score(
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
    params = TerracedDriftParams(dimension=ToneDimension.FREQUENCY, max_step_change_pct=25)

    drifted_phrase = terraced_drift_phrase_transform(context, params)
    assert len(drifted_phrase.motifs[0].tones) == len(drift_target_tones)

    drifted_score = terraced_drift_score_transform(score, params)
    assert len(drifted_score.voices) == len(score.voices)


def test_weierstrass_phrase_and_score_transform_observable_output():
    weierstrass_target_tones = [Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)]
    score = Score(
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
    params = WeierstrassParams(dimension=ToneDimension.FREQUENCY, intensity="medium")

    transformed_phrase = weierstrass_phrase_transform(context, params)
    assert len(transformed_phrase.motifs[0].tones) == len(weierstrass_target_tones)

    transformed_score = weierstrass_score_transform(score, params)
    assert len(transformed_score.voices) == len(score.voices)


def test_phrase_relative_golden_ratio_shrink_transform_uses_previous_voice_when_first_phrase():
    previous_voice_first_phrase_tone_duration = 0.5
    previous_voice_second_phrase_tone_duration = 1.0
    previous_voice_total_duration = (
        previous_voice_first_phrase_tone_duration * 2
        + previous_voice_second_phrase_tone_duration
    )
    current_voice_tone_duration = 0.25
    current_voice_tone_count = 2

    score = Score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="first-phrase",
                                tones=[
                                    Tone(220.0, duration=previous_voice_first_phrase_tone_duration),
                                    Tone(330.0, duration=previous_voice_first_phrase_tone_duration),
                                ],
                            )
                        ]
                    ),
                    Phrase(
                        motifs=[
                            Motif(
                                name="second-phrase",
                                tones=[Tone(440.0, duration=previous_voice_second_phrase_tone_duration)],
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
                                tones=[
                                    Tone(550.0, duration=current_voice_tone_duration),
                                    Tone(660.0, duration=current_voice_tone_duration),
                                ],
                            )
                        ]
                    )
                ]
            ),
        ]
    )
    cross_voice_context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)

    shrunk = phrase_relative_golden_ratio_shrink_transform(cross_voice_context, GoldenRatioParams(dimension=ToneDimension.DURATION))
    durations = [tone.duration for tone in shrunk.motifs[0].tones]

    expected_total_duration = previous_voice_total_duration / GOLDEN_RATIO
    expected_duration_per_tone = expected_total_duration / current_voice_tone_count
    assert len(durations) == current_voice_tone_count
    assert sum(durations) == pytest.approx(expected_total_duration)
    assert durations[0] == pytest.approx(expected_duration_per_tone)
    assert durations[1] == pytest.approx(expected_duration_per_tone)


def test_feigenbaum_phrase_and_score_transform_previous_phrase_paths():
    feigenbaum_target_tones = [Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)]
    score = Score(
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

    seq_phrase = feigenbaum_sequence_phrase_transform(context, FeigenbaumParams(dimension=ToneDimension.DURATION))
    assert len(seq_phrase.motifs[0].tones) == len(feigenbaum_target_tones)

    seq_score = feigenbaum_sequence_score_transform(score, FeigenbaumParams(dimension=ToneDimension.DURATION))
    assert len(seq_score.voices) == len(score.voices)
