from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from transforms.base import PhraseTransformContext, ToneSequence, TransformParamsSpec

REVERSE_PARAMS_SPEC = TransformParamsSpec()


def reverse_tones(tones: ToneSequence) -> ToneSequence:
    return tones[::-1]


def reverse_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    del params

    phrase_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]
    reversed_tones = reverse_tones(phrase_tones)
    return Phrase(motifs=[Motif(name="<transformed>", tones=reversed_tones)])
