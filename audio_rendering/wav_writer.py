import logging
import wave

import numpy as np

from score_model.score import Score
from score_model._migration import _legacy_flatten_voice_tones
from score_model.tone import DEFAULT_SAMPLE_RATE_HZ, MAX_16BIT_PCM

logger = logging.getLogger(__name__)

MAX_DURATION_SECONDS = 600.0


def mix_waveforms(waveforms: list[np.ndarray]) -> np.ndarray:
    if not waveforms:
        return np.array([], dtype=np.int16)

    max_len = max(len(waveform) for waveform in waveforms)
    summed_waveform = np.zeros(max_len, dtype=np.float32)

    for waveform in waveforms:
        padded_waveform = np.pad(waveform, (0, max_len - len(waveform)), mode="constant")
        summed_waveform += padded_waveform

    max_amplitude = np.max(np.abs(summed_waveform))
    if max_amplitude > MAX_16BIT_PCM:
        summed_waveform = (summed_waveform / max_amplitude) * float(MAX_16BIT_PCM)

    return summed_waveform.astype(np.int16)


def save_score_to_wav(score: Score, filename: str = "output.wav") -> None:
    sample_rate = DEFAULT_SAMPLE_RATE_HZ
    voice_waveforms: list[np.ndarray] = []

    for voice in score.voices:
        total_duration = sum(tone.duration for tone in _legacy_flatten_voice_tones(voice))
        if total_duration > MAX_DURATION_SECONDS:
            raise ValueError(
                f"Voice duration ({total_duration:.1f}s) exceeds the maximum allowed duration of {MAX_DURATION_SECONDS}s."
            )

        tone_waveforms = [tone.generate_tone() for tone in _legacy_flatten_voice_tones(voice)]

        if tone_waveforms:
            voice_waveform = np.concatenate(tone_waveforms)
        else:
            voice_waveform = np.array([], dtype=np.int16)

        voice_waveforms.append(voice_waveform)

    mixed_audio = mix_waveforms(voice_waveforms)

    with wave.open(filename, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(mixed_audio.tobytes())

    logger.info(f"File '{filename}' has been saved.")
