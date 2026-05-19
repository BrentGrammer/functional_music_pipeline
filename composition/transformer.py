from collections.abc import Callable
from typing import TypeAlias

from composition.score_plan import (
    PhraseTransformRequest,
    ScorePlan,
    ScoreTransformRequest,
)
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone_utils import copy_tones
from score_model.voice import Voice
from transforms.base import PhraseTransformContext
from transforms.registry import PHRASE_TRANSFORMS, SCORE_TRANSFORMS

PreparedTransform: TypeAlias = Callable[[Score], Score]


def build_score(score_plan: ScorePlan) -> Score:
    voices = []
    for voice_plan in score_plan.voices:
        phrases = []
        for phrase_plan in voice_plan.phrases:
            motifs = []
            for plan_motif in phrase_plan.motifs:
                motifs.append(Motif(name=plan_motif.name, tones=copy_tones(plan_motif.tones)))
            phrases.append(Phrase(motifs=motifs))
        voices.append(Voice(phrases=phrases))
    return Score(voices=voices)


def prepare_phrase_transform(request: PhraseTransformRequest) -> PreparedTransform:
    req = request.transform_request
    transform_name = req.name
    transform_params = req.params

    if transform_name in PHRASE_TRANSFORMS:
        descriptor = PHRASE_TRANSFORMS[transform_name]
    elif transform_name in SCORE_TRANSFORMS:
        raise ValueError(f"Transform '{transform_name}' is only available as a score transform.")
    else:
        raise ValueError(f"Unknown phrase transform '{transform_name}'")

    descriptor.validate_params(transform_params)

    def prepared_transform(score: Score) -> Score:
        context = PhraseTransformContext(
            score=score,
            voice_index=request.voice_index,
            phrase_index=request.phrase_index,
        )

        transformed_phrase = descriptor.transform(context, transform_params)

        new_voices = []
        for v_idx, voice in enumerate(score.voices):
            if v_idx == request.voice_index:
                new_phrases = list(voice.phrases)
                new_phrases[request.phrase_index] = transformed_phrase
                new_voices.append(Voice(phrases=new_phrases))
            else:
                new_voices.append(voice)

        return Score(voices=new_voices)

    return prepared_transform


def prepare_score_transform(request: ScoreTransformRequest) -> PreparedTransform:
    req = request.transform_request
    transform_name = req.name
    transform_params = req.params

    if transform_name in SCORE_TRANSFORMS:
        descriptor = SCORE_TRANSFORMS[transform_name]
    elif transform_name in PHRASE_TRANSFORMS:
        raise ValueError(f"Transform '{transform_name}' is only available as a phrase transform.")
    else:
        raise ValueError(f"Unknown score transform '{transform_name}'")

    descriptor.validate_params(transform_params)

    def prepared_transform(score: Score) -> Score:
        return descriptor.transform(score, transform_params)

    return prepared_transform


def assemble_prepared_transforms(score_plan: ScorePlan) -> list[PreparedTransform]:
    prepared_transforms = []

    for phrase_req in score_plan.phrase_transform_requests:
        prepared_transforms.append(prepare_phrase_transform(phrase_req))

    for score_req in score_plan.score_transform_requests:
        prepared_transforms.append(prepare_score_transform(score_req))

    return prepared_transforms


def transform_score(score_plan: ScorePlan) -> Score:
    current_score = build_score(score_plan)
    for transform in assemble_prepared_transforms(score_plan):
        current_score = transform(current_score)
    return current_score
