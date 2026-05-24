import pytest

from composition.parser import generate_score_plan, parse_motifs
from composition.schema import CompositionDocumentInput
from composition.transformer import transform_score
from score_model.score import Score
from score_model.traversal import flatten_voice_tones


def _build_geological_example_composition() -> CompositionDocumentInput:
    return {
        "name": "Geological Example Composition",
        "description": (
            "A showcase of the stochastic transforms. Each voice plays the same C major arpeggio, "
            "but has a different stochastic transform applied to a different musical dimension "
            "(frequency, duration, or amplitude). A score-level transform is also applied to all voices."
        ),
        "score": {
            "motifs": {
                "c_major_arpeggio": [
                    "261.63:0.5",
                    "329.63:0.5",
                    "392.00:0.5",
                    "523.25:0.5",
                ]
            },
            "voices": [
                {
                    "phrases": [
                        {
                            "motifs": ["c_major_arpeggio"],
                            "transforms": [
                                {
                                    "name": "weierstrass",
                                    "params": {
                                        "dimension": "frequency",
                                        "intensity": "low",
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
                                    "name": "terraced_drift",
                                    "params": {
                                        "dimension": "duration",
                                        "max_step_change_pct": 25,
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
                                    "name": "cellular_automata",
                                    "params": {
                                        "dimension": "amplitude",
                                        "rule": 30,
                                        "generations": 5,
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
                                    "name": "random_drop",
                                    "params": {
                                        "dimension": "amplitude",
                                        "max_drop_pct": 90,
                                        "drop_frequency_pct": 50,
                                    },
                                }
                            ],
                        }
                    ]
                },
            ],
            "score_transforms": [
                {
                    "name": "weierstrass",
                    "params": {
                        "dimension": "amplitude",
                        "intensity": "medium",
                    },
                }
            ],
        },
    }


class TestGeologicalExampleComposition:
    def test_loads_and_parses_without_error(self):
        # This test ensures the example composition file is valid JSON and
        # can be successfully parsed by the composition engine, serving as a
        # basic integration test for the flat stochastic transform API.
        composition_data = _build_geological_example_composition()

        score = transform_score(generate_score_plan(composition_data))

        assert isinstance(score, Score)
        assert len(score.voices) == 4

        # The motif "c_major_arpeggio" has 4 tones, so each voice should have 4 tones.
        for voice in score.voices:
            assert len(flatten_voice_tones(voice)) == 4

    def test_parsing_is_deterministic(self):
        # Stochastic transforms are seeded, so repeated parsing of the same
        # composition must yield identical musical output. This test locks in
        # that invariant.
        composition_data = _build_geological_example_composition()

        score1 = transform_score(generate_score_plan(composition_data))
        score2 = transform_score(generate_score_plan(composition_data))

        assert len(score1.voices) == len(score2.voices)

        for voice1, voice2 in zip(score1.voices, score2.voices):
            voice1_tones = flatten_voice_tones(voice1)
            voice2_tones = flatten_voice_tones(voice2)
            assert len(voice1_tones) == len(voice2_tones)
            for tone1, tone2 in zip(voice1_tones, voice2_tones):
                assert tone1.frequency == pytest.approx(tone2.frequency)
                assert tone1.duration == pytest.approx(tone2.duration)
                assert tone1.amplitude == pytest.approx(tone2.amplitude)

    def test_structural_invariants(self):
        # Verifies the user-visible guarantees of the stochastic transform API
        # at the composition boundary.
        composition_data = _build_geological_example_composition()

        score = transform_score(generate_score_plan(composition_data))

        # Retrieve original tones for comparison by reusing the motif parser.
        # This avoids duplicating tone-string parsing logic in the test.
        parsed_motifs = parse_motifs(composition_data["score"]["motifs"])
        original_motif_tones = parsed_motifs["c_major_arpeggio"]

        # Voice 1: Weierstrass on Frequency
        voice1_tones = flatten_voice_tones(score.voices[0])
        for i, transformed_tone in enumerate(voice1_tones):
            original_freq = original_motif_tones[i].frequency
            assert transformed_tone.frequency != original_freq

        # Voice 2: Terraced Brownian on Duration
        voice2_tones = flatten_voice_tones(score.voices[1])
        for transformed_tone in voice2_tones:
            assert transformed_tone.duration > 0

        # All Voices: Verify score-level amplitude transform and general amplitude invariants
        for i, voice in enumerate(score.voices):
            for j, transformed_tone in enumerate(flatten_voice_tones(voice)):
                # Check invariant: amplitude must be in valid range
                assert 0.0 <= transformed_tone.amplitude <= 1.0

                # Check effect: score transform should have modified all amplitudes
                # from their original values.
                original_amp = original_motif_tones[j].amplitude
                assert transformed_tone.amplitude != original_amp
