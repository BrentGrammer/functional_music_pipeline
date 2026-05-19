import math
from collections.abc import Mapping
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.pitch_utils import CENTS_PER_OCTAVE
from score_model.score import Score
from score_model.tone import Tone
from score_model.tone_utils import copy_tones
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from transforms.base import IntegerParam, TransformParamFieldSpec, TransformParamsSpec
from transforms.basic.delay import delay_tones

FrostPendingEdgeExpansion: TypeAlias = tuple[Voice, Callable[[float], float]]
FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS = 25.0
FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS = 115.0
FROST_EFFECT_EDGE_STAGGER_MIN_SECONDS = 0.28
FROST_EFFECT_EDGE_STAGGER_MAX_SECONDS = 0.55
FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MIN_SECONDS = 0.18
FROST_EFFECT_SINGLE_SEED_EDGE_SEPARATION_MAX_SECONDS = 0.32
FROST_ROLE_CENTER = "center"
FROST_ROLE_SIDE = "side"

FROST_EFFECT_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "iterations": TransformParamFieldSpec(
            schema=IntegerParam(),
        )
    }
)


@dataclass(frozen=True)
class FrostOnsetTone:
    voice: Voice
    tone: Tone
    onset_time: float


@dataclass(frozen=True)
class FrostVoiceBuildSpec:
    tone: Tone
    delay_seconds: float
    generation: int
    frequency: float
    role: str


@dataclass(frozen=True)
class FrostEventBuildSpec:
    source_voices: list[Voice]
    event_start: float
    generation: int
    preserve_existing_roles: bool
    single_seed_event: bool


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
    setattr(copied_voice, "frost_role", getattr(voice, "frost_role", FROST_ROLE_CENTER))
    return copied_voice


def _build_frost_voice(spec: FrostVoiceBuildSpec) -> Voice:
    child_voice = Voice(
        phrases=[
            Phrase(
                motifs=[
                    Motif(
                        name="<frost>",
                        tones=delay_tones(
                            [
                                Tone(
                                    frequency=spec.frequency,
                                    duration=spec.tone.duration,
                                    sample_rate=spec.tone.sample_rate,
                                    amplitude=spec.tone.amplitude,
                                )
                            ],
                            spec.delay_seconds,
                        ),
                    )
                ]
            )
        ]
    )
    setattr(child_voice, "frost_generation", spec.generation)
    setattr(child_voice, "frost_role", spec.role)
    return child_voice

def _score_end_time(score: Score) -> float:
    return max(
        (sum(tone.duration for tone in flatten_voice_tones(voice)) for voice in score.voices),
        default=0.0,
    )


def _first_audible_tone_with_onset(voice: Voice) -> FrostOnsetTone | None:
    onset_time = 0.0

    for tone in flatten_voice_tones(voice):
        if tone.frequency > 0 and tone.amplitude > 0 and tone.duration > 0:
            return FrostOnsetTone(voice=voice, tone=tone, onset_time=onset_time)

        onset_time += tone.duration

    return None


def _first_audible_onset_time(score: Score) -> float | None:
    onset_tones = [
        onset_tone
        for voice in score.voices
        if (onset_tone := _first_audible_tone_with_onset(voice)) is not None
    ]

    if not onset_tones:
        return None

    return min(onset_tone.onset_time for onset_tone in onset_tones)


def _first_audible_onset_field(score: Score) -> list[FrostOnsetTone]:
    first_onset_time = _first_audible_onset_time(score)
    if first_onset_time is None:
        return []

    onset_field: list[FrostOnsetTone] = []

    for voice in score.voices:
        onset_tone = _first_audible_tone_with_onset(voice)
        if onset_tone is None:
            continue
        if math.isclose(onset_tone.onset_time, first_onset_time):
            onset_field.append(onset_tone)

    return onset_field


def _first_audible_tone(voice: Voice) -> Tone | None:
    for tone in flatten_voice_tones(voice):
        if tone.frequency > 0 and tone.amplitude > 0 and tone.duration > 0:
            return tone

    return None


def _first_audible_frequency(voice: Voice) -> float | None:
    tone = _first_audible_tone(voice)
    if tone is None:
        return None

    return tone.frequency


def _find_frost_edge_voices(voices: list[Voice]) -> tuple[Voice | None, Voice | None]:
    audible_voices = [voice for voice in voices if _first_audible_frequency(voice) is not None]

    if not audible_voices:
        return None, None

    lower_edge_voice = min(audible_voices, key=lambda voice: _first_audible_frequency(voice) or 0.0)
    upper_edge_voice = max(audible_voices, key=lambda voice: _first_audible_frequency(voice) or 0.0)
    return lower_edge_voice, upper_edge_voice


def _cents_to_frequency_ratio(cents: float) -> float:
    return math.pow(2.0, cents / CENTS_PER_OCTAVE)


def _random_outward_cents() -> float:
    return random.uniform(
        FROST_EFFECT_MINIMUM_OUTWARD_MOVEMENT_CENTS,
        FROST_EFFECT_MAXIMUM_OUTWARD_MOVEMENT_CENTS,
    )


def _jitter_frequency_down_within_bounds(frequency: float) -> float:
    """
    Shift a frequency downward by a random bounded interval.
    """
    return max(1.0, frequency / _cents_to_frequency_ratio(_random_outward_cents()))


def _jitter_frequency_up_within_bounds(frequency: float) -> float:
    """
    Shift a frequency upward by a random bounded interval.
    """
    return frequency * _cents_to_frequency_ratio(_random_outward_cents())


def _build_pending_edge_expansions(voices: list[Voice]) -> list[FrostPendingEdgeExpansion]:
    lower_edge_voice, upper_edge_voice = _find_frost_edge_voices(voices)
    pending_edge_expansions: list[FrostPendingEdgeExpansion] = []

    if lower_edge_voice is not None:
        pending_edge_expansions.append((lower_edge_voice, _jitter_frequency_down_within_bounds))
    if upper_edge_voice is not None:
        pending_edge_expansions.append((upper_edge_voice, _jitter_frequency_up_within_bounds))

    return pending_edge_expansions


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


def _build_replay_entry_delays(voice_count: int) -> list[float]:
    if voice_count <= 0:
        return []

    entry_delays: list[float] = []
    current_delay = _random_edge_stagger_seconds()

    for index in range(voice_count):
        if index > 0:
            current_delay += _random_edge_stagger_seconds()
        entry_delays.append(current_delay)

    return entry_delays


def _advance_edge_delay(
    previous_edge_delay: float | None,
    edge_base_delay: float,
    next_delay: Callable[[], float],
) -> float:
    if previous_edge_delay is None:
        return edge_base_delay + _random_edge_stagger_seconds()

    return previous_edge_delay + next_delay()


def _build_replayed_event_voices(
    voices: list[Voice],
    event_start: float,
    generation: int,
    preserve_existing_roles: bool,
    entry_delays: list[float] | None = None,
) -> list[Voice]:
    replayed_voices: list[Voice] = []
    if entry_delays is None:
        entry_delays = _build_replay_entry_delays(len(voices))

    for voice, entry_delay in zip(voices, entry_delays):
        tone = _first_audible_tone(voice)
        if tone is None:
            continue

        replayed_voices.append(
            _build_frost_voice(
                FrostVoiceBuildSpec(
                    tone=tone,
                    delay_seconds=event_start + entry_delay,
                    generation=generation,
                    frequency=tone.frequency,
                    role=getattr(voice, "frost_role", FROST_ROLE_CENTER)
                    if preserve_existing_roles
                    else FROST_ROLE_CENTER,
                )
            )
        )

    return replayed_voices


def _build_edge_voices(
    spec: FrostEventBuildSpec,
    edge_base_delay: float,
) -> list[Voice]:
    pending_edge_expansions = _build_pending_edge_expansions(spec.source_voices)
    random.shuffle(pending_edge_expansions)
    next_edge_delay = (
        _random_single_seed_edge_separation_seconds
        if spec.single_seed_event
        else _random_edge_stagger_seconds
    )

    edge_voices: list[Voice] = []
    previous_edge_delay: float | None = None

    for voice, build_child_frequency in pending_edge_expansions:
        tone = _first_audible_tone(voice)
        if tone is None:
            continue

        edge_delay = _advance_edge_delay(previous_edge_delay, edge_base_delay, next_edge_delay)
        previous_edge_delay = edge_delay

        edge_voices.append(
            _build_frost_voice(
                FrostVoiceBuildSpec(
                    tone=tone,
                    delay_seconds=spec.event_start + edge_delay,
                    generation=spec.generation,
                    frequency=build_child_frequency(tone.frequency),
                    role=FROST_ROLE_SIDE,
                )
            )
        )

    return edge_voices


def _build_frost_event_voices(
    spec: FrostEventBuildSpec,
) -> list[Voice]:
    replay_entry_delays = _build_replay_entry_delays(len(spec.source_voices))
    replayed_voices = _build_replayed_event_voices(
        spec.source_voices,
        spec.event_start,
        spec.generation,
        preserve_existing_roles=spec.preserve_existing_roles,
        entry_delays=replay_entry_delays,
    )
    edge_voices = _build_edge_voices(
        spec,
        edge_base_delay=max(replay_entry_delays, default=0.0),
    )
    return replayed_voices + edge_voices


def _build_initial_frost_event_voices(score: Score, event_start: float) -> list[Voice]:
    source_voices = [onset_tone.voice for onset_tone in _first_audible_onset_field(score)]
    return _build_frost_event_voices(
        FrostEventBuildSpec(
            source_voices=source_voices,
            event_start=event_start,
            generation=1,
            preserve_existing_roles=False,
            single_seed_event=len(source_voices) == 1,
        )
    )


def _build_later_frost_event_voices(score: Score, latest_generation: int, event_start: float) -> list[Voice]:
    latest_voices = [
        voice
        for voice in score.voices
        if getattr(voice, "frost_generation", 0) == latest_generation and _first_audible_tone(voice) is not None
    ]
    return _build_frost_event_voices(
        FrostEventBuildSpec(
            source_voices=latest_voices,
            event_start=event_start,
            generation=latest_generation + 1,
            preserve_existing_roles=True,
            single_seed_event=False,
        )
    )


def _apply_frost_iteration(score: Score) -> Score:
    """
    Append one audible frost event to a score.
    """
    original_voices = [_copy_voice_retaining_frost_history(voice) for voice in score.voices]
    latest_generation = max((getattr(voice, "frost_generation", 0) for voice in score.voices), default=0)
    event_start = _score_end_time(score)

    if latest_generation == 0:
        frosted_voices = _build_initial_frost_event_voices(score, event_start)
    else:
        frosted_voices = _build_later_frost_event_voices(score, latest_generation, event_start)

    return Score(original_voices + frosted_voices)


def frost_effect(score: Score, iterations: int = 1) -> Score:
    """
    Score-level frost effect entry point.

    Applies one or more audible frost events to the score.
    """
    if isinstance(iterations, bool) or not isinstance(iterations, int):
        raise ValueError("frost_effect iterations must be a positive integer.")
    if iterations < 1:
        raise ValueError("frost_effect iterations must be a positive integer.")

    result = score
    for _ in range(iterations):
        result = _apply_frost_iteration(result)

    return result


def frost_effect_score_transform_adapter(score: Score, params: Mapping[str, object]) -> Score:
    iterations = params.get("iterations", 1)
    if isinstance(iterations, bool) or not isinstance(iterations, int):
        raise ValueError("frost_effect iterations must be a positive integer.")
    return frost_effect(score, iterations=iterations)
