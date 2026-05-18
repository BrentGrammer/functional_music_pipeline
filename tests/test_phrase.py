import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.tone import Tone


class TestPhrase:
    def test_phrase_initialization(self):
        motif_name_1 = "motif_1"
        motif_name_2 = "motif_2"

        motifs = [
            Motif(motif_name_1, [Tone(440)]),
            Motif(motif_name_2, [Tone(880)]),
        ]

        phrase = Phrase(motifs)
        assert len(phrase.motifs) == len(motifs)
        assert phrase.motifs[0].name == motif_name_1
        assert phrase.motifs[1].name == motif_name_2

    def test_empty_phrase(self):
        phrase = Phrase()
        assert len(phrase.motifs) == 0
