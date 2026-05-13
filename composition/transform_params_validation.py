from __future__ import annotations


def validate_add_pedal_point_params(transform_params: dict[str, object]) -> None:
    if transform_params.get("mode") != "repeat":
        return

    if "pulse_duration" not in transform_params:
        raise ValueError("The 'add_pedal_point' transform requires 'pulse_duration' when mode is 'repeat'.")
