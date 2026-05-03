import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from score_model.tone import Tone
from score_model.voice import Voice
from score_model.score import Score

class TestScore:
    def test_score_initialization(self):
        voice1 = Voice([Tone(440)])
        voice2 = Voice([Tone(880)])
        score = Score([voice1, voice2])
        
        assert len(score) == 2
        assert len(score[0]) == 1
        assert score[0][0].frequency == 440
        assert score[1][0].frequency == 880

    def test_empty_score(self):
        score = Score()
        assert len(score) == 0
