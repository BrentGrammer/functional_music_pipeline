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
    TransformParamFieldSpec,
    TransformParamsSpec,
)


@dataclass(frozen=True)
class FragmentParams:
    damage_pct: int
    damage_tones_chunk_size: int # how wide a span of tones to damage throughout the phrase
    repeatable_damage_key: str | None


def _create_fragment_params(parsed_params: ParsedTransformParams) -> FragmentParams:
    damage_pct = parsed_params.required("damage_pct", int)
    damage_tones_chunk_size = parsed_params.required("damage_tones_chunk_size", int)
    repeatable_damage_key = parsed_params.required("repeatable_damage_key", (str, type(None)))

    _validate_fragment_params(damage_pct=damage_pct, damage_tones_chunk_size=damage_tones_chunk_size)

    return FragmentParams(
        damage_pct=damage_pct,
        damage_tones_chunk_size=damage_tones_chunk_size,
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
        desired_chunk_size = min(damage_tones_chunk_size, remaining_damage_budget)
        current_chunk_size = desired_chunk_size

        valid_starts = _find_valid_chunk_starts(
            damaged_positions=damaged_positions,
            tone_count=tone_count,
            chunk_size=current_chunk_size,
        )

        while not valid_starts and current_chunk_size > 1:
            current_chunk_size -= 1
            valid_starts = _find_valid_chunk_starts(
                damaged_positions=damaged_positions,
                tone_count=tone_count,
                chunk_size=current_chunk_size,
            )

        if not valid_starts:
            # the algorithm thinks damage is still owed, but there is nowhere legal left to put it.
            raise ValueError("unable to select fragment chunks for the requested damage pattern")

        start_index = randomizer.choice(valid_starts)
        selected_chunk = list(range(start_index, start_index + current_chunk_size))
        damaged_positions.update(selected_chunk)
        selected_chunks.append(selected_chunk)

    return selected_chunks


def fragment_transform(
    tones: list[Tone],
    damage_pct: int,
    damage_tones_chunk_size: int,
    repeatable_damage_key: str | None = None,
) -> list[Tone]:
    _validate_fragment_params(damage_pct=damage_pct, damage_tones_chunk_size=damage_tones_chunk_size)

    if repeatable_damage_key is not None:
        _create_damage_pattern_randomizer(repeatable_damage_key)

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

    raise NotImplementedError("fragment transform damage behavior is not implemented yet")


def fragment_phrase_transform(context: PhraseTransformContext, params: FragmentParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    transformed_tones = fragment_transform(
        phrase_tones,
        damage_pct=params.damage_pct,
        damage_tones_chunk_size=params.damage_tones_chunk_size,
        repeatable_damage_key=params.repeatable_damage_key,
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])
