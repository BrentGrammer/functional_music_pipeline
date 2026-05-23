import hashlib
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
    damage_pattern_key: str | None


def _create_fragment_params(parsed_params: ParsedTransformParams) -> FragmentParams:
    damage_pct = parsed_params.required("damage_pct", int)
    damage_tones_chunk_size = parsed_params.required("damage_tones_chunk_size", int)
    damage_pattern_key = parsed_params.required("damage_pattern_key", (str, type(None)))

    _validate_fragment_params(damage_pct=damage_pct, damage_tones_chunk_size=damage_tones_chunk_size)

    return FragmentParams(
        damage_pct=damage_pct,
        damage_tones_chunk_size=damage_tones_chunk_size,
        damage_pattern_key=damage_pattern_key,
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
        "damage_pattern_key": TransformParamFieldSpec(
            schema=StringParam(),
            default=None,
        ),
    },
)


def _create_damage_pattern_randomizer(damage_pattern_key: str) -> random.Random:
    seed_bytes = hashlib.sha256(damage_pattern_key.encode("utf-8")).digest()
    seed = int.from_bytes(seed_bytes[:8], byteorder="big", signed=False)
    return random.Random(seed)


def fragment_transform(
    tones: list[Tone],
    damage_pct: int,
    damage_tones_chunk_size: int,
    damage_pattern_key: str | None = None,
) -> list[Tone]:
    _validate_fragment_params(damage_pct=damage_pct, damage_tones_chunk_size=damage_tones_chunk_size)

    if damage_pattern_key is not None:
        _create_damage_pattern_randomizer(damage_pattern_key)

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
        damage_pattern_key=params.damage_pattern_key,
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])
