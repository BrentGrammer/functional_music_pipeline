from score_model.tone import Tone


class Motif:
    """
    A Motif represents a named sequence of Tones.
    """

    def __init__(self, name: str, tones: list[Tone] | None = None) -> None:
        self.name = name
        self.tones = tones if tones is not None else []
