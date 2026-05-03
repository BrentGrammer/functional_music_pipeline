import numpy as np
import pytest

from composition.parser import TRANSFORMS, parse_composition
from score_model.math_constants import FEIGENBAUM_DELTA, GOLDEN_RATIO
from score_model.score import Score
from score_model.tone import Tone
from score_model.tone_utils import make_silence_tone
from score_model.voice import Voice
from transforms.base import TransformScope
from transforms.fugue import add_pedal_point, stretto

class TestStretto:
    def test_stretto_appends_fixed_spacing_entries_from_motif(self):
        score = Score([Voice([Tone(880.0, duration=0.25)])])
        parsed_motifs = {
            "subject": [Tone(440.0, duration=0.5), Tone(660.0, duration=0.25)],
        }

        result = stretto(score, parsed_motifs, motif="subject", num_times=3, spacing=0.75)

        assert len(result.voices) == 4
        assert result.voices[0].tones[0].frequency == pytest.approx(880.0)

        first_entry = result.voices[1].tones
        assert len(first_entry) == 2
        assert first_entry[0].frequency == pytest.approx(440.0)
        assert first_entry[1].frequency == pytest.approx(660.0)

        second_entry = result.voices[2].tones
        silence = make_silence_tone(0.75)
        assert second_entry[0].frequency == pytest.approx(silence.frequency)
        assert second_entry[0].duration == pytest.approx(silence.duration)
        assert second_entry[0].amplitude == pytest.approx(silence.amplitude)
        assert second_entry[1].frequency == pytest.approx(440.0)

        third_entry = result.voices[3].tones
        silence = make_silence_tone(1.5)
        assert third_entry[0].frequency == pytest.approx(silence.frequency)
        assert third_entry[0].duration == pytest.approx(silence.duration)
        assert third_entry[0].amplitude == pytest.approx(silence.amplitude)
        assert third_entry[1].frequency == pytest.approx(440.0)

    def test_stretto_copies_motif_tones(self):
        score = Score()
        original_tone = Tone(440.0, duration=0.5, amplitude=0.25)
        parsed_motifs = {"subject": [original_tone]}

        result = stretto(score, parsed_motifs, motif="subject", num_times=1, spacing=0.75)

        assert result.voices[0].tones[0] is not original_tone
        assert result.voices[0].tones[0].frequency == pytest.approx(original_tone.frequency)
        assert result.voices[0].tones[0].duration == pytest.approx(original_tone.duration)
        assert result.voices[0].tones[0].amplitude == pytest.approx(original_tone.amplitude)

    def test_stretto_rejects_unknown_motif(self):
        with pytest.raises(ValueError, match="not found"):
            stretto(Score(), {}, motif="missing", num_times=1, spacing=0.75)

    def test_stretto_rejects_num_times_less_than_one(self):
        with pytest.raises(ValueError, match="num_times"):
            stretto(Score(), {"subject": [Tone(440.0)]}, motif="subject", num_times=0, spacing=0.75)

    def test_stretto_rejects_invalid_spacing(self):
        with pytest.raises(ValueError, match="spacing"):
            stretto(
                Score(),
                {"subject": [Tone(440.0)]},
                motif="subject",
                num_times=1,
                spacing=[],
            )

    def test_stretto_rejects_non_positive_spacing(self):
        with pytest.raises(ValueError, match="spacing"):
            stretto(
                Score(),
                {"subject": [Tone(440.0)]},
                motif="subject",
                num_times=1,
                spacing=0,
            )

    def test_stretto_uses_named_spacing_values(self):
        score = Score()
        motif_duration = 0.5
        parsed_motifs = {"subject": [Tone(440.0, duration=motif_duration)]}
        golden_ratio_spacing = motif_duration / GOLDEN_RATIO
        feigenbaum_spacing = motif_duration / FEIGENBAUM_DELTA

        result = stretto(score, parsed_motifs, motif="subject", num_times=3, spacing="golden_ratio")

        silence = make_silence_tone(golden_ratio_spacing)
        assert result.voices[1].tones[0].frequency == pytest.approx(silence.frequency)
        assert result.voices[1].tones[0].duration == pytest.approx(silence.duration)
        assert result.voices[1].tones[0].amplitude == pytest.approx(silence.amplitude)

        silence = make_silence_tone(golden_ratio_spacing * 2)
        assert result.voices[2].tones[0].frequency == pytest.approx(silence.frequency)
        assert result.voices[2].tones[0].duration == pytest.approx(silence.duration)
        assert result.voices[2].tones[0].amplitude == pytest.approx(silence.amplitude)

        result = stretto(score, parsed_motifs, motif="subject", num_times=3, spacing="feigenbaum_delta")

        silence = make_silence_tone(feigenbaum_spacing)
        assert result.voices[1].tones[0].frequency == pytest.approx(silence.frequency)
        assert result.voices[1].tones[0].duration == pytest.approx(silence.duration)
        assert result.voices[1].tones[0].amplitude == pytest.approx(silence.amplitude)

        silence = make_silence_tone(feigenbaum_spacing * 2)
        assert result.voices[2].tones[0].frequency == pytest.approx(silence.frequency)
        assert result.voices[2].tones[0].duration == pytest.approx(silence.duration)
        assert result.voices[2].tones[0].amplitude == pytest.approx(silence.amplitude)

    def test_stretto_rejects_unknown_spacing_name(self):
        with pytest.raises(ValueError, match="spacing"):
            stretto(
                Score(),
                {"subject": [Tone(440.0)]},
                motif="subject",
                num_times=1,
                spacing="unknown_ratio",
            )

    def test_stretto_golden_ratio_spacing_should_overlap_against_subject_duration(self):
        score = Score()
        parsed_motifs = {
            "subject": [
                Tone(440.0, duration=0.5),
                Tone(660.0, duration=0.5),
            ]
        }

        result = stretto(score, parsed_motifs, motif="subject", num_times=2, spacing="golden_ratio")

        subject_duration = sum(tone.duration for tone in parsed_motifs["subject"])
        expected_overlap_offset = subject_duration / GOLDEN_RATIO

        assert result.voices[0].tones[0].frequency == pytest.approx(440.0)
        assert result.voices[1].tones[0].frequency == pytest.approx(0)
        assert result.voices[1].tones[0].duration == pytest.approx(expected_overlap_offset)
        assert expected_overlap_offset < subject_duration


class TestPedalPoint:
    def test_add_sustained_pedal_point_appends_voice(self):
        score = Score([Voice([Tone(440.0, duration=0.5)])])

        result = add_pedal_point(score, frequency=130.81, duration=2.0, amplitude=0.25)

        assert len(result.voices) == 2
        assert len(result.voices[0].tones) == 1
        assert len(result.voices[1].tones) == 1
        assert result.voices[1].tones[0].frequency == pytest.approx(130.81)
        assert result.voices[1].tones[0].duration == pytest.approx(2.0)
        assert result.voices[1].tones[0].amplitude == pytest.approx(0.25)

    def test_add_repeated_pedal_point_uses_pulse_duration(self):
        score = Score()

        result = add_pedal_point(
            score,
            frequency=130.81,
            duration=1.25,
            amplitude=0.4,
            mode="repeat",
            pulse_duration=0.5,
        )

        pedal_tones = result.voices[0].tones
        assert len(pedal_tones) == 3
        assert [tone.duration for tone in pedal_tones] == pytest.approx([0.5, 0.5, 0.25])
        assert all(tone.frequency == pytest.approx(130.81) for tone in pedal_tones)
        assert all(tone.amplitude == pytest.approx(0.4) for tone in pedal_tones)

    def test_repeat_mode_requires_pulse_duration(self):
        with pytest.raises(ValueError, match="pulse_duration"):
            add_pedal_point(Score(), frequency=130.81, duration=1.0, mode="repeat")

    def test_rejects_invalid_duration(self):
        with pytest.raises(ValueError, match="duration"):
            add_pedal_point(Score(), frequency=130.81, duration=0)

    def test_rejects_invalid_frequency(self):
        with pytest.raises(ValueError, match="frequency"):
            add_pedal_point(Score(), frequency=0, duration=1.0)

    def test_rejects_invalid_amplitude(self):
        with pytest.raises(ValueError, match="amplitude"):
            add_pedal_point(Score(), frequency=130.81, duration=1.0, amplitude=1.5)


class TestPedalPointRegistration:
    def test_add_pedal_point_registered(self):
        assert "add_pedal_point" in TRANSFORMS

    def test_add_pedal_point_has_score_scope(self):
        assert TRANSFORMS["add_pedal_point"].scope == TransformScope.SCORE

    def test_add_pedal_point_wraps_transform(self):
        assert TRANSFORMS["add_pedal_point"].transform is add_pedal_point


class TestPedalPointComposition:
    def test_add_pedal_point_applies_from_composition_json(self):
        composition_document = {
            "motifs": {
                "subject": ["261.63:0.5", "293.66:0.5"],
            },
            "composition": {
                "voices": [
                    {"phrases": [{"motifs": ["subject"]}]},
                ],
                "score_transforms": [
                    {
                        "name": "add_pedal_point",
                        "params": {
                            "frequency": 130.81,
                            "duration": 1.0,
                            "amplitude": 0.3,
                        },
                    },
                ],
            },
        }

        score = parse_composition(composition_document)

        assert len(score.voices) == 2
        assert score.voices[1].tones[0].frequency == pytest.approx(130.81)
        assert score.voices[1].tones[0].duration == pytest.approx(1.0)
        assert score.voices[1].tones[0].amplitude == pytest.approx(0.3)


class TestStrettoComposition:
    def test_stretto_applies_from_composition_json(self):
        composition_document = {
            "motifs": {
                "subject": ["261.63:0.5", "329.63:0.25"],
            },
            "composition": {
                "voices": [],
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

        assert len(score.voices) == 3
        assert score.voices[0].tones[0].frequency == pytest.approx(261.63)
        assert score.voices[1].tones[0].frequency == 0
        assert score.voices[1].tones[0].duration == pytest.approx((0.5 + 0.25) / GOLDEN_RATIO)
        assert score.voices[2].tones[0].frequency == 0
        assert score.voices[2].tones[0].duration == pytest.approx(((0.5 + 0.25) / GOLDEN_RATIO) * 2)

    def test_stretto_rendering_overlaps_voice_onsets(self):
        composition_document = {
            "motifs": {
                "subject": [
                    "261.63:0.5",
                    "329.63:0.5",
                ],
            },
            "composition": {
                "voices": [],
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
            tone_waveforms = [tone.generate_tone() for tone in voice]
            if tone_waveforms:
                voice_waveforms.append(np.concatenate(tone_waveforms))
            else:
                voice_waveforms.append(np.array([], dtype=np.int16))

        first_voice_audible = np.flatnonzero(voice_waveforms[0])
        second_voice_audible = np.flatnonzero(voice_waveforms[1])

        assert 0 < second_voice_audible[0] < first_voice_audible[-1]
