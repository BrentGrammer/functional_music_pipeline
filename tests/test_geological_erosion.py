
import pytest

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import PhraseTransformContext, ToneDimension
from transforms.geological.erosion import erosion_phrase_transform, erosion_transform


class TestErosionDuration:
    def test_empty_sequence(self):
        assert erosion_transform([]) == []

    def test_single_tone_returns_empty(self):
        # A single tone cannot be eroded further (loop condition len > 1 fails immediately).
        # The result is an empty list because the loop never runs to extend it.
        tones = [Tone(440, 1.0)]
        result = erosion_transform(tones)
        assert result == []

    def test_two_tones(self):
        # Input: [A, B]
        # Pass 1: pop B -> [A]. Result extends to [A].
        # Loop ends.
        # Result: [A]
        FREQ_A = 440.0
        FREQ_B = 880.0
        
        tones = [Tone(FREQ_A, 1.0), Tone(FREQ_B, 0.5)]
        result = erosion_transform(tones)
        
        assert len(result) == 1
        assert result[0].frequency == FREQ_A

    def test_three_tones(self):
        # Input: [A, B, C]
        # Pass 1: pop C -> [A, B]. Result extends to [A, B].
        # Pass 2: pop B -> [A]. Result extends to [A, B, A].
        # Loop ends.
        FREQ_A = 100.0
        FREQ_B = 200.0
        FREQ_C = 300.0
        
        tones = [
            Tone(FREQ_A, 1.0), 
            Tone(FREQ_B, 1.0), 
            Tone(FREQ_C, 1.0)
        ]
        result = erosion_transform(tones)
        
        assert len(result) == 3
        assert result[0].frequency == FREQ_A
        assert result[1].frequency == FREQ_B
        assert result[2].frequency == FREQ_A

    def test_four_tones(self):
        # Input: [A, B, C, D]
        # Pass 1: pop D -> [A, B, C]. Result extends to [A, B, C].
        # Pass 2: pop C -> [A, B]. Result extends to [A, B, C, A, B].
        # Pass 3: pop B -> [A]. Result extends to [A, B, C, A, B, A].
        # Loop ends.
        FREQ_A = 100.0
        FREQ_B = 200.0
        FREQ_C = 300.0
        FREQ_D = 400.0
        
        tones = [
            Tone(FREQ_A, 1.0), 
            Tone(FREQ_B, 1.0), 
            Tone(FREQ_C, 1.0), 
            Tone(FREQ_D, 1.0)
        ]
        result = erosion_transform(tones)
        
        EXPECTED_RESULT_LENGTH = 6
        
        assert len(result) == EXPECTED_RESULT_LENGTH
        # Check the sequence matches the algorithm
        assert result[0].frequency == FREQ_A 
        assert result[1].frequency == FREQ_B 
        assert result[2].frequency == FREQ_C 
        assert result[3].frequency == FREQ_A 
        assert result[4].frequency == FREQ_B 
        assert result[5].frequency == FREQ_A 

    def test_string_dimension(self):
        FREQ_A = 440.0
        FREQ_B = 880.0
        
        tones = [Tone(FREQ_A, 1.0), Tone(FREQ_B, 0.5)]
        result = erosion_transform(tones, dimension="DURATION")
        assert len(result) == 1


class TestErosionAmplitude:
    def test_empty_sequence(self):
        assert erosion_transform([], dimension=ToneDimension.AMPLITUDE) == []

    def test_single_tone_full_volume(self):
        # N=1. Scale = 1.0 - 0/(1-1) -> Division by zero.
        # Algorithm should handle N=1 gracefully (scale 1.0).
        FREQ_A = 440.0
        AMP_A = 0.5
        
        tones = [Tone(FREQ_A, 1.0, amplitude=AMP_A)]
        result = erosion_transform(tones, dimension=ToneDimension.AMPLITUDE)
        
        assert len(result) == 1
        assert result[0].amplitude == pytest.approx(AMP_A)

    def test_linear_fade_on_two_tones(self):
        # N=2.
        # i=0: scale = 1.0 - 0/1 = 1.0. Amp = 0.8 * 1.0 = 0.8
        # i=1: scale = 1.0 - 1/1 = 0.0. Amp = 0.8 * 0.0 = 0.0
        FREQ_A = 440.0
        FREQ_B = 880.0
        INITIAL_AMP = 0.8
        FADED_AMP = 0.0
        
        tones = [
            Tone(FREQ_A, 1.0, amplitude=INITIAL_AMP), 
            Tone(FREQ_B, 1.0, amplitude=INITIAL_AMP)
        ]
        result = erosion_transform(tones, dimension=ToneDimension.AMPLITUDE)
        
        assert len(result) == 2
        assert result[0].amplitude == pytest.approx(INITIAL_AMP)
        assert result[1].amplitude == pytest.approx(FADED_AMP)

    def test_linear_fade_on_three_tones(self):
        # N=3.
        # i=0: scale = 1.0 - 0/2 = 1.0
        # i=1: scale = 1.0 - 1/2 = 0.5
        # i=2: scale = 1.0 - 2/2 = 0.0
        FREQ_A = 100.0
        FREQ_B = 200.0
        FREQ_C = 300.0
        INITIAL_AMP = 1.0
        MID_AMP = 0.5
        FADED_AMP = 0.0
        
        tones = [
            Tone(FREQ_A, 1.0, amplitude=INITIAL_AMP), 
            Tone(FREQ_B, 1.0, amplitude=INITIAL_AMP), 
            Tone(FREQ_C, 1.0, amplitude=INITIAL_AMP)
        ]
        result = erosion_transform(tones, dimension=ToneDimension.AMPLITUDE)
        
        assert len(result) == 3
        assert result[0].amplitude == pytest.approx(INITIAL_AMP)
        assert result[1].amplitude == pytest.approx(MID_AMP)
        assert result[2].amplitude == pytest.approx(FADED_AMP)


class TestErosionFrequency:
    def test_empty_sequence(self):
        assert erosion_transform([], dimension=ToneDimension.FREQUENCY) == []

    def test_single_tone_unchanged(self):
        FREQ_A = 440.0
        
        tones = [Tone(FREQ_A, 1.0)]
        result = erosion_transform(tones, dimension=ToneDimension.FREQUENCY)
        
        assert len(result) == 1
        assert result[0].frequency == FREQ_A

    def test_two_tones_collapse(self):
        # Target = 100.
        # i=0: Freq = 100 (Target)
        # i=1: Freq = 100 (Last tone collapses to target)
        FREQ_A = 100.0
        FREQ_B = 200.0
        
        tones = [
            Tone(FREQ_A, 1.0), 
            Tone(FREQ_B, 1.0)
        ]
        result = erosion_transform(tones, dimension=ToneDimension.FREQUENCY)
        
        assert len(result) == 2
        assert result[0].frequency == pytest.approx(FREQ_A)
        assert result[1].frequency == pytest.approx(FREQ_A)

    def test_three_tones_interpolation(self):
        # Target = 100.
        # i=0: Freq = 100.
        # i=1: Interpolate 50% towards 100. 200 -> 150.
        # i=2: Freq = 100 (Last tone collapses to target).
        FREQ_A = 100.0
        FREQ_B = 200.0
        FREQ_C = 300.0
        INTERPOLATED_FREQ = 150.0
        
        tones = [
            Tone(FREQ_A, 1.0), 
            Tone(FREQ_B, 1.0), 
            Tone(FREQ_C, 1.0)
        ]
        result = erosion_transform(tones, dimension=ToneDimension.FREQUENCY)
        
        assert len(result) == 3
        assert result[0].frequency == pytest.approx(FREQ_A)
        assert result[1].frequency == pytest.approx(INTERPOLATED_FREQ)
        assert result[2].frequency == pytest.approx(FREQ_A)


def test_erosion_phrase_transform_returns_transformed_phrase():
    phrase = Phrase([Motif("<test>", [Tone(440.0, 1.0), Tone(880.0, 1.0)])])
    context = PhraseTransformContext(
        score=Score([Voice([phrase])]),
        voice_index=0,
        phrase_index=0,
    )

    result = erosion_phrase_transform(context, {"dimension": ToneDimension.DURATION})

    assert len(result.motifs) == 1
    assert result.motifs[0].name == "<transformed>"
    assert len(result.motifs[0].tones) == 1
    assert result.motifs[0].tones[0].frequency == pytest.approx(440.0)


def test_erosion_phrase_transform_rejects_non_string_non_dimension_param():
    phrase = Phrase([Motif("<test>", [Tone(440.0, 1.0)])])
    context = PhraseTransformContext(
        score=Score([Voice([phrase])]),
        voice_index=0,
        phrase_index=0,
    )

    with pytest.raises(ValueError, match="must be a string or ToneDimension"):
        erosion_phrase_transform(context, {"dimension": 123})


def test_erosion_transform_rejects_invalid_dimension_value():
    tones = [Tone(440.0, 1.0), Tone(880.0, 0.5)]

    with pytest.raises(ValueError, match="Invalid dimension"):
        erosion_transform(tones, dimension="unexpected")
