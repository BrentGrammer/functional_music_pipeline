from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import PhraseTransformContext, ToneSequence, TransformParamsSpec

REVERSE_PARAMS_SPEC = TransformParamsSpec()


def reverse_tones(tones: ToneSequence) -> ToneSequence:
    return tones[::-1]


def reverse_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    del params

    phrase_tones = flatten_phrase_tones(context.phrase)
    reversed_tones = reverse_tones(phrase_tones)
    return Phrase(motifs=[Motif(name="<transformed>", tones=reversed_tones)])


def reverse_score_transform(score: Score, params: Mapping[str, object]) -> Score:
    del params
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        reversed_tones = reverse_tones(voice_tones)
        new_voices.append(
            Voice(phrases=[Phrase(motifs=[Motif(name="<transformed>", tones=reversed_tones)])])
        )
    return Score(voices=new_voices)
