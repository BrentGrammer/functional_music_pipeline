from score_model.phrase import Phrase


class Voice:
    """
    A Voice represents an ordered sequence of Phrases.
    """

    def __init__(self, phrases: list[Phrase] | None = None) -> None:
        self.phrases = phrases if phrases is not None else []
