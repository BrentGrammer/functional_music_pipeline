import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.tone import Tone
from score_model.voice import Voice


class TestVoice:
    def test_voice_initialization(self):
        phrase1_freq = 440
        phrase2_freq = 880
        phrase1 = Phrase(motifs=[Motif("motif_1", [Tone(phrase1_freq)])])
        phrase2 = Phrase(motifs=[Motif("motif_2", [Tone(phrase2_freq)])])
        phrases = [phrase1,phrase2]
        voice = Voice(phrases)
        assert len(voice.phrases) == len(phrases)
        assert voice.phrases[0].motifs[0].tones[0].frequency == phrase1_freq
        assert voice.phrases[1].motifs[0].tones[0].frequency == phrase2_freq

    def test_empty_voice(self):
        voice = Voice()
        assert len(voice.phrases) == 0
