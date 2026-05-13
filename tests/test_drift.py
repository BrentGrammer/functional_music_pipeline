from composition.schema import CompositionDocument
import pytest

from composition.parser import TRANSFORMS, parse_composition
from score_model.tone import Tone
from transforms.base import ToneDimension, TransformScope
from transforms.drift import drift_transform


class TestDriftFrequency:
    def test_empty_sequence(self):
        assert drift_transform([], dimension=ToneDimension.FREQUENCY, rate=0.1) == []

    def test_single_tone_shifted(self):
        # Rate 0.1 means step is 44. First tone becomes 440 + 44 = 484.
        FREQ_A = 440.0
        RATE = 0.1
        EXPECTED_FREQ = FREQ_A + (FREQ_A * RATE)
        
        tones = [Tone(FREQ_A, 1.0)]
        result = drift_transform(tones, dimension=ToneDimension.FREQUENCY, rate=RATE)
        
        assert len(result) == 1
        assert result[0].frequency == pytest.approx(EXPECTED_FREQ)

    def test_positive_rate_upward_drift(self):
        # Rate 0.1. Step = 44.
        # Tones: [440, 440, 440]
        # Result: [484, 528, 572]
        FREQ_A = 440.0
        RATE = 0.1
        STEP = FREQ_A * RATE
        
        tones = [Tone(FREQ_A, 1.0), Tone(FREQ_A, 1.0), Tone(FREQ_A, 1.0)]
        result = drift_transform(tones, dimension=ToneDimension.FREQUENCY, rate=RATE)
        
        assert len(result) == 3
        assert result[0].frequency == pytest.approx(FREQ_A + STEP)
        assert result[1].frequency == pytest.approx(FREQ_A + (2 * STEP))
        assert result[2].frequency == pytest.approx(FREQ_A + (3 * STEP))

    def test_negative_rate_downward_drift(self):
        # Rate -0.1. Step = -44.
        # Tones: [440, 440, 440]
        # Result: [396, 352, 308]
        FREQ_A = 440.0
        RATE = -0.1
        STEP = FREQ_A * RATE
        
        tones = [Tone(FREQ_A, 1.0), Tone(FREQ_A, 1.0), Tone(FREQ_A, 1.0)]
        result = drift_transform(tones, dimension=ToneDimension.FREQUENCY, rate=RATE)
        
        assert len(result) == 3
        assert result[0].frequency == pytest.approx(FREQ_A + STEP)
        assert result[1].frequency == pytest.approx(FREQ_A + (2 * STEP))
        assert result[2].frequency == pytest.approx(FREQ_A + (3 * STEP))

    def test_zero_rate_is_identity(self):
        # A rate of 0 means "no drift", so the frequency dimension
        # must remain untouched regardless of sequence length.
        FREQ_A = 440.0
        FREQ_B = 880.0
        
        tones = [Tone(FREQ_A, 1.0), Tone(FREQ_B, 1.0)]
        result = drift_transform(tones, dimension=ToneDimension.FREQUENCY, rate=0.0)
        
        assert len(result) == 2
        assert result[0].frequency == pytest.approx(FREQ_A)
        assert result[1].frequency == pytest.approx(FREQ_B)

    def test_string_dimension(self):
        FREQ_A = 440.0
        RATE = 0.1
        EXPECTED_FREQ = FREQ_A + (FREQ_A * RATE)
        
        tones = [Tone(FREQ_A, 1.0)]
        result = drift_transform(tones, dimension="FREQUENCY", rate=RATE)
        
        assert result[0].frequency == pytest.approx(EXPECTED_FREQ)

    def test_preserves_untouched_fields(self):
        # When drifting frequency, the other tone fields (duration, sample_rate,
        # amplitude) must pass through unchanged. This guards against accidental
        # mutation of unrelated dimensions.
        CUSTOM_SAMPLE_RATE = 22050
        DURATION = 0.75
        AMPLITUDE = 0.6
        
        tones = [Tone(440.0, DURATION, sample_rate=CUSTOM_SAMPLE_RATE, amplitude=AMPLITUDE)]
        result = drift_transform(tones, dimension=ToneDimension.FREQUENCY, rate=0.1)
        
        assert result[0].duration == pytest.approx(DURATION)
        assert result[0].sample_rate == CUSTOM_SAMPLE_RATE
        assert result[0].amplitude == pytest.approx(AMPLITUDE)


class TestDriftAmplitude:
    def test_positive_rate_crescendo(self):
        # Rate 0.2. Step = 0.1.
        # Tones: [0.5, 0.5, 0.5]
        # Result: [0.6, 0.7, 0.8]
        AMP = 0.5
        RATE = 0.2
        STEP = AMP * RATE
        
        tones = [Tone(440, 1.0, amplitude=AMP), Tone(440, 1.0, amplitude=AMP), Tone(440, 1.0, amplitude=AMP)]
        result = drift_transform(tones, dimension=ToneDimension.AMPLITUDE, rate=RATE)
        
        assert len(result) == 3
        assert result[0].amplitude == pytest.approx(AMP + STEP)
        assert result[1].amplitude == pytest.approx(AMP + (2 * STEP))
        assert result[2].amplitude == pytest.approx(AMP + (3 * STEP))

    def test_negative_rate_diminuendo(self):
        # Rate -0.2. Step = -0.1.
        # Tones: [0.5, 0.5, 0.5]
        # Result: [0.4, 0.3, 0.2]
        AMP = 0.5
        RATE = -0.2
        STEP = AMP * RATE
        
        tones = [Tone(440, 1.0, amplitude=AMP), Tone(440, 1.0, amplitude=AMP), Tone(440, 1.0, amplitude=AMP)]
        result = drift_transform(tones, dimension=ToneDimension.AMPLITUDE, rate=RATE)
        
        assert len(result) == 3
        assert result[0].amplitude == pytest.approx(AMP + STEP)
        assert result[1].amplitude == pytest.approx(AMP + (2 * STEP))
        assert result[2].amplitude == pytest.approx(AMP + (3 * STEP))

    def test_clamp_at_max_amplitude(self):
        # Rate 1.0. Step = 0.5.
        # Tones: [0.5, 0.5, 0.5]
        # Result: [1.0, 1.0, 1.0] (Clamped)
        AMP = 0.5
        RATE = 1.0
        
        tones = [Tone(440, 1.0, amplitude=AMP), Tone(440, 1.0, amplitude=AMP), Tone(440, 1.0, amplitude=AMP)]
        result = drift_transform(tones, dimension=ToneDimension.AMPLITUDE, rate=RATE)
        
        assert result[0].amplitude == 1.0
        assert result[1].amplitude == 1.0
        assert result[2].amplitude == 1.0

    def test_clamp_at_zero_amplitude(self):
        # Rate -1.0. Step = -0.5.
        # Tones: [0.5, 0.5, 0.5]
        # Result: [0.0, 0.0, 0.0] (Clamped)
        AMP = 0.5
        RATE = -1.0
        
        tones = [Tone(440, 1.0, amplitude=AMP), Tone(440, 1.0, amplitude=AMP), Tone(440, 1.0, amplitude=AMP)]
        result = drift_transform(tones, dimension=ToneDimension.AMPLITUDE, rate=RATE)
        
        assert result[0].amplitude == 0.0
        assert result[1].amplitude == 0.0
        assert result[2].amplitude == 0.0

    def test_zero_rate_is_identity(self):
        # A rate of 0 means "no drift", so amplitude must remain untouched.
        AMP = 0.5
        
        tones = [Tone(440, 1.0, amplitude=AMP), Tone(440, 1.0, amplitude=AMP)]
        result = drift_transform(tones, dimension=ToneDimension.AMPLITUDE, rate=0.0)
        
        assert result[0].amplitude == pytest.approx(AMP)
        assert result[1].amplitude == pytest.approx(AMP)


class TestDriftDuration:
    def test_positive_rate_accelerando(self):
        # Rate 0.5. Step = 0.25.
        # Tones: [0.5, 0.5, 0.5]
        # Result: [0.75, 1.0, 1.25]
        DUR = 0.5
        RATE = 0.5
        STEP = DUR * RATE
        
        tones = [Tone(440, DUR), Tone(440, DUR), Tone(440, DUR)]
        result = drift_transform(tones, dimension=ToneDimension.DURATION, rate=RATE)
        
        assert len(result) == 3
        assert result[0].duration == pytest.approx(DUR + STEP)
        assert result[1].duration == pytest.approx(DUR + (2 * STEP))
        assert result[2].duration == pytest.approx(DUR + (3 * STEP))

    def test_negative_rate_ritardando(self):
        # Rate -0.5. Step = -0.25.
        # Tones: [0.5, 0.5, 0.5]
        # Result: [0.25, 0.0, 0.0] (Clamped at 0)
        DUR = 0.5
        RATE = -0.5
        STEP = DUR * RATE
        
        tones = [Tone(440, DUR), Tone(440, DUR), Tone(440, DUR)]
        result = drift_transform(tones, dimension=ToneDimension.DURATION, rate=RATE)
        
        assert len(result) == 3
        assert result[0].duration == pytest.approx(DUR + STEP)
        assert result[1].duration == pytest.approx(max(0.0, DUR + (2 * STEP)))
        assert result[2].duration == pytest.approx(max(0.0, DUR + (3 * STEP)))

    def test_clamp_at_zero_duration(self):
        # Rate -2.0. Step = -1.0.
        # Tones: [0.5, 0.5, 0.5]
        # Result: [0.0, 0.0, 0.0] (Clamped)
        DUR = 0.5
        RATE = -2.0
        
        tones = [Tone(440, DUR), Tone(440, DUR), Tone(440, DUR)]
        result = drift_transform(tones, dimension=ToneDimension.DURATION, rate=RATE)
        
        assert result[0].duration == 0.0
        assert result[1].duration == 0.0
        assert result[2].duration == 0.0

    def test_zero_rate_is_identity(self):
        # A rate of 0 means "no drift", so duration must remain untouched.
        DUR = 0.5
        
        tones = [Tone(440, DUR), Tone(440, DUR)]
        result = drift_transform(tones, dimension=ToneDimension.DURATION, rate=0.0)
        
        assert result[0].duration == pytest.approx(DUR)
        assert result[1].duration == pytest.approx(DUR)


class TestScoreDriftRegistration:
    def test_score_drift_registered(self):
        # The parser must expose `score_drift` so compositions can use it
        # as a top-level score transform affecting all voices uniformly.
        assert "score_drift" in TRANSFORMS

    def test_score_drift_has_correct_scope(self):
        # `score_drift` must apply across all voices of a score, matching
        # the pattern of other `score_*` transforms (e.g. score_reverse, score_scale).
        descriptor = TRANSFORMS["score_drift"]
        assert descriptor.scope == TransformScope.ALL_VOICES

    def test_score_drift_wraps_drift_transform(self):
        descriptor = TRANSFORMS["score_drift"]
        assert descriptor.transform is drift_transform


class TestScoreDriftApplication:
    def test_score_drift_applies_to_all_voices(self):
        # A single `score_drift` declaration at the composition level should
        # shift every voice's tones by the configured rate, uniformly.
        RATE = 0.1
        FREQ_A = 440.0
        FREQ_B = 220.0

        composition_document: CompositionDocument = {
            "motifs": {
                "high": [f"{FREQ_A}:0.3", f"{FREQ_A}:0.3"],
                "low": [f"{FREQ_B}:0.3", f"{FREQ_B}:0.3"],
            },
            "composition": {
                "voices": [
                    {"phrases": [{"motifs": ["high"]}]},
                    {"phrases": [{"motifs": ["low"]}]},
                ],
                "score_transforms": [
                    {"name": "score_drift", "params": {"dimension": "FREQUENCY", "rate": RATE}},
                ],
            },
        }

        score = parse_composition(composition_document)

        assert len(score.voices) == 2

        expected_high_step = FREQ_A * RATE
        assert score.voices[0].tones[0].frequency == pytest.approx(FREQ_A + expected_high_step)
        assert score.voices[0].tones[1].frequency == pytest.approx(FREQ_A + (2 * expected_high_step))

        expected_low_step = FREQ_B * RATE
        assert score.voices[1].tones[0].frequency == pytest.approx(FREQ_B + expected_low_step)
        assert score.voices[1].tones[1].frequency == pytest.approx(FREQ_B + (2 * expected_low_step))
