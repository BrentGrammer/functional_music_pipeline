from score_model.tone import Tone
from score_model.voice import Voice


def iter_voice_tones(voice: Voice) -> list[Tone]:
    return [
        tone
        for phrase in voice.phrases
        for motif in phrase.motifs
        for tone in motif.tones
    ]
