import pytest

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from transforms.base import PhraseTransformContext, ToneDimension
from transforms.basic.scale import scale_phrase_transform, scale_score_transform, scale_transform


class TestScaleTransform:
    def test_empty_sequence_returns_empty_list(self):
        no_tones: list[Tone] = []

        assert scale_transform(no_tones, ToneDimension.DURATION, 2.0) == []

    def test_scale_frequency(self):
        tones = [Tone(440.0)]
        result = scale_transform(tones, ToneDimension.FREQUENCY, 1.5)
        assert result[0].frequency == pytest.approx(660.0)

    def test_scale_duration(self):
        tones = [Tone(440.0, duration=1.0)]
        result = scale_transform(tones, ToneDimension.DURATION, 2.0)
        assert result[0].duration == pytest.approx(2.0)

    def test_scale_amplitude(self):
        tones = [Tone(440.0, amplitude=0.5)]
        result = scale_transform(tones, ToneDimension.AMPLITUDE, 0.5)
        assert result[0].amplitude == pytest.approx(0.25)

    def test_scale_amplitude_clamp(self):
        tones = [Tone(440.0, amplitude=0.8)]
        result = scale_transform(tones, ToneDimension.AMPLITUDE, 2.0)
        assert result[0].amplitude == pytest.approx(1.0)

    def test_scale_frequency_clamps_to_minimum_positive_frequency(self):
        sub_minimum_frequency = 0.5
        shrinking_factor = 0.5
        minimum_allowed_frequency = 1.0
        tones = [Tone(sub_minimum_frequency)]

        result = scale_transform(tones, ToneDimension.FREQUENCY, shrinking_factor)

        assert result[0].frequency == pytest.approx(minimum_allowed_frequency)

    def test_scale_duration_clamps_to_zero(self):
        original_duration = 1.0
        shrinking_factor = -2.0
        minimum_allowed_duration = 0.0
        tones = [Tone(440.0, duration=original_duration)]

        result = scale_transform(tones, ToneDimension.DURATION, shrinking_factor)

        assert result[0].duration == pytest.approx(minimum_allowed_duration)

    def test_scale_frequency_accepts_string_dimension_and_preserves_other_fields(self):
        original_frequency = 440.0
        original_duration = 0.75
        original_sample_rate = 22050
        original_amplitude = 0.6
        scaling_factor = 1.5
        tones = [
            Tone(
                original_frequency,
                duration=original_duration,
                sample_rate=original_sample_rate,
                amplitude=original_amplitude,
            )
        ]

        result = scale_transform(tones, "frequency", scaling_factor)

        assert result[0].frequency == pytest.approx(original_frequency * scaling_factor)
        assert result[0].duration == pytest.approx(original_duration)
        assert result[0].sample_rate == original_sample_rate
        assert result[0].amplitude == pytest.approx(original_amplitude)


class TestScalePhraseTransformHappyPath:
    def test_phrase_transform_scales_duration(self):
        first_duration = 1.0
        second_duration = 2.0
        score = Score(
            voices=[
                Voice(
                    phrases=[
                        Phrase(
                            motifs=[
                                Motif(name="m", tones=[Tone(440.0, duration=first_duration), Tone(440.0, duration=second_duration)])
                            ]
                        )
                    ]
                )
            ]
        )
        context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)
        
        factor = 0.5
        result = scale_phrase_transform(context, {"dimension": ToneDimension.DURATION, "factor": factor})

        tones = result.motifs[0].tones
        assert tones[0].duration == pytest.approx(first_duration * factor)
        assert tones[1].duration == pytest.approx(second_duration * factor)


class TestScalePhraseTransformErrorPath:
    def test_phrase_transform_rejects_invalid_dimension_type(self):
        score = Score(voices=[Voice(phrases=[Phrase(motifs=[Motif(name="m", tones=[Tone(440.0, duration=1.0)])])])])
        context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

        with pytest.raises(ValueError):
            scale_phrase_transform(context, {"dimension": True, "factor": 2.0})

    def test_phrase_transform_rejects_invalid_factor_type(self):
        score = Score(voices=[Voice(phrases=[Phrase(motifs=[Motif(name="m", tones=[Tone(440.0, duration=1.0)])])])])
        context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

        with pytest.raises(ValueError):
            scale_phrase_transform(context, {"dimension": "DURATION", "factor": True})


class TestScaleScoreTransformHappyPath:
    def test_score_transform_scales_all_voices(self):
        first_duration = 1.0
        second_duration = 2.0
        score = Score(
            voices=[
                Voice(phrases=[Phrase(motifs=[Motif(name="a", tones=[Tone(440.0, duration=first_duration)])])]),
                Voice(phrases=[Phrase(motifs=[Motif(name="b", tones=[Tone(220.0, duration=second_duration)])])]),
            ]
        )

        factor = 2.0
        result = scale_score_transform(score, {"dimension": ToneDimension.DURATION, "factor": factor})

        first = flatten_voice_tones(result.voices[0])
        second = flatten_voice_tones(result.voices[1])
        assert first[0].duration == pytest.approx(first_duration * factor)
        assert second[0].duration == pytest.approx(second_duration * factor)


class TestScaleScoreTransformErrorPath:
    def test_score_transform_rejects_invalid_dimension_type(self):
        with pytest.raises(ValueError):
            scale_score_transform(Score(voices=[]), {"dimension": None, "factor": 2.0})

    def test_score_transform_rejects_invalid_factor_type(self):
        with pytest.raises(ValueError):
            scale_score_transform(Score(voices=[]), {"dimension": "DURATION", "factor": True})
