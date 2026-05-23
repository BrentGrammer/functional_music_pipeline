import pytest

from composition.parser import generate_score_plan
from composition.transformer import transform_score
from score_model.math_constants import GOLDEN_RATIO
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import PhraseTransformContext, ToneDimension
from transforms.proportion.golden_ratio import (
    GOLDEN_RATIO_PARAMS_SPEC,
    GoldenRatioParams,
    golden_ratio_transform_shrink,
    phrase_relative_golden_ratio_grow,
    phrase_relative_golden_ratio_grow_transform,
    phrase_relative_golden_ratio_shrink,
    phrase_relative_golden_ratio_shrink_transform,
)


class TestGoldenRatioTransform:
    def test_golden_ratio_shrink_scales_duration_down_proportional_to_original_duration(self):
        original_duration = 1.0
        tones = [Tone(440.0, original_duration)]

        result = golden_ratio_transform_shrink(tones)

        assert result[0].duration == pytest.approx(original_duration / GOLDEN_RATIO)

    def test_golden_ratio_shrink_scales_frequency_down_when_dimension_is_frequency_string(self):
        original_frequency = 440.0
        original_duration = 1.0
        tones = [Tone(original_frequency, original_duration)]

        result = golden_ratio_transform_shrink(tones, dimension=ToneDimension.FREQUENCY)

        assert result[0].frequency == pytest.approx(original_frequency / GOLDEN_RATIO)
        assert result[0].duration == pytest.approx(original_duration)


class TestPhraseGoldenRatioShrink:
    def test_relative_scale_on_duration_dimension(self):
        previous_phrase_total_duration = 1.0
        previous_phrase = [Tone(440.0, duration=previous_phrase_total_duration)]

        current_tone_duration = 1.0
        current_phrase = [
            Tone(880.0, duration=current_tone_duration),
            Tone(523.0, duration=current_tone_duration),
        ]

        transformed_phrase = phrase_relative_golden_ratio_shrink(current_phrase, previous_phrase)

        expected_total_duration_current_phrase = previous_phrase_total_duration / GOLDEN_RATIO # 0.618 seconds total or 61.8% of the prev phrase duration after shrinking
        actual_total_duration = sum(tone.duration for tone in transformed_phrase)
        expected_duration_per_tone = expected_total_duration_current_phrase / len(current_phrase)

        assert actual_total_duration == pytest.approx(expected_total_duration_current_phrase)
        assert transformed_phrase[0].duration == pytest.approx(expected_duration_per_tone)
        assert transformed_phrase[1].duration == pytest.approx(expected_duration_per_tone)

    def test_empty_previous_phrase_raises_error(self):
        current_phrase = [Tone(880.0, 1.0)]

        with pytest.raises(
            ValueError,
            match="Cannot apply phrase-relative-golden-ratio-shrink: no preceding phrases exist to relate to.",
        ):
            phrase_relative_golden_ratio_shrink(current_phrase, [])

    def test_empty_current_phrase_returns_empty_list(self):
        previous_phrase = [Tone(440.0, duration=1.0)]

        assert phrase_relative_golden_ratio_shrink([], previous_phrase) == []

    def test_zero_current_total_returns_original_tones(self):
        previous_phrase = [Tone(440.0, duration=1.0)]
        zero_duration_phrase = [Tone(880.0, duration=0.0), Tone(523.0, duration=0.0)]

        result = phrase_relative_golden_ratio_shrink(zero_duration_phrase, previous_phrase)

        assert result is zero_duration_phrase

    def test_zero_previous_total_returns_original_tones(self):
        zero_duration_previous_phrase = [Tone(440.0, duration=0.0)]
        current_phrase = [Tone(880.0, duration=1.0)]

        result = phrase_relative_golden_ratio_shrink(current_phrase, zero_duration_previous_phrase)

        assert result is current_phrase

    def test_relative_scale_on_amplitude_dimension(self):
        previous_phrase_total_amplitude = 0.6
        previous_phrase = [Tone(440.0, amplitude=previous_phrase_total_amplitude)]
        current_phrase = [
            Tone(660.0, amplitude=0.3),
            Tone(880.0, amplitude=0.3),
        ]

        transformed_phrase = phrase_relative_golden_ratio_shrink(
            current_phrase,
            previous_phrase,
            dimension=ToneDimension.AMPLITUDE,
        )

        expected_total_amplitude = previous_phrase_total_amplitude / GOLDEN_RATIO
        actual_total_amplitude = sum(tone.amplitude for tone in transformed_phrase)

        assert actual_total_amplitude == pytest.approx(expected_total_amplitude)


class TestPhraseGoldenRatioGrow:
    def test_inverse_relative_scale_on_duration_dimension(self):
        previous_phrase_total_duration = 1.0
        previous_phrase = [Tone(440.0, duration=previous_phrase_total_duration)]

        current_tone_duration = 1.0
        current_phrase = [
            Tone(880.0, duration=current_tone_duration),
            Tone(523.0, duration=current_tone_duration),
        ]

        transformed_phrase = phrase_relative_golden_ratio_grow(current_phrase, previous_phrase)

        expected_total_duration = previous_phrase_total_duration * GOLDEN_RATIO
        actual_total_duration = sum(tone.duration for tone in transformed_phrase)
        expected_duration_per_tone = expected_total_duration / len(current_phrase)

        assert actual_total_duration == pytest.approx(expected_total_duration)
        assert transformed_phrase[0].duration == pytest.approx(expected_duration_per_tone)
        assert transformed_phrase[1].duration == pytest.approx(expected_duration_per_tone)

    def test_empty_previous_phrase_raises_error(self):
        current_phrase = [Tone(880.0, 1.0)]

        with pytest.raises(
            ValueError,
            match="Cannot apply phrase-relative-golden-ratio-grow: no preceding phrases exist to relate to.",
        ):
            phrase_relative_golden_ratio_grow(current_phrase, [])

    def test_empty_current_phrase_returns_empty_list(self):
        previous_phrase = [Tone(440.0, duration=1.0)]

        assert phrase_relative_golden_ratio_grow([], previous_phrase) == []

    def test_zero_current_total_returns_original_tones(self):
        previous_phrase = [Tone(440.0, duration=1.0)]
        zero_duration_phrase = [Tone(880.0, duration=0.0), Tone(523.0, duration=0.0)]

        result = phrase_relative_golden_ratio_grow(zero_duration_phrase, previous_phrase)

        assert result is zero_duration_phrase

    def test_zero_previous_total_returns_original_tones(self):
        zero_duration_previous_phrase = [Tone(440.0, duration=0.0)]
        current_phrase = [Tone(880.0, duration=1.0)]

        result = phrase_relative_golden_ratio_grow(current_phrase, zero_duration_previous_phrase)

        assert result is current_phrase

    def test_relative_scale_on_frequency_dimension(self):
        previous_phrase_total_frequency = 440.0
        previous_phrase = [Tone(previous_phrase_total_frequency, duration=1.0)]
        current_phrase = [
            Tone(220.0, duration=1.0),
            Tone(220.0, duration=1.0),
        ]

        transformed_phrase = phrase_relative_golden_ratio_grow(
            current_phrase,
            previous_phrase,
            dimension=ToneDimension.FREQUENCY,
        )

        expected_total_frequency = previous_phrase_total_frequency * GOLDEN_RATIO
        actual_total_frequency = sum(tone.frequency for tone in transformed_phrase)

        assert actual_total_frequency == pytest.approx(expected_total_frequency)


class TestGoldenRatioErrors:
    def test_golden_ratio_params_spec_rejects_invalid_dimension(self):
        with pytest.raises(ValueError):
            GOLDEN_RATIO_PARAMS_SPEC.parse_params({"dimension": 1})
        with pytest.raises(ValueError):
            GOLDEN_RATIO_PARAMS_SPEC.parse_params({"dimension": []})

    def test_phrase_relative_golden_ratio_grow_transform_without_previous_phrase_raises(self):
        score = Score([Voice([Phrase([Motif("m", [Tone(440.0, duration=1.0)])])])])
        context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

        with pytest.raises(ValueError):
            phrase_relative_golden_ratio_grow_transform(context, GoldenRatioParams(dimension=ToneDimension.DURATION))


class TestGoldenRatioCompositionRegression:


    def test_phrase_relative_golden_ratio_shrink_demo_scales_from_immediately_previous_phrase(self):
        
        origin_seed_total_duration = 8.0 # 2.0 + 2.0 + 2.0 + 2.0 - each duration added up from the seed tones

        composition_document = {
            "motifs": {
                "c_major_arpeggio": [
                    "261.63:2.0",
                    "329.63:2.0",
                    "392.00:2.0",
                    "523.25:2.0",
                ]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {"motifs": ["c_major_arpeggio"]},
                            {
                                "motifs": ["c_major_arpeggio"],
                                "transforms": [
                                    {
                                        "name": "phrase_relative_golden_ratio_shrink",
                                        "params": {"dimension": "duration"},
                                    }
                                ],
                            },
                            {
                                "motifs": ["c_major_arpeggio"],
                                "transforms": [
                                    {
                                        "name": "phrase_relative_golden_ratio_shrink",
                                        "params": {"dimension": "duration"},
                                    }
                                ],
                            },
                        ]
                    }
                ],
                "score_transforms": [],
            },
        }

        score = transform_score(generate_score_plan(composition_document))

        phrase_duration_totals = [
            sum(tone.duration for motif in phrase.motifs for tone in motif.tones)
            for phrase in score.voices[0].phrases
        ]
        original_phrase_total_duration = phrase_duration_totals[0]

        assert original_phrase_total_duration == pytest.approx(origin_seed_total_duration)
        assert phrase_duration_totals[1] == pytest.approx(original_phrase_total_duration / GOLDEN_RATIO)
        assert phrase_duration_totals[2] == pytest.approx(original_phrase_total_duration / GOLDEN_RATIO / GOLDEN_RATIO)


    def test_phrase_relative_golden_ratio_grow_demo_scales_from_immediately_previous_phrase(self):

        origin_seed_total_duration = 8.0 # 2.0 + 2.0 + 2.0 + 2.0 - each duration added up from the seed tones

        composition_document = {
            "motifs": {
                "c_major_arpeggio": [
                    "261.63:2.0",
                    "329.63:2.0",
                    "392.00:2.0",
                    "523.25:2.0",
                ]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {"motifs": ["c_major_arpeggio"]},
                            {
                                "motifs": ["c_major_arpeggio"],
                                "transforms": [
                                    {
                                        "name": "phrase_relative_golden_ratio_grow",
                                        "params": {"dimension": "duration"},
                                    }
                                ],
                            },
                            {
                                "motifs": ["c_major_arpeggio"],
                                "transforms": [
                                    {
                                        "name": "phrase_relative_golden_ratio_grow",
                                        "params": {"dimension": "duration"},
                                    }
                                ],
                            },
                        ]
                    }
                ],
                "score_transforms": [],
            },
        }

        score = transform_score(generate_score_plan(composition_document))

        phrase_duration_totals = [
            sum(tone.duration for motif in phrase.motifs for tone in motif.tones)
            for phrase in score.voices[0].phrases
        ]
        original_phrase_total_duration = phrase_duration_totals[0]

        assert original_phrase_total_duration == pytest.approx(origin_seed_total_duration)
        assert phrase_duration_totals[1] == pytest.approx(original_phrase_total_duration * GOLDEN_RATIO)
        assert phrase_duration_totals[2] == pytest.approx(original_phrase_total_duration * GOLDEN_RATIO * GOLDEN_RATIO)
