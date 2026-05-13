import numpy as np
from numpy.typing import NDArray

DEFAULT_DURATION_SECONDS = 0.5
DEFAULT_SAMPLE_RATE_HZ = 44100
DEFAULT_AMPLITUDE = 0.5
MAX_16BIT_PCM = 32767
TWO_PI = 2.0 * np.pi


class Tone:
    def __init__(
        self,
        frequency: float,
        duration: float = DEFAULT_DURATION_SECONDS,
        sample_rate: int = DEFAULT_SAMPLE_RATE_HZ,
        amplitude: float = DEFAULT_AMPLITUDE,
    ) -> None:
        self.frequency = frequency
        self.duration = duration
        self.sample_rate = sample_rate
        self.amplitude = amplitude

    def generate_tone(self) -> NDArray[np.int16]:
        if self.frequency == 0 or self.amplitude == 0:
            return np.zeros(int(self.sample_rate * self.duration), dtype=np.int16)

        t: NDArray[np.float64] = np.linspace(
            0,
            self.duration,
            int(self.sample_rate * self.duration),
            endpoint=False,
        )
        wave: NDArray[np.float64] = self.amplitude * np.sin(TWO_PI * self.frequency * t)
        return np.asarray(wave * MAX_16BIT_PCM, dtype=np.int16)
