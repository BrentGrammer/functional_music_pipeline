from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.tone_utils import make_silence_tone
from transforms.base import FloatParam, PhraseTransformContext, ToneSequence, TransformParamFieldSpec, TransformParamsSpec

DELAY_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "seconds": TransformParamFieldSpec(
            schema=FloatParam(),
            required=True,
        )
    }
)


def delay_tones(tones: ToneSequence, seconds: float) -> ToneSequence:
    if seconds < 0:
        raise ValueError("Delay must be non-negative. Negative offsets are not supported.")
    if seconds == 0:
        return tones[:]

    silent_tone = make_silence_tone(seconds)
    return [silent_tone] + tones[:]


def delay_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    seconds = params["seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise ValueError("Param 'seconds' must be a float.")

    phrase_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]
    delayed_tones = delay_tones(phrase_tones, seconds=float(seconds))
    return Phrase(motifs=[Motif(name="<transformed>", tones=delayed_tones)])
