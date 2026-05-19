from score_model.phrase import Phrase
from score_model.tone import Tone
from score_model.tone_utils import copy_tones
from score_model.voice import Voice


def flatten_phrase_tones(phrase: Phrase) -> list[Tone]:
    return copy_tones([
        tone
        for motif in phrase.motifs
        for tone in motif.tones
    ])


def flatten_voice_tones(voice: Voice) -> list[Tone]:
    return copy_tones([
        tone
        for phrase in voice.phrases
        for motif in phrase.motifs
        for tone in motif.tones
    ])
