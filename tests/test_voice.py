import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from score_model.tone import Tone
from score_model.voice import Voice

class TestVoice:
    def test_voice_initialization(self):
        tones = [Tone(440), Tone(880)]
        voice = Voice(tones)
        assert len(voice) == 2
        assert voice[0].frequency == 440
        assert voice[1].frequency == 880

    def test_empty_voice(self):
        voice = Voice()
        assert len(voice) == 0
