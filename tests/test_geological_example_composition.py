import pytest

from composition.parser import parse_composition, parse_motifs
from composition.schema import CompositionDocument
from score_model.score import Score


def _build_geological_example_composition() -> dict:
    return {
        "description": (
            "A showcase of the four geological profiles. Each voice plays the same C major arpeggio, "
            "but has a different stochastic transform applied to a different musical dimension "
            "(frequency, duration, or amplitude). A score-level transform is also applied to all voices."
        ),
        "motifs": {
            "c_major_arpeggio": [
                "261.63:0.5",
                "329.63:0.5",
                "392.00:0.5",
                "523.25:0.5",
            ]
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {
                            "motifs": ["c_major_arpeggio"],
                            "transforms": [
                                {
                                    "name": "geological",
                                    "params": {
                                        "profile": {"type": "weierstrass", "params": {"seed": 42}},
                                        "dimension": "frequency",
                                        "max_deviation": 0.05,
                                    },
                                }
                            ],
                        }
                    ]
                },
                {
                    "phrases": [
                        {
                            "motifs": ["c_major_arpeggio"],
                            "transforms": [
                                {
                                    "name": "geological",
                                    "params": {
                                        "profile": {"type": "terraced", "params": {"seed": 42}},
                                        "dimension": "duration",
                                        "max_deviation": 0.5,
                                    },
                                }
                            ],
                        }
                    ]
                },
                {
                    "phrases": [
                        {
                            "motifs": ["c_major_arpeggio"],
                            "transforms": [
                                {
                                    "name": "geological",
                                    "params": {
                                        "profile": {"type": "cellular_automata", "params": {"seed": 42}},
                                        "dimension": "amplitude",
                                        "max_deviation": 0.4,
                                    },
                                }
                            ],
                        }
                    ]
                },
                {
                    "phrases": [
                        {
                            "motifs": ["c_major_arpeggio"],
                            "transforms": [
                                {
                                    "name": "geological",
                                    "params": {
                                        "profile": {"type": "ridged_multifractal", "params": {"seed": 42}},
                                        "dimension": "amplitude",
                                        "max_deviation": 0.9,
                                    },
                                }
                            ],
                        }
                    ]
                },
            ],
            "score_transforms": [
                {
                    "name": "score_geological",
                    "params": {
                        "profile": {"type": "weierstrass", "params": {"seed": 100}},
                        "dimension": "amplitude",
                        "max_deviation": 0.1,
                    },
                }
            ],
        },
    }


class TestGeologicalExampleComposition:
    def test_loads_and_parses_without_error(self):
        # This test ensures the example composition file is valid JSON and
        # can be successfully parsed by the composition engine, serving as a
        # basic integration test for the unified geological transform API.
        composition_data: CompositionDocument = _build_geological_example_composition()

        score = parse_composition(composition_data)

        assert isinstance(score, Score)
        assert len(score.voices) == 4

        # The motif "c_major_arpeggio" has 4 tones, so each voice should have 4 tones.
        for voice in score.voices:
            assert len(voice.tones) == 4

    def test_parsing_is_deterministic(self):
        # Geological transforms are seeded, so repeated parsing of the same
        # composition must yield identical musical output. This test locks in
        # that invariant.
        composition_data: CompositionDocument = _build_geological_example_composition()

        score1 = parse_composition(composition_data)
        score2 = parse_composition(composition_data)

        assert len(score1.voices) == len(score2.voices)

        for voice1, voice2 in zip(score1.voices, score2.voices):
            assert len(voice1.tones) == len(voice2.tones)
            for tone1, tone2 in zip(voice1.tones, voice2.tones):
                assert tone1.frequency == pytest.approx(tone2.frequency)
                assert tone1.duration == pytest.approx(tone2.duration)
                assert tone1.amplitude == pytest.approx(tone2.amplitude)

    def test_structural_invariants(self):
        # Verifies the user-visible guarantees of the geological transform API
        # at the composition boundary.
        composition_data: CompositionDocument = _build_geological_example_composition()

        score = parse_composition(composition_data)

        # Retrieve original tones for comparison by reusing the motif parser.
        # This avoids duplicating tone-string parsing logic in the test.
        parsed_motifs = parse_motifs(composition_data["motifs"])
        original_motif_tones = parsed_motifs["c_major_arpeggio"]

        # Voice 1: Weierstrass on Frequency
        voice1_tones = score.voices[0].tones
        max_deviation_v1 = composition_data["composition"]["voices"][0]["phrases"][0]["transforms"][0]["params"]["max_deviation"]
        for i, transformed_tone in enumerate(voice1_tones):
            original_freq = original_motif_tones[i].frequency
            assert original_freq * (1 - max_deviation_v1) <= transformed_tone.frequency <= original_freq * (1 + max_deviation_v1)

        # Voice 2: Terraced Brownian on Duration
        voice2_tones = score.voices[1].tones
        max_deviation_v2 = composition_data["composition"]["voices"][1]["phrases"][0]["transforms"][0]["params"]["max_deviation"]
        for i, transformed_tone in enumerate(voice2_tones):
            original_dur = original_motif_tones[i].duration
            assert original_dur * (1 - max_deviation_v2) <= transformed_tone.duration <= original_dur * (1 + max_deviation_v2)
            assert transformed_tone.duration > 0

        # All Voices: Verify score-level amplitude transform and general amplitude invariants
        for i, voice in enumerate(score.voices):
            for j, transformed_tone in enumerate(voice.tones):
                # Check invariant: amplitude must be in valid range
                assert 0.0 <= transformed_tone.amplitude <= 1.0

                # Check effect: score transform should have modified all amplitudes
                # from their original values.
                original_amp = original_motif_tones[j].amplitude
                assert transformed_tone.amplitude != original_amp
