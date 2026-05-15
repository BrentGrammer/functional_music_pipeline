import math
import random
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class StochasticProfile(Protocol):
    def generate(self, length: int) -> list[float]: ...


def _build_random_phases(seed: int, count: int) -> list[float]:
    random.seed(seed)
    return [random.uniform(0, 2 * math.pi) for _ in range(count)]


def _cellular_initial_state(seed: int, width: int) -> list[int]:
    random.seed(seed)
    return [random.choice([0, 1]) for _ in range(width)]


def _cellular_cell_value(state: list[int], index: int) -> int:
    return state[index % len(state)]


def _cellular_next_state(state: list[int], rule: int) -> list[int]:
    next_state = [0] * len(state)

    for index in range(len(state)):
        left = _cellular_cell_value(state, index - 1)
        center = _cellular_cell_value(state, index)
        right = _cellular_cell_value(state, index + 1)
        neighborhood = (left << 2) | (center << 1) | right
        next_state[index] = (rule >> neighborhood) & 1

    return next_state


def _sample_ridged_octave(index: int, phase: float, rate: float) -> float:
    return 1.0 - abs(math.sin(index * rate + phase))


def _sample_ridged_noise(index: int, phases: list[float], rates: list[float], amplitudes: list[float]) -> float:
    noise = 0.0
    weight = 1.0

    for octave_index in range(len(phases)):
        octave_value = _sample_ridged_octave(index, phases[octave_index], rates[octave_index])
        octave_value *= weight
        weight = max(0.0, min(1.0, octave_value * 2.0))
        noise += octave_value * amplitudes[octave_index]

    return noise


def _normalize_ridged_noise(noise: float, max_possible: float) -> float:
    if max_possible == 0:
        return 0.0

    return noise / max_possible


def _emit_ridged_value(normalized_noise: float, threshold: float) -> float:
    if normalized_noise > threshold:
        if threshold < 1.0:
            drop_intensity = -1.0 * ((normalized_noise - threshold) / (1.0 - threshold))
        else:
            drop_intensity = -1.0
        return max(-1.0, drop_intensity)

    return 0.0


@dataclass(frozen=True)
class WeierstrassProfile:
    """
    Produces a continuous, self-similar fractal curve (the Weierstrass function).

    Musical effect: creates a smooth, shimmering, "wobbly" modulation — like
    vibrato with a life of its own. Because the curve is fractal, the motion
    contains slow sweeps overlaid with fast micro-tremors simultaneously.

    Applied to frequency: a breathing, pitch-bending shimmer.
    Applied to duration: tones elastically stretch and compress with a natural,
    organic rubato feel.
    Applied to amplitude: a complex, quasi-tremolo that never quite repeats.
    """
    seed: int = 42
    amplitude_scaling: float = 0.5
    ripples_per_wave: float = 3.0
    iterations: int = 10

    def generate(self, length: int) -> list[float]:
        """
        Samples the Weierstrass fractal curve at evenly spaced points.

        The resulting sequence of values smoothly wanders between -1.0 and 1.0,
        producing continuous, organic modulation in whatever tone dimension it
        is mapped onto.
        """
        random.seed(self.seed)
        start_x = random.uniform(0.0, 100.0)
        step = 0.15

        max_val = sum(self.amplitude_scaling**n for n in range(self.iterations))
        if max_val == 0:
            max_val = 1.0

        profile = []
        for i in range(length):
            x = start_x + (i * step)
            val = 0.0
            for n in range(self.iterations):
                val += (self.amplitude_scaling**n) * math.cos((self.ripples_per_wave**n) * math.pi * x)
            profile.append(val / max_val)

        return profile


@dataclass(frozen=True)
class TerracedBrownianProfile:
    """
    Produces a quantized random walk — a "staircase" drift through value space.

    Musical effect: creates stepwise, plateau-like shifts reminiscent of
    geological terraces or tectonic settling. Values stay flat for stretches,
    then jump to a new level and hold there.

    Applied to frequency: the motif drifts through stepped pitch regions, as if
    modulating to nearby keys without any smooth glide.
    Applied to duration: clusters of tones take on a shared tempo, then
    suddenly all shift to a slower or faster gait.
    Applied to amplitude: dynamics settle into terraced loud/soft plateaus,
    evoking classical "terraced dynamics" (e.g. Baroque organ registration).
    """
    seed: int = 42
    step_size: float = 0.25
    quantize_resolution: float = 0.2

    def generate(self, length: int) -> list[float]:
        """
        Performs a bounded random walk and snaps each step to a discrete level.

        The walk produces gradual drift, while quantization forces values onto
        a grid — so the output reads as flat plateaus punctuated by jumps
        rather than continuous motion.
        """
        random.seed(self.seed)
        current_value = 0.0
        profile = []

        for _ in range(length):
            current_value += random.uniform(-self.step_size, self.step_size)
            current_value = max(-1.0, min(1.0, current_value))

            if self.quantize_resolution > 0:
                quantized = round(current_value / self.quantize_resolution) * self.quantize_resolution
            else:
                quantized = current_value

            quantized = max(-1.0, min(1.0, quantized))
            profile.append(quantized)

        return profile


@dataclass(frozen=True)
class CellularAutomataProfile:
    """
    Produces a binary sequence evolved from an elementary cellular automaton
    (e.g. Wolfram's Rule 30).

    Musical effect: creates a sharp, binary, on/off modulation with emergent
    chaotic patterns — no smoothness, only flips between two extremes. The
    sequence is deterministic yet computationally irreducible, so it feels
    simultaneously structured and unpredictable.

    Applied to frequency: tones snap between a "high" and "low" pitch variant,
    producing a jagged, almost Morse-code-like melodic contour.
    Applied to duration: alternating short/long tones create a stuttering,
    rhythmically unstable pulse.
    Applied to amplitude: accented/unaccented tones form chaotic but
    self-similar rhythmic accents.
    """
    rule: int = 30
    seed: int = 42
    width: int = 31

    def generate(self, length: int) -> list[float]:
        """
        Evolves a 1D cellular automaton and samples the center cell each step.

        Each generation applies the chosen Wolfram rule to the entire row; the
        center cell's state (0 or 1) is emitted as -1.0 or +1.0. The result is
        an extreme, bistable modulation signal.
        """
        random.seed(self.seed)

        state = [random.choice([0, 1]) for _ in range(self.width)]
        profile = []
        center_idx = self.width // 2

        for _ in range(length):
            profile.append(-1.0 if state[center_idx] == 0 else 1.0)

            next_state = [0] * self.width
            for i in range(self.width):
                left = state[i - 1] if i > 0 else state[-1]
                center = state[i]
                right = state[i + 1] if i < self.width - 1 else state[0]

                neighborhood = (left << 2) | (center << 1) | right
                next_state[i] = (self.rule >> neighborhood) & 1

            state = next_state

        return profile


@dataclass(frozen=True)
class RidgedMultifractalProfile:
    """
    Produces a mostly-zero signal punctuated by sharp negative "drops" when
    multi-octave noise crosses a threshold.

    Musical effect: leaves the motif largely untouched, but occasionally
    punches in a dramatic event — a sudden silence, a sharp pitch dip, or a
    momentary collapse. Evokes geological ridges with rare deep crevasses, or
    a stable surface that occasionally gives way.

    Applied to duration: most tones play normally, but rare tones stretch
    dramatically or nearly vanish — creating surprising rhythmic ruptures.
    Applied to frequency: most pitches hold, but isolated tones plunge
    downward, like a voice cracking.
    Applied to amplitude: the motif plays steadily, with occasional sudden
    dropouts or ghost-like fades.

    Attributes:
        seed: Random seed controlling the phase offsets of each noise octave.
            Different seeds produce different drop patterns for the same length.
        octaves: Number of sinusoidal layers summed together. More octaves
            produce richer, more irregular noise with finer-grained detail.
        ridge_density: How densely packed the ridges of the underlying noise
            pattern are across the tone sequence. Higher values (e.g. 1.0+)
            pack ridges close together, producing more frequent drop events
            and making the effect audible on fewer tones. Lower values (e.g.
            0.05) spread ridges far apart, so drops become rare and may not
            occur at all within a short motif. Each successive octave
            doubles the density (adding finer-grained ridges on top).
        drop_when_noise_above: The noise level (0.0 to 1.0) above which a
            drop event is triggered. Lower values make drops easier to
            trigger (producing more frequent drops); higher values raise the
            bar so only the strongest noise peaks qualify (producing rare
            but dramatic drops).
    """
    seed: int = 42
    octaves: int = 3
    ridge_density: float = 0.3
    drop_when_noise_above: float = 0.5

    def generate(self, length: int) -> list[float]:
        """
        Sums multiple octaves of ridged sinusoidal noise and emits a drop
        value only where the noise exceeds the `drop_when_noise_above` level.

        At or below that level the profile returns 0.0 (no deviation); above
        it, the value scales linearly toward -1.0, producing sparse but
        intense downward events.
        """
        random.seed(self.seed)
        phases = [random.uniform(0, 2 * math.pi) for _ in range(self.octaves)]

        rates = [self.ridge_density * (2 ** i) for i in range(self.octaves)]
        amplitudes = [1.0 / (2 ** i) for i in range(self.octaves)]

        max_possible = sum(amplitudes)
        if max_possible == 0:
            max_possible = 1.0

        threshold = self.drop_when_noise_above

        profile = []
        for i in range(length):
            noise = 0.0
            weight = 1.0
            for o in range(self.octaves):
                v = 1.0 - abs(math.sin(i * rates[o] + phases[o]))
                v *= weight
                weight = max(0.0, min(1.0, v * 2.0))
                noise += v * amplitudes[o]

            normalized_noise = noise / max_possible

            if normalized_noise > threshold:
                drop_intensity = -1.0 * ((normalized_noise - threshold) / (1.0 - threshold)) if threshold < 1.0 else -1.0
                profile.append(max(-1.0, drop_intensity))
            else:
                profile.append(0.0)

        return profile


@dataclass(frozen=True)
class RandomDropProfile:
    """
    Produces a mostly-zero signal punctuated by random negative "drops" at a
    controlled rate.

    Musical effect: leaves the motif mostly untouched, but randomly punches in
    sudden downward events at a predictable average rate. Each drop has a
    random depth, so drops vary in intensity from subtle to dramatic.

    Compared to RidgedMultifractalProfile: this profile is simpler and more
    directly controllable — one parameter governs how often drops occur,
    without layered noise fields. Drops are independent events rather than
    emerging from an underlying terrain.

    Applied to duration: most tones play normally, with occasional tones that
    suddenly compress or nearly vanish.
    Applied to frequency: most pitches hold, with occasional tones that dip
    downward by varying amounts.
    Applied to amplitude: the motif plays steadily, with random fades or
    dropouts scattered throughout.

    Attributes:
        seed: Random seed controlling which tones become drops and how deep
            each drop is. Different seeds produce different drop patterns.
        drop_rate: Probability (0.0 to 1.0) that any given tone becomes a
            drop. 0.0 means no drops ever; 1.0 means every tone is a drop.
            A value of 0.2, for example, produces drops on roughly 20% of
            tones on average.
    """
    seed: int = 42
    drop_rate: float = 0.2

    def generate(self, length: int) -> list[float]:
        """
        For each tone position, randomly decides whether to emit a drop.

        When a drop is emitted, its depth is a random value in [-1.0, 0.0),
        producing drops of varied intensity. Non-drop positions emit 0.0
        (no deviation).
        """
        rng = random.Random(self.seed)
        profile = []
        for _ in range(length):
            if rng.random() < self.drop_rate:
                profile.append(-rng.random())
            else:
                profile.append(0.0)
        return profile
