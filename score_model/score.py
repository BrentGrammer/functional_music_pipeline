from score_model.voice import Voice


class Score:
    """
    A Score represents a polyphonic composition consisting of multiple Voices.
    """

    def __init__(self, voices: list[Voice] | None = None) -> None:
        self.voices = voices if voices is not None else []

    def __len__(self) -> int:
        return len(self.voices)

    def __getitem__(self, index: int) -> Voice:
        return self.voices[index]
