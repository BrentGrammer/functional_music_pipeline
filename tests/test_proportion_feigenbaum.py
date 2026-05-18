import pytest

from score_model.math_constants import FEIGENBAUM_DELTA
from score_model.motif import Motif
from score_model.score import Score
from score_model.phrase import Phrase
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from transforms.base import PhraseTransformContext, ToneDimension
from transforms.proportion.feigenbaum import (
    feigenbaum_sequence,
    phrase_feigenbaum_grow,
    phrase_feigenbaum_shrink,
    phrase_feigenbaum_shrink_transform,
    score_feigenbaum_sequence,
)


class TestFeigenbaumSequence:
    def test_basic_sequence(self):
        tones = [
            Tone(440.0, duration=FEIGENBAUM_DELTA),
            Tone(523.0),
            Tone(659.0),
        ]

        result = feigenbaum_sequence(tones)

        assert len(result) == 3
        assert result[0].duration == pytest.approx(FEIGENBAUM_DELTA)
        assert result[1].duration == pytest.approx(1.0)
        assert result[2].duration == pytest.approx(1.0 / FEIGENBAUM_DELTA)

    def test_single_tone_returns_original_duration(self):
        tone = Tone(440.0)

        result = feigenbaum_sequence([tone])

        assert len(result) == 1
        assert result[0].duration == tone.duration

    def test_empty_input_returns_empty_list(self):
        assert feigenbaum_sequence([]) == []

    def test_amplitude_dimension_scales_by_inverse_constant(self):
        tones = [Tone(440.0, amplitude=1.0), Tone(880.0, amplitude=1.0)]

        result = feigenbaum_sequence(tones, dimension=ToneDimension.AMPLITUDE)

        assert result[0].amplitude == 1.0
        assert result[1].amplitude == pytest.approx(1.0 / FEIGENBAUM_DELTA)

    def test_frequency_dimension_clamps_to_minimum_positive_frequency(self):
        tones = [
            Tone(0.5, duration=1.0),
            Tone(0.5, duration=1.0),
        ]

        result = feigenbaum_sequence(tones, dimension=ToneDimension.FREQUENCY)

        assert result[1].frequency == 1.0


class TestPhraseFeigenbaumShrink:
    def test_relative_scale_on_duration_dimension(self):
        previous_phrase = [Tone(440.0, duration=1.0)]
        current_phrase = [
            Tone(880.0, duration=1.0),
            Tone(523.0, duration=1.0),
        ]

        transformed_phrase = phrase_feigenbaum_shrink(current_phrase, previous_phrase)

        expected_total_duration = 1.0 / FEIGENBAUM_DELTA
        actual_total_duration = sum(tone.duration for tone in transformed_phrase)

        assert actual_total_duration == pytest.approx(expected_total_duration)
        assert transformed_phrase[0].duration == pytest.approx(expected_total_duration / 2)
        assert transformed_phrase[1].duration == pytest.approx(expected_total_duration / 2)

    def test_empty_previous_phrase_raises_error(self):
        with pytest.raises(
            ValueError,
            match="Cannot apply phrase-feigenbaum-shrink: no preceding phrases exist to relate to.",
        ):
            phrase_feigenbaum_shrink([Tone(880.0, 1.0)], [])

    def test_empty_current_phrase_returns_empty_list(self):
        previous_phrase = [Tone(440.0, duration=1.0)]

        assert phrase_feigenbaum_shrink([], previous_phrase) == []

    def test_zero_current_total_returns_original_tones(self):
        previous_phrase = [Tone(440.0, duration=1.0)]
        zero_duration_phrase = [
            Tone(880.0, duration=0.0),
            Tone(523.0, duration=0.0),
        ]

        result = phrase_feigenbaum_shrink(zero_duration_phrase, previous_phrase)

        assert result is zero_duration_phrase

    def test_zero_previous_total_returns_original_tones(self):
        zero_duration_previous_phrase = [Tone(440.0, duration=0.0)]
        current_phrase = [Tone(880.0, duration=1.0)]

        result = phrase_feigenbaum_shrink(current_phrase, zero_duration_previous_phrase)

        assert result is current_phrase

    def test_relative_scale_on_amplitude_dimension(self):
        previous_phrase = [Tone(440.0, amplitude=0.6)]
        current_phrase = [
            Tone(880.0, amplitude=0.3),
            Tone(523.0, amplitude=0.3),
        ]

        transformed_phrase = phrase_feigenbaum_shrink(
            current_phrase,
            previous_phrase,
            dimension="AMPLITUDE",
        )

        actual_total_amplitude = sum(tone.amplitude for tone in transformed_phrase)

        assert actual_total_amplitude == pytest.approx(0.6 / FEIGENBAUM_DELTA)

    def test_phrase_feigenbaum_shrink_transform_scales_against_previous_phrase(self):
        prev_phrase_total_duration = 2.0
        current_phrase_duration = 1.0

        reference_phrase_idx = 0
        active_phrase_idx = 1

        score = Score(
            [
                Voice(
                    [
                        Phrase([Motif("first", [Tone(440.0, duration=prev_phrase_total_duration)])]),
                        Phrase(
                            [
                                Motif(
                                    "second",
                                    [
                                        Tone(880.0, duration=current_phrase_duration),
                                        Tone(523.0, duration=current_phrase_duration),
                                    ],
                                )
                            ]
                        ),
                    ]
                )
            ]
        )
        context = PhraseTransformContext(score=score, voice_index=reference_phrase_idx, phrase_index=active_phrase_idx)

        result = phrase_feigenbaum_shrink_transform(context, {})

        assert len(result.motifs) == 1

        transformed_motifs = result.motifs[0]
        assert transformed_motifs.name == "<transformed>"
        
        scaled_total_phrase_duration_based_on_ref_phrase = prev_phrase_total_duration / FEIGENBAUM_DELTA
        # The phrase has two equal-length tones, so after scaling the total
        # phrase duration, each tone should get half of that total.
        assert [tone.duration for tone in transformed_motifs.tones] == [
            pytest.approx(scaled_total_phrase_duration_based_on_ref_phrase / 2),
            pytest.approx(scaled_total_phrase_duration_based_on_ref_phrase / 2),
        ]


class TestPhraseFeigenbaumGrow:
    def test_relative_scale_on_duration_dimension(self):
        previous_phrase = [Tone(440.0, duration=1.0)]
        current_phrase = [
            Tone(880.0, duration=1.0),
            Tone(523.0, duration=1.0),
        ]

        transformed_phrase = phrase_feigenbaum_grow(current_phrase, previous_phrase)

        expected_total_duration = 1.0 * FEIGENBAUM_DELTA
        actual_total_duration = sum(tone.duration for tone in transformed_phrase)

        assert actual_total_duration == pytest.approx(expected_total_duration)
        assert transformed_phrase[0].duration == pytest.approx(expected_total_duration / 2)
        assert transformed_phrase[1].duration == pytest.approx(expected_total_duration / 2)

    def test_empty_previous_phrase_raises_error(self):
        with pytest.raises(
            ValueError,
            match="Cannot apply phrase-feigenbaum-grow: no preceding phrases exist to relate to.",
        ):
            phrase_feigenbaum_grow([Tone(880.0, 1.0)], [])

    def test_empty_current_phrase_returns_empty_list(self):
        previous_phrase = [Tone(440.0, duration=1.0)]

        assert phrase_feigenbaum_grow([], previous_phrase) == []

    def test_zero_current_total_returns_original_tones(self):
        previous_phrase = [Tone(440.0, duration=1.0)]
        zero_duration_phrase = [
            Tone(880.0, duration=0.0),
            Tone(523.0, duration=0.0),
        ]

        result = phrase_feigenbaum_grow(zero_duration_phrase, previous_phrase)

        assert result is zero_duration_phrase

    def test_zero_previous_total_returns_original_tones(self):
        zero_duration_previous_phrase = [Tone(440.0, duration=0.0)]
        current_phrase = [Tone(880.0, duration=1.0)]

        result = phrase_feigenbaum_grow(current_phrase, zero_duration_previous_phrase)

        assert result is current_phrase

    def test_relative_scale_on_frequency_dimension(self):
        previous_phrase = [Tone(440.0, duration=1.0)]
        current_phrase = [
            Tone(220.0, duration=1.0),
            Tone(220.0, duration=1.0),
        ]

        transformed_phrase = phrase_feigenbaum_grow(
            current_phrase,
            previous_phrase,
            dimension="FREQUENCY",
        )

        actual_total_frequency = sum(tone.frequency for tone in transformed_phrase)

        assert actual_total_frequency == pytest.approx(440.0 * FEIGENBAUM_DELTA)


class TestScoreFeigenbaumSequence:
    def test_score_duration_sequence_scales_each_voice_by_position(self):
        score = Score(
            [
                Voice([Phrase([Motif("<test>", [Tone(440.0, 1.0)])])]),
                Voice([Phrase([Motif("<test>", [Tone(880.0, 1.0)])])]),
                Voice([Phrase([Motif("<test>", [Tone(523.0, 1.0)])])]),
            ]
        )

        result_score = score_feigenbaum_sequence(score)
        first_voice_tones = flatten_voice_tones(result_score.voices[0])
        second_voice_tones = flatten_voice_tones(result_score.voices[1])
        third_voice_tones = flatten_voice_tones(result_score.voices[2])

        assert len(result_score.voices) == 3
        assert first_voice_tones[0].duration == 1.0
        assert second_voice_tones[0].duration == pytest.approx(1.0 / FEIGENBAUM_DELTA)
        assert third_voice_tones[0].duration == pytest.approx((1.0 / FEIGENBAUM_DELTA) / FEIGENBAUM_DELTA)

    def test_empty_score_returns_original_score(self):
        empty_score = Score()

        result = score_feigenbaum_sequence(empty_score)

        assert result is empty_score

    def test_single_voice_score_raises_error(self):
        single_voice_score = Score([Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])])])

        with pytest.raises(ValueError, match="requires at least 2 voices"):
            score_feigenbaum_sequence(single_voice_score)

    def test_frequency_dimension_scales_each_voice_by_position(self):
        score = Score(
            [
                Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])]),
                Voice([Phrase([Motif("<test>", [Tone(440.0, duration=1.0)])])]),
            ]
        )

        result = score_feigenbaum_sequence(score, dimension="FREQUENCY")
        first_voice_tones = flatten_voice_tones(result.voices[0])
        second_voice_tones = flatten_voice_tones(result.voices[1])

        assert first_voice_tones[0].frequency == pytest.approx(440.0)
        assert second_voice_tones[0].frequency == pytest.approx(440.0 / FEIGENBAUM_DELTA)
