from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import NoParams, PhraseTransformContext, TransformParamsSpec

REVERSE_PARAMS_SPEC = TransformParamsSpec[NoParams](params_factory=lambda params: NoParams())


def reverse_tones(tones: list[Tone]) -> list[Tone]:
    return tones[::-1]


def reverse_phrase_transform(context: PhraseTransformContext, params: NoParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    reversed_tones = reverse_tones(phrase_tones)
    return Phrase(motifs=[Motif(name="<transformed>", tones=reversed_tones)])


def reverse_score_transform(score: Score, params: NoParams) -> Score:
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        reversed_tones = reverse_tones(voice_tones)
        new_voices.append(
            Voice(phrases=[Phrase(motifs=[Motif(name="<transformed>", tones=reversed_tones)])])
        )
    return Score(voices=new_voices)
