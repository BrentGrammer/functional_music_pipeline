from __future__ import annotations

from collections.abc import Mapping

from transforms.profiles import StochasticProfile


def validate_add_pedal_point_params(transform_params: Mapping[str, object]) -> None:
    if transform_params.get("mode") != "repeat":
        return

    if "pulse_duration" not in transform_params:
        raise ValueError("The 'add_pedal_point' transform requires 'pulse_duration' when mode is 'repeat'.")


def validate_geological_params(transform_params: Mapping[str, object]) -> None:
    profile = transform_params.get("profile")
    if profile is None:
        return

    if isinstance(profile, dict):
        if "type" not in profile:
            raise ValueError("The 'geological' transform requires the 'profile' object to have a 'type' field.")
        if not isinstance(profile["type"], str):
            raise ValueError("The 'geological' transform requires the 'profile.type' field to be a string.")
    elif not isinstance(profile, StochasticProfile):
        raise ValueError("The 'geological' transform requires 'profile' to be an object.")
