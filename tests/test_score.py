import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice


class TestScore:
    def test_score_initialization(self):
        phrase1_freq = 440
        phrase2_freq = 880
        voice1 = Voice([Phrase(motifs=[Motif("motif_1", [Tone(phrase1_freq)])])])
        voice2 = Voice([Phrase(motifs=[Motif("motif_2", [Tone(phrase2_freq)])])])
        voices = [voice1, voice2]
        score = Score(voices)
        
        assert len(score) == len(voices)
        assert len(score[0].phrases) == 1
        assert score[0].phrases[0].motifs[0].tones[0].frequency == phrase1_freq
        assert score[1].phrases[0].motifs[0].tones[0].frequency == phrase2_freq

    def test_empty_score(self):
        score = Score()
        assert len(score) == 0
