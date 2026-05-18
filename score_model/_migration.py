"""Temporary migration scaffold for Phase 2 voice-shape transition.

This module exists only to provide a compatibility shim while consumers are
migrated off direct `Voice` internals. It will be removed at the end of
Phase 2.
"""

from score_model.tone import Tone
from score_model.voice import Voice


def _legacy_flatten_voice_tones(voice: Voice) -> list[Tone]:
    return voice.tones
