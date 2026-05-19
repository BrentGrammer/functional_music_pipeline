from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from transforms.base import IntegerParam, PhraseTransformContext, ToneSequence, TransformParamFieldSpec, TransformParamsSpec

REPEAT_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "count": TransformParamFieldSpec(
            schema=IntegerParam(),
            required=True,
        )
    }
)


def repeat_tones(tones: ToneSequence, count: int) -> ToneSequence:
    if count < 1:
        raise ValueError("Repeat count must be at least 1.")

    return tones * (count + 1)


def repeat_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    count = params["count"]
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("Param 'count' must be an integer.")

    phrase_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]
    repeated_tones = repeat_tones(phrase_tones, count=int(count))
    return Phrase(motifs=[Motif(name="<transformed>", tones=repeated_tones)])
