import hashlib
import math
import random
from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones
from transforms.base import (
    IntegerParam,
    ParsedTransformParams,
    PhraseTransformContext,
    StringParam,
    ToneDimension,
    ToneDimensionParam,
    TransformParamFieldSpec,
    TransformParamsSpec,
)

TONE_REMOVAL_CHANCE = 0.33
DURATION_DAMAGE_CHANCE = 0.45
AMPLITUDE_DAMAGE_CHANCE = 0.45
MIN_DURATION_AFTER_DAMAGE_SECONDS = 0.03
MAX_DURATION_AFTER_DAMAGE_RATIO = 0.99
# Use a relative decibel-reduction band instead of raw amplitude ratios so amplitude damage
# can range from barely perceptible to clearly softer without forcing damaged tones toward silence.
MIN_AMPLITUDE_REDUCTION_DECIBELS = 0.1
MAX_AMPLITUDE_REDUCTION_DECIBELS = 20.0


@dataclass(frozen=True)
class FragmentParams:
    damage_pct: int
    damage_tones_chunk_size: int # how wide a span of tones to damage throughout the phrase
    dimension: ToneDimension | None
    repeatable_damage_key: str | None


def _create_fragment_params(parsed_params: ParsedTransformParams) -> FragmentParams:
    damage_pct = parsed_params.required("damage_pct", int)
    damage_tones_chunk_size = parsed_params.required("damage_tones_chunk_size", int)
    dimension = parsed_params.required("dimension", (ToneDimension, type(None)))
    repeatable_damage_key = parsed_params.required("repeatable_damage_key", (str, type(None)))

    _validate_fragment_params(damage_pct=damage_pct, damage_tones_chunk_size=damage_tones_chunk_size)

    return FragmentParams(
        damage_pct=damage_pct,
        damage_tones_chunk_size=damage_tones_chunk_size,
        dimension=dimension,
        repeatable_damage_key=repeatable_damage_key,
    )


def _validate_fragment_params(damage_pct: int, damage_tones_chunk_size: int) -> None:
    if damage_pct < 0 or damage_pct > 100:
        raise ValueError(f"damage_pct must be between 0 and 100, got {damage_pct}")
    if damage_tones_chunk_size < 1:
        raise ValueError(f"damage_tones_chunk_size must be at least 1, got {damage_tones_chunk_size}")


FRAGMENT_PARAMS_SPEC = TransformParamsSpec[FragmentParams](
    params_factory=_create_fragment_params,
    fields={
        "damage_pct": TransformParamFieldSpec(
            required=True,
            schema=IntegerParam(),
        ),
        "damage_tones_chunk_size": TransformParamFieldSpec(
            required=True,
            schema=IntegerParam(),
        ),
        "dimension": TransformParamFieldSpec(
            schema=ToneDimensionParam(),
            default=None,
        ),
        "repeatable_damage_key": TransformParamFieldSpec(
            schema=StringParam(),
            default=None,
        ),
    },
)


def _create_damage_pattern_randomizer(repeatable_damage_key: str) -> random.Random:
    seed_bytes = hashlib.sha256(repeatable_damage_key.encode("utf-8")).digest()
    seed = int.from_bytes(seed_bytes[:8], byteorder="big", signed=False)
    return random.Random(seed)


def _calculate_how_many_tones_to_damage(tone_count: int, damage_pct: int) -> int:
    rounded_damage_target = math.floor((tone_count * damage_pct / 100) + 0.5)

    if tone_count == 0 or damage_pct == 0:
        return 0

    return min(tone_count, max(1, rounded_damage_target))


def _convert_reduction_decibels_to_ratio(reduction_decibels: float) -> float:
    """
    Convert a relative amplitude reduction in decibels into a linear amplitude ratio.

    Amplitude decibels use 20 * log10(ratio), so converting back to a ratio requires
    10 ** (decibels / 20). The negative sign is needed because these values represent
    a reduction from the original tone, not a boost.
    """
    return 10 ** (-reduction_decibels / 20)


def _calculate_damaged_duration(original_duration: float, randomizer: random.Random) -> tuple[float, float]:
    duration_after_damage_ratio = randomizer.uniform(
        0.0,
        MAX_DURATION_AFTER_DAMAGE_RATIO,
    )
    shortened_duration = original_duration * duration_after_damage_ratio
    minimum_duration_after_damage = min(original_duration, MIN_DURATION_AFTER_DAMAGE_SECONDS)
    shortened_duration = max(minimum_duration_after_damage, shortened_duration)
    trailing_silence_duration = original_duration - shortened_duration
    return shortened_duration, trailing_silence_duration


def _calculate_damaged_amplitude(original_amplitude: float, randomizer: random.Random) -> float:
    amplitude_reduction_decibels = randomizer.uniform(
        MIN_AMPLITUDE_REDUCTION_DECIBELS,
        MAX_AMPLITUDE_REDUCTION_DECIBELS,
    )
    amplitude_after_damage_ratio = _convert_reduction_decibels_to_ratio(amplitude_reduction_decibels)
    return original_amplitude * amplitude_after_damage_ratio


def _create_silence_from_tone(original_tone: Tone, duration: float) -> Tone:
    return Tone(
        frequency=0.0,
        duration=duration,
        sample_rate=original_tone.sample_rate,
        amplitude=0.0,
    )


def _damage_selected_tone_across_dimensions(tone: Tone, randomizer: random.Random) -> list[Tone]:
    should_remove_tone = randomizer.random() < TONE_REMOVAL_CHANCE
    if should_remove_tone:
        return [_create_silence_from_tone(tone, duration=tone.duration)]

    should_shorten_duration = randomizer.random() < DURATION_DAMAGE_CHANCE
    should_reduce_amplitude = randomizer.random() < AMPLITUDE_DAMAGE_CHANCE
    if not should_shorten_duration and not should_reduce_amplitude:
        # randomly choose a remaining dimension to damage so we have some damage
        if randomizer.random() < 0.5:
            should_shorten_duration = True
        else:
            should_reduce_amplitude = True

    damaged_duration = tone.duration
    trailing_silence_duration = 0.0
    if should_shorten_duration:
        damaged_duration, trailing_silence_duration = _calculate_damaged_duration(tone.duration, randomizer)

    damaged_amplitude = tone.amplitude
    if should_reduce_amplitude:
        damaged_amplitude = _calculate_damaged_amplitude(tone.amplitude, randomizer)

    damaged_tone = Tone(
        frequency=tone.frequency,
        duration=damaged_duration,
        sample_rate=tone.sample_rate,
        amplitude=damaged_amplitude,
    )
    # the tone was not shortened so there is no need to return more tones/silence, just return the transformed tone
    if trailing_silence_duration == 0.0:
        return [damaged_tone]

    return [
        damaged_tone,
        _create_silence_from_tone(tone, duration=trailing_silence_duration),
    ]


def _damage_selected_tone_for_dimension(
    tone: Tone,
    dimension: ToneDimension,
    randomizer: random.Random,
) -> list[Tone]:
    if dimension == ToneDimension.FREQUENCY:
        return [_create_silence_from_tone(tone, duration=tone.duration)]

    if dimension == ToneDimension.DURATION:
        damaged_duration, trailing_silence_duration = _calculate_damaged_duration(tone.duration, randomizer)
        return [
            Tone(
                frequency=tone.frequency,
                duration=damaged_duration,
                sample_rate=tone.sample_rate,
                amplitude=tone.amplitude,
            ),
            _create_silence_from_tone(tone, duration=trailing_silence_duration),
        ]

    if dimension == ToneDimension.AMPLITUDE:
        return [
            Tone(
                frequency=tone.frequency,
                duration=tone.duration,
                sample_rate=tone.sample_rate,
                amplitude=_calculate_damaged_amplitude(tone.amplitude, randomizer),
            )
        ]
    raise ValueError(f"Unsupported fragment dimension: {dimension}")


def _find_valid_chunk_starts(
    damaged_positions: set[int],
    tone_count: int,
    chunk_size: int,
) -> list[int]:
    valid_starts: list[int] = []
    last_start = tone_count - chunk_size

    for start_index in range(last_start + 1):
        chunk_positions = range(start_index, start_index + chunk_size)
        if all(position not in damaged_positions for position in chunk_positions):
            valid_starts.append(start_index)

    return valid_starts


def _select_chunks_to_damage(
    tone_count: int,
    damage_pct: int,
    damage_tones_chunk_size: int,
    repeatable_damage_key: str | None = None,
) -> list[list[int]]:
    _validate_fragment_params(damage_pct=damage_pct, damage_tones_chunk_size=damage_tones_chunk_size)

    target_damaged_tone_count = _calculate_how_many_tones_to_damage(
        tone_count=tone_count,
        damage_pct=damage_pct,
    )
    if target_damaged_tone_count == 0:
        return []

    randomizer = (
        _create_damage_pattern_randomizer(repeatable_damage_key)
        if repeatable_damage_key is not None
        else random.Random()
    )
    damaged_positions: set[int] = set()
    selected_chunks: list[list[int]] = []

    while len(damaged_positions) < target_damaged_tone_count:
        remaining_damage_budget = target_damaged_tone_count - len(damaged_positions)
        widest_allowed_chunk_size = min(damage_tones_chunk_size, remaining_damage_budget)
        selected_chunk_size = 0
        valid_starts: list[int] = []

        for candidate_chunk_size in range(widest_allowed_chunk_size, 0, -1):
            candidate_starts = _find_valid_chunk_starts(
                damaged_positions=damaged_positions,
                tone_count=tone_count,
                chunk_size=candidate_chunk_size,
            )
            if candidate_starts:
                selected_chunk_size = candidate_chunk_size
                valid_starts = candidate_starts
                break

        if not valid_starts:
            # the algorithm thinks damage is still owed, but there is nowhere legal left to put it.
            raise RuntimeError("unable to select fragment chunks for the requested damage pattern")

        start_index = randomizer.choice(valid_starts)
        selected_chunk = list(range(start_index, start_index + selected_chunk_size))
        damaged_positions.update(selected_chunk)
        selected_chunks.append(selected_chunk)

    return selected_chunks


def fragment_transform(
    tones: list[Tone],
    damage_pct: int,
    damage_tones_chunk_size: int,
    dimension: ToneDimension | None = None,
    repeatable_damage_key: str | None = None,
) -> list[Tone]:
    _validate_fragment_params(damage_pct=damage_pct, damage_tones_chunk_size=damage_tones_chunk_size)

    randomizer = (
        _create_damage_pattern_randomizer(repeatable_damage_key)
        if repeatable_damage_key is not None
        else random.Random()
    )

    if damage_pct == 0:
        return [
            Tone(
                frequency=tone.frequency,
                duration=tone.duration,
                sample_rate=tone.sample_rate,
                amplitude=tone.amplitude,
            )
            for tone in tones
        ]

    selected_chunks = _select_chunks_to_damage(
        tone_count=len(tones),
        damage_pct=damage_pct,
        damage_tones_chunk_size=damage_tones_chunk_size,
        repeatable_damage_key=repeatable_damage_key,
    )
    damaged_positions = {position for chunk in selected_chunks for position in chunk}
    transformed_tones: list[Tone] = []

    for tone_index, tone in enumerate(tones):
        if tone_index not in damaged_positions:
            transformed_tones.append(
                Tone(
                    frequency=tone.frequency,
                    duration=tone.duration,
                    sample_rate=tone.sample_rate,
                    amplitude=tone.amplitude,
                )
            )
            continue

        if dimension is None:
            transformed_tones.extend(_damage_selected_tone_across_dimensions(tone, randomizer))
        else:
            transformed_tones.extend(_damage_selected_tone_for_dimension(tone, dimension, randomizer))

    return transformed_tones


def fragment_phrase_transform(context: PhraseTransformContext, params: FragmentParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    transformed_tones = fragment_transform(
        phrase_tones,
        damage_pct=params.damage_pct,
        damage_tones_chunk_size=params.damage_tones_chunk_size,
        dimension=params.dimension,
        repeatable_damage_key=params.repeatable_damage_key,
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])
