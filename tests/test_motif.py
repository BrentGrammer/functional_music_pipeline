import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from score_model.motif import Motif
from score_model.tone import Tone


class TestMotif:
    def test_motif_initialization(self):
        freq1 = 440
        freq2 = 880
        name = "test_motif"

        tones = [Tone(freq1), Tone(freq2)]
        motif = Motif(name, tones)
        assert motif.name == name
        assert len(motif.tones) == len(tones)
        assert motif.tones[0].frequency == freq1
        assert motif.tones[1].frequency == freq2

    def test_empty_motif(self):
        name = "empty_motif"
        motif = Motif(name)
        assert motif.name == name
        assert len(motif.tones) == 0
