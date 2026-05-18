import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import PhraseTransformContext
from transforms.basic.reversal import reverse_phrase_transform, reverse_tones


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

        result = reverse_phrase_transform(context=context, params={})

        assert len(result.motifs) == 1
        assert result.motifs[0].name == "<transformed>"
        assert [tone.frequency for tone in result.motifs[0].tones] == [
            third_frequency,
            second_frequency,
            first_frequency,
        ]
