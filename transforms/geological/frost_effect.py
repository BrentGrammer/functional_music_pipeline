import math
import random
from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.pitch_utils import CENTS_PER_OCTAVE
from score_model.score import Score
from score_model.tone import Tone
from score_model.tone_utils import copy_tones
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from transforms.base import BooleanParam, IntegerParam, ParsedTransformParams, TransformParamFieldSpec, TransformParamsSpec
from transforms.basic.delay import delay_tones

FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS = 25.0
FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS = 115.0
FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS = 0.28
FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS = 0.55
FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS = 0.18
FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS = 0.32
DEFAULT_FROST_EFFECT_ITERATIONS = 1
DEFAULT_FROST_EFFECT_SUSTAIN_NOTES = False


@dataclass(frozen=True)
class FrostEffectParams:
    iterations: int
    sustain_notes: bool


@dataclass(frozen=True)
class FrostSeedEvent:
    tone: Tone
    start_time: float
    end_time: float


def _create_frost_effect_params(parsed_params: ParsedTransformParams) -> FrostEffectParams:
    return FrostEffectParams(
        iterations=parsed_params.required("iterations", int),
        sustain_notes=parsed_params.required("sustain_notes", bool),
    )


FROST_EFFECT_PARAMS_SPEC = TransformParamsSpec[FrostEffectParams](
    params_factory=_create_frost_effect_params,
    fields={
        "iterations": TransformParamFieldSpec(
            schema=IntegerParam(),
            default=DEFAULT_FROST_EFFECT_ITERATIONS,
        ),
        "sustain_notes": TransformParamFieldSpec(
            schema=BooleanParam(),
            default=DEFAULT_FROST_EFFECT_SUSTAIN_NOTES,
        )
    }
)


def _copy_voice_retaining_frost_history(voice: Voice) -> Voice:
    copied_voice = Voice(
        phrases=[
            Phrase(
                motifs=[
                    Motif(
                        name="<frost_copy>",
                        tones=copy_tones(flatten_voice_tones(voice)),
                    )
                ]
            )
        ]
    )
    setattr(copied_voice, "frost_generation", getattr(voice, "frost_generation", 0))
    return copied_voice


def _build_frost_voice(
    tone: Tone,
    delay_seconds: float,
    generation: int,
    frequency: float,
) -> Voice:
    child_voice = Voice(
        phrases=[
            Phrase(
                motifs=[
                    Motif(
                        name="<frost>",
                        tones=delay_tones(
                            [
                                Tone(
                                    frequency=frequency,
                                    duration=tone.duration,
                                    sample_rate=tone.sample_rate,
                                    amplitude=tone.amplitude,
                                )
                            ],
                            delay_seconds,
                        ),
                    )
                ]
            )
        ]
    )
    setattr(child_voice, "frost_generation", generation)
    return child_voice


def _score_end_time(score: Score) -> float:
    return max(
        (sum(tone.duration for tone in flatten_voice_tones(voice)) for voice in score.voices),
        default=0.0,
    )


def _first_audible_tone_with_start_time(voice: Voice) -> tuple[Tone, float] | None:
    start_time = 0.0

    for tone in flatten_voice_tones(voice):
        if tone.frequency > 0 and tone.amplitude > 0 and tone.duration > 0:
            return tone, start_time
        start_time += tone.duration

    return None


def _first_audible_start_time_voices(score: Score) -> list[Voice]:
    earliest_start_time: float | None = None
    earliest_voices: list[Voice] = []

    for voice in score.voices:
        start_tone = _first_audible_tone_with_start_time(voice)
        if start_tone is None:
            continue

        _, start_time = start_tone
        if earliest_start_time is None or start_time < earliest_start_time:
            earliest_start_time = start_time
            earliest_voices = [voice]
        elif math.isclose(start_time, earliest_start_time):
            earliest_voices.append(voice)

    return earliest_voices


def _first_audible_tone(voice: Voice) -> Tone | None:
    for tone in flatten_voice_tones(voice):
        if tone.frequency > 0 and tone.amplitude > 0 and tone.duration > 0:
            return tone

    return None


def _collect_audible_seed_events(score: Score) -> list[FrostSeedEvent]:
    seed_events: list[FrostSeedEvent] = []

    for voice in score.voices:
        voice_time = 0.0
        for tone in flatten_voice_tones(voice):
            tone_end_time = voice_time + tone.duration
            if tone.frequency > 0 and tone.amplitude > 0 and tone.duration > 0:
                seed_events.append(FrostSeedEvent(tone=tone, start_time=voice_time, end_time=tone_end_time))
            voice_time = tone_end_time

    return seed_events


def _find_frost_edge_voices(voices: list[Voice]) -> tuple[Voice | None, Voice | None]:
    lowest_voice: Voice | None = None
    highest_voice: Voice | None = None
    lowest_frequency: float | None = None
    highest_frequency: float | None = None

    for voice in voices:
        tone = _first_audible_tone(voice)
        if tone is None:
            continue

        if lowest_frequency is None or tone.frequency < lowest_frequency:
            lowest_frequency = tone.frequency
            lowest_voice = voice
        if highest_frequency is None or tone.frequency > highest_frequency:
            highest_frequency = tone.frequency
            highest_voice = voice

    if lowest_voice is None or highest_voice is None:
        return None, None

    return lowest_voice, highest_voice


def _cents_to_frequency_ratio(cents: float) -> float:
    return math.pow(2.0, cents / CENTS_PER_OCTAVE)


def _random_outward_cents() -> float:
    return random.uniform(
        FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS,
        FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS,
    )


def _jitter_frequency_down_within_bounds(frequency: float) -> float:
    return max(1.0, frequency / _cents_to_frequency_ratio(_random_outward_cents()))


def _jitter_frequency_up_within_bounds(frequency: float) -> float:
    return frequency * _cents_to_frequency_ratio(_random_outward_cents())


def _random_edge_stagger_seconds() -> float:
    return random.uniform(
        FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS,
        FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS,
    )


def _random_single_seed_edge_separation_seconds() -> float:
    return random.uniform(
        FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS,
        FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS,
    )


def _apply_frost_iteration(score: Score) -> Score:
    """
    Append one audible frost event to a score.
    """
    original_voices = [_copy_voice_retaining_frost_history(voice) for voice in score.voices]
    latest_generation = max((getattr(voice, "frost_generation", 0) for voice in score.voices), default=0)
    event_start = _score_end_time(score)

    if latest_generation == 0:
        source_voices = _first_audible_start_time_voices(score)
        generation = 1
        use_single_seed_edge_separation = len(source_voices) == 1
    else:
        source_voices = [
            voice
            for voice in score.voices
            if getattr(voice, "frost_generation", 0) == latest_generation and _first_audible_tone(voice) is not None
        ]
        generation = latest_generation + 1
        use_single_seed_edge_separation = False

    if not source_voices:
        return Score(original_voices)

    frosted_voices: list[Voice] = []
    replay_delays: list[float] = []
    current_replay_delay = _random_edge_stagger_seconds()

    for index, voice in enumerate(source_voices):
        if index > 0:
            current_replay_delay += _random_edge_stagger_seconds()
        replay_delays.append(current_replay_delay)

        tone = _first_audible_tone(voice)
        if tone is None:
            continue

        frosted_voices.append(
            _build_frost_voice(
                tone=tone,
                delay_seconds=event_start + current_replay_delay,
                generation=generation,
                frequency=tone.frequency,
            )
        )

    lower_edge_voice, upper_edge_voice = _find_frost_edge_voices(source_voices)
    if lower_edge_voice is None or upper_edge_voice is None:
        raise RuntimeError("Frost effect expected audible edge voices when source voices are present.")
    edge_sources = [
        (lower_edge_voice, _jitter_frequency_down_within_bounds),
        (upper_edge_voice, _jitter_frequency_up_within_bounds),
    ]

    random.shuffle(edge_sources)
    previous_edge_delay: float | None = None
    edge_base_delay = max(replay_delays, default=0.0)

    for edge_voice, adjust_frequency in edge_sources:
        tone = _first_audible_tone(edge_voice)
        if tone is None:
            raise RuntimeError("Frost effect edge voice did not contain an audible tone.")

        if previous_edge_delay is None:
            edge_delay = edge_base_delay + _random_edge_stagger_seconds()
        else:
            edge_gap = (
                _random_single_seed_edge_separation_seconds()
                if use_single_seed_edge_separation
                else _random_edge_stagger_seconds()
            )
            edge_delay = previous_edge_delay + edge_gap
        previous_edge_delay = edge_delay

        frosted_voices.append(
            _build_frost_voice(
                tone=tone,
                delay_seconds=event_start + edge_delay,
                generation=generation,
                frequency=adjust_frequency(tone.frequency),
            )
        )

    return Score(original_voices + frosted_voices)


def frost_effect(score: Score, iterations: int = 3, sustain_notes: bool = DEFAULT_FROST_EFFECT_SUSTAIN_NOTES) -> Score:
    """
    Score-level frost effect entry point.

    Applies one or more audible frost events to the score.
    """
    if iterations < 1:
        raise ValueError("frost_effect iterations must be a positive integer.")

    result = score
    for _ in range(iterations):
        result = _apply_frost_iteration(result)

    return result


def frost_effect_score_transform_adapter(score: Score, params: FrostEffectParams) -> Score:
    return frost_effect(score, iterations=params.iterations, sustain_notes=params.sustain_notes)
