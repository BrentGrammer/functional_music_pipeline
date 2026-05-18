import numpy as np
import pytest

from composition.parser import parse_composition
from composition.schema import CompositionDocument
from score_model.math_constants import FEIGENBAUM_DELTA, GOLDEN_RATIO
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.tone_utils import make_silence_tone
from score_model.traversal import iter_voice_tones
from score_model.voice import Voice
from transforms.counterpoint.fugue import add_pedal_tone, stretto
from transforms.registry import SCORE_TRANSFORMS


class TestStretto:
    def test_stretto_appends_fixed_spacing_entries_from_motif(self):
        score = Score(
            [
                Voice([Phrase([Motif("subject", [Tone(440.0, duration=0.5), Tone(660.0, duration=0.25)])])]),
                Voice([Phrase([Motif("counter", [Tone(880.0, duration=0.25)])])]),
            ]
        )

        result = stretto(score, motif="subject", num_times=3, spacing=0.75)

        assert len(result.voices) == 5
        assert iter_voice_tones(result.voices[1])[0].frequency == pytest.approx(880.0)

        first_entry = iter_voice_tones(result.voices[2])
        assert len(first_entry) == 2
        assert first_entry[0].frequency == pytest.approx(440.0)
        assert first_entry[1].frequency == pytest.approx(660.0)

        second_entry = iter_voice_tones(result.voices[3])
        silence = make_silence_tone(0.75)
        assert second_entry[0].frequency == pytest.approx(silence.frequency)
        assert second_entry[0].duration == pytest.approx(silence.duration)
        assert second_entry[0].amplitude == pytest.approx(silence.amplitude)
        assert second_entry[1].frequency == pytest.approx(440.0)

        third_entry = iter_voice_tones(result.voices[4])
        silence = make_silence_tone(1.5)
        assert third_entry[0].frequency == pytest.approx(silence.frequency)
        assert third_entry[0].duration == pytest.approx(silence.duration)
        assert third_entry[0].amplitude == pytest.approx(silence.amplitude)
        assert third_entry[1].frequency == pytest.approx(440.0)

    def test_stretto_copies_motif_tones(self):
        original_tone = Tone(440.0, duration=0.5, amplitude=0.25)
        score = Score(
            [
                Voice([Phrase([Motif("subject", [original_tone])])]),
            ]
        )

        result = stretto(score, motif="subject", num_times=1, spacing=0.75)

        generated_voice_tones = iter_voice_tones(result.voices[1])
        assert generated_voice_tones[0] is not original_tone
        assert generated_voice_tones[0].frequency == pytest.approx(original_tone.frequency)
        assert generated_voice_tones[0].duration == pytest.approx(original_tone.duration)
        assert generated_voice_tones[0].amplitude == pytest.approx(original_tone.amplitude)

    def test_stretto_rejects_unknown_motif(self):
        with pytest.raises(ValueError, match="not found"):
            stretto(Score(), motif="missing", num_times=1, spacing=0.75)

    def test_stretto_rejects_num_times_less_than_one(self):
        score = Score([Voice([Phrase([Motif("subject", [Tone(440.0)])])])])
        with pytest.raises(ValueError, match="num_times"):
            stretto(score, motif="subject", num_times=0, spacing=0.75)

    def test_stretto_rejects_invalid_spacing(self):
        score = Score([Voice([Phrase([Motif("subject", [Tone(440.0)])])])])
        with pytest.raises(ValueError, match="spacing"):
            stretto(
                score,
                motif="subject",
                num_times=1,
                spacing=[],
            )

    def test_stretto_rejects_non_positive_spacing(self):
        score = Score([Voice([Phrase([Motif("subject", [Tone(440.0)])])])])
        with pytest.raises(ValueError, match="spacing"):
            stretto(
                score,
                motif="subject",
                num_times=1,
                spacing=0,
            )

    def test_stretto_uses_named_spacing_values(self):
        motif_duration = 0.5
        score = Score([Voice([Phrase([Motif("subject", [Tone(440.0, duration=motif_duration)])])])])
        golden_ratio_spacing = motif_duration / GOLDEN_RATIO
        feigenbaum_spacing = motif_duration / FEIGENBAUM_DELTA

        result = stretto(score, motif="subject", num_times=3, spacing="golden_ratio")

        silence = make_silence_tone(golden_ratio_spacing)
        assert iter_voice_tones(result.voices[2])[0].frequency == pytest.approx(silence.frequency)
        assert iter_voice_tones(result.voices[2])[0].duration == pytest.approx(silence.duration)
        assert iter_voice_tones(result.voices[2])[0].amplitude == pytest.approx(silence.amplitude)

        silence = make_silence_tone(golden_ratio_spacing * 2)
        assert iter_voice_tones(result.voices[3])[0].frequency == pytest.approx(silence.frequency)
        assert iter_voice_tones(result.voices[3])[0].duration == pytest.approx(silence.duration)
        assert iter_voice_tones(result.voices[3])[0].amplitude == pytest.approx(silence.amplitude)

        result = stretto(score, motif="subject", num_times=3, spacing="feigenbaum_delta")

        silence = make_silence_tone(feigenbaum_spacing)
        assert iter_voice_tones(result.voices[2])[0].frequency == pytest.approx(silence.frequency)
        assert iter_voice_tones(result.voices[2])[0].duration == pytest.approx(silence.duration)
        assert iter_voice_tones(result.voices[2])[0].amplitude == pytest.approx(silence.amplitude)

        silence = make_silence_tone(feigenbaum_spacing * 2)
        assert iter_voice_tones(result.voices[3])[0].frequency == pytest.approx(silence.frequency)
        assert iter_voice_tones(result.voices[3])[0].duration == pytest.approx(silence.duration)
        assert iter_voice_tones(result.voices[3])[0].amplitude == pytest.approx(silence.amplitude)

    def test_stretto_rejects_unknown_spacing_name(self):
        score = Score([Voice([Phrase([Motif("subject", [Tone(440.0)])])])])
        with pytest.raises(ValueError, match="spacing"):
            stretto(
                score,
                motif="subject",
                num_times=1,
                spacing="unknown_ratio",
            )

    def test_stretto_rejects_empty_spacing_string(self):
        empty_spacing_name = ""
        score = Score([Voice([Phrase([Motif("subject", [Tone(440.0)])])])])

        with pytest.raises(ValueError, match="non-empty string"):
            stretto(
                score,
                motif="subject",
                num_times=1,
                spacing=empty_spacing_name,
            )

    def test_stretto_golden_ratio_spacing_should_overlap_against_subject_duration(self):
        score = Score([Voice([Phrase([Motif("subject", [Tone(440.0, duration=0.5), Tone(660.0, duration=0.5)])])])])

        result = stretto(score, motif="subject", num_times=2, spacing="golden_ratio")

        subject_duration = sum(tone.duration for tone in iter_voice_tones(score.voices[0]))
        expected_overlap_offset = subject_duration / GOLDEN_RATIO

        assert iter_voice_tones(result.voices[0])[0].frequency == pytest.approx(440.0)
        assert iter_voice_tones(result.voices[2])[0].frequency == pytest.approx(0)
        assert iter_voice_tones(result.voices[2])[0].duration == pytest.approx(expected_overlap_offset)
        assert expected_overlap_offset < subject_duration


class TestPedalTone:
    def test_add_pedal_tone_appends_voice(self):
        tones = [Tone(440.0, duration=2.0)]
        score = Score([Voice([Phrase([Motif("seed", tones)])])])
        pedal_tone_freq = 339.81

        result = add_pedal_tone(score, frequency=pedal_tone_freq)

        assert len(result.voices) == len(tones) + 1
        assert len(iter_voice_tones(result.voices[1])) == 1
        assert iter_voice_tones(result.voices[1])[0].frequency == pytest.approx(pedal_tone_freq)

    def test_pedal_tone_duration_matches_longest_voice(self):
        score = Score([
            Voice([Phrase([Motif("v1", [Tone(440.0, duration=1.0), Tone(550.0, duration=1.0)])])]),
            Voice([Phrase([Motif("v2", [Tone(330.0, duration=0.5)])])]),
        ])

        longest_duration = max(
            sum(tone.duration for tone in iter_voice_tones(voice))
            for voice in score.voices
        )

        result = add_pedal_tone(score, frequency=130.81)

        # The pedal tone is always appended as the last voice.
        pedal_voice = result.voices[-1]
        assert iter_voice_tones(pedal_voice)[0].duration == pytest.approx(longest_duration)

    def test_pedal_tone_uses_sensible_default_amplitude(self):
        score = Score([Voice([Phrase([Motif("seed", [Tone(440.0, duration=1.0)])])])])

        result = add_pedal_tone(score, frequency=130.81)

        assert 0.0 < iter_voice_tones(result.voices[-1])[0].amplitude <= 1.0

    def test_pedal_tone_rejects_non_positive_frequency(self):
        with pytest.raises(ValueError, match="frequency"):
            add_pedal_tone(Score(), frequency=0)

    def test_pedal_tone_empty_score_uses_fallback_duration(self):
        """Empty scores fall back to a one-second pedal tone so the output remains audible."""
        result = add_pedal_tone(Score(), frequency=130.81)

        assert iter_voice_tones(result.voices[0])[0].duration > 0


class TestPedalToneRegistration:
    def test_add_pedal_tone_registered(self):
        descriptor = SCORE_TRANSFORMS["add_pedal_tone"]
        assert descriptor is not None


class TestPedalToneComposition:
    def test_add_pedal_tone_applies_from_composition_json(self):
        composition_document: CompositionDocument = {
            "motifs": {
                "subject": ["261.63:0.5", "293.66:0.5"],
            },
            "composition": {
                "voices": [
                    {"phrases": [{"motifs": ["subject"]}]},
                ],
                "score_transforms": [
                    {
                        "name": "add_pedal_tone",
                        "params": {
                            "frequency": 130.81,
                        },
                    },
                ],
            },
        }

        score = parse_composition(composition_document)

        assert len(score.voices) == 2
        assert iter_voice_tones(score.voices[1])[0].frequency == pytest.approx(130.81)
        assert iter_voice_tones(score.voices[1])[0].duration == pytest.approx(1.0)


class TestStrettoComposition:
    def test_stretto_applies_from_composition_json(self):
        composition_document: CompositionDocument = {
            "motifs": {
                "subject": ["261.63:0.5", "329.63:0.25"],
            },
            "composition": {
                "voices": [
                    {"phrases": [{"motifs": ["subject"]}]},
                ],
                "score_transforms": [
                    {
                        "name": "stretto",
                        "params": {
                            "motif": "subject",
                            "num_times": 3,
                            "spacing": "golden_ratio",
                        },
                    }
                ],
            },
        }

        score = parse_composition(composition_document)

        assert len(score.voices) == 4
        assert iter_voice_tones(score.voices[0])[0].frequency == pytest.approx(261.63)
        assert iter_voice_tones(score.voices[1])[0].frequency == pytest.approx(261.63)
        assert iter_voice_tones(score.voices[2])[0].frequency == 0
        assert iter_voice_tones(score.voices[2])[0].duration == pytest.approx((0.5 + 0.25) / GOLDEN_RATIO)
        assert iter_voice_tones(score.voices[3])[0].frequency == 0
        assert iter_voice_tones(score.voices[3])[0].duration == pytest.approx(((0.5 + 0.25) / GOLDEN_RATIO) * 2)

    def test_stretto_rendering_overlaps_voice_onsets(self):
        composition_document: CompositionDocument = {
            "motifs": {
                "subject": [
                    "261.63:0.5",
                    "329.63:0.5",
                ],
            },
            "composition": {
                "voices": [
                    {"phrases": [{"motifs": ["subject"]}]},
                ],
                "score_transforms": [
                    {
                        "name": "stretto",
                        "params": {
                            "motif": "subject",
                            "num_times": 2,
                            "spacing": "golden_ratio",
                        },
                    }
                ],
            },
        }

        score = parse_composition(composition_document)
        voice_waveforms = []
        for voice in score.voices:
            tone_waveforms = [tone.generate_tone() for tone in iter_voice_tones(voice)]
            if tone_waveforms:
                voice_waveforms.append(np.concatenate(tone_waveforms))
            else:
                voice_waveforms.append(np.array([], dtype=np.int16))

        first_voice_audible = np.flatnonzero(voice_waveforms[0])
        second_voice_audible = np.flatnonzero(voice_waveforms[1])

        assert 0 < second_voice_audible[0] < first_voice_audible[-1]
