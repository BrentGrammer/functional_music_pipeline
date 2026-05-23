from score_model.phrase import Phrase
from score_model.score import Score
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


def previous_phrase_tones(score: Score, voice_index: int, phrase_index: int) -> list[Tone]:
    if phrase_index > 0:
        return flatten_phrase_tones(score.voices[voice_index].phrases[phrase_index - 1])

    if voice_index > 0:
        return flatten_voice_tones(score.voices[voice_index - 1])

    return []
