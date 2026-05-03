from collections.abc import Iterator

from score_model.tone import Tone


class Voice:
    """
    A Voice represents a single, monophonic sequence of Tones.
    """

    def __init__(self, tones: list[Tone] | None = None) -> None:
        self.tones = tones if tones is not None else []

    def __len__(self) -> int:
        return len(self.tones)

    def __getitem__(self, index: int) -> Tone:
        return self.tones[index]

    def __iter__(self) -> Iterator[Tone]:
        return iter(self.tones)
