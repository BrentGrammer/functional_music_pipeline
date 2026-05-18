from score_model.motif import Motif


class Phrase:
    """
    A Phrase represents an ordered sequence of Motifs.
    """

    def __init__(self, motifs: list[Motif] | None = None) -> None:
        self.motifs = motifs if motifs is not None else []
