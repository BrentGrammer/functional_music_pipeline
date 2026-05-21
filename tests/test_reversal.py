import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import NoParams, PhraseTransformContext
from transforms.basic.reversal import reverse_phrase_transform, reverse_score_transform, reverse_tones


class TestReverseTones:
    def test_reverse(self):
        first_frequency = 440
        second_frequency = 880
        third_frequency = 523
        tones = [Tone(first_frequency), Tone(second_frequency), Tone(third_frequency)]
        result = reverse_tones(tones)
        assert len(result) == 3
        assert result[0].frequency == third_frequency
        assert result[1].frequency == second_frequency
        assert result[2].frequency == first_frequency


class TestReversePhraseTransform:
    def test_reverse_phrase_transform_returns_reversed_phrase(self):
        first_frequency = 440
        second_frequency = 880
        third_frequency = 523
        score = Score(
            [
                Voice(
                    [
                        Phrase(
                            [
                                Motif(
                                    "subject",
                                    [
                                        Tone(first_frequency),
                                        Tone(second_frequency),
                                        Tone(third_frequency),
                                    ],
                                )
                            ]
                        )
                    ]
                ),
            ]
        )
        context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

        result = reverse_phrase_transform(context=context, params=NoParams())

        assert len(result.motifs) == 1
        assert result.motifs[0].name == "<transformed>"
        assert [tone.frequency for tone in result.motifs[0].tones] == [
            third_frequency,
            second_frequency,
            first_frequency,
        ]


class TestReverseScoreTransform:
    def test_reverse_score_transform_returns_score_with_each_voice_reversed(self):
        voice_one_first_frequency = 440
        voice_one_second_frequency = 880
        voice_two_first_frequency = 523
        voice_two_second_frequency = 1046
        score = Score(
            [
                Voice(
                    [
                        Phrase(
                            [
                                Motif("m1", [Tone(voice_one_first_frequency), Tone(voice_one_second_frequency)]),
                            ]
                        )
                    ]
                ),
                Voice(
                    [
                        Phrase(
                            [
                                Motif("m2", [Tone(voice_two_first_frequency), Tone(voice_two_second_frequency)]),
                            ]
                        )
                    ]
                ),
            ]
        )

        result = reverse_score_transform(score=score, params=NoParams())

        assert len(result.voices) == 2

        # Voice 1
        assert len(result.voices[0].phrases) == 1
        assert len(result.voices[0].phrases[0].motifs) == 1
        assert [tone.frequency for tone in result.voices[0].phrases[0].motifs[0].tones] == [
            voice_one_second_frequency,
            voice_one_first_frequency,
        ]

        # Voice 2
        assert len(result.voices[1].phrases) == 1
        assert len(result.voices[1].phrases[0].motifs) == 1
        assert [tone.frequency for tone in result.voices[1].phrases[0].motifs[0].tones] == [
            voice_two_second_frequency,
            voice_two_first_frequency,
        ]
