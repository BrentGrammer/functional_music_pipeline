import logging
from typing import NamedTuple

from mido import Message, MetaMessage, MidiFile, MidiTrack  # type: ignore[import-untyped]

from score_model.pitch_utils import frequency_to_semitones
from score_model.score import Score
from score_model.tone import Tone
from score_model._migration import _legacy_flatten_voice_tones

logger = logging.getLogger(__name__)

TUNING_ANCHOR_MIDI_NOTE = 69
TUNING_ANCHOR_FREQUENCY_HZ = 440.0
MIN_MIDI_NOTE = 0
MAX_MIDI_NOTE = 127
MIN_MIDI_VELOCITY = 0
MAX_MIDI_VELOCITY = 127
MAX_MIDI_CHANNELS = 16
DRUM_CHANNEL = 9
TICKS_PER_SECOND = 960

# MIDI Pitch Bend is a 14-bit value (-8192 to 8191).
# We mapped this full range to +/- 1 semitone (100 cents) via RPN messages.
MIN_PITCHWHEEL_VALUE = -8192
MAX_PITCHWHEEL_VALUE = 8191
CENTS_PER_SEMITONE = 100.0


class MidiPitch(NamedTuple):
    note: int
    offset_cents: float


def _constrain_to_valid_midi_range(value: int, minimum: int, maximum: int) -> int:
    """Keeps generated MIDI notes and velocities within their valid integer ranges."""
    return max(minimum, min(maximum, value))


def _initialize_pitch_bend_range(channel: int) -> list[Message]:
    """
    Returns the standard MIDI Registered Parameter Number (RPN) sequence required 
    to explicitly set the pitch bend range to +/- 1 semitone for a given channel.
    This ensures microtonal tuning is interpreted correctly by the target DAW/VST.
    """
    # We use paired 7-bit Coarse (MSB) and Fine (LSB) Control Change messages here 
    # *only* to configure the VST's maximum pitch bend range. The actual microtonal 
    # note bends are sent later using dedicated 14-bit Pitchwheel messages.
    CC_SELECT_PARAMETER_COARSE_MSB = 101
    CC_SELECT_PARAMETER_FINE_LSB = 100
    CC_SET_PARAMETER_VALUE_COARSE_MSB = 6
    CC_SET_PARAMETER_VALUE_FINE_LSB = 38

    PITCH_BEND_SENSITIVITY_PARAMETER = 0
    TARGET_BEND_RANGE_SEMITONES = 1
    TARGET_BEND_RANGE_CENTS = 0
    IMMEDIATE_EXECUTION_TIME = 0

    return [
        Message("control_change", channel=channel, control=CC_SELECT_PARAMETER_COARSE_MSB, value=PITCH_BEND_SENSITIVITY_PARAMETER, time=IMMEDIATE_EXECUTION_TIME),
        Message("control_change", channel=channel, control=CC_SELECT_PARAMETER_FINE_LSB, value=PITCH_BEND_SENSITIVITY_PARAMETER, time=IMMEDIATE_EXECUTION_TIME),
        Message("control_change", channel=channel, control=CC_SET_PARAMETER_VALUE_COARSE_MSB, value=TARGET_BEND_RANGE_SEMITONES, time=IMMEDIATE_EXECUTION_TIME),
        Message("control_change", channel=channel, control=CC_SET_PARAMETER_VALUE_FINE_LSB, value=TARGET_BEND_RANGE_CENTS, time=IMMEDIATE_EXECUTION_TIME),
    ]


def frequency_to_midi_note(frequency: float) -> MidiPitch:
    if frequency <= 0:
        raise ValueError("Frequency must be greater than zero.")

    exact_note = TUNING_ANCHOR_MIDI_NOTE + frequency_to_semitones(frequency, TUNING_ANCHOR_FREQUENCY_HZ)
    rounded_note = round(exact_note)
    offset_cents = (exact_note - rounded_note) * 100

    clamped_note = _constrain_to_valid_midi_range(rounded_note, MIN_MIDI_NOTE, MAX_MIDI_NOTE)

    return MidiPitch(note=clamped_note, offset_cents=offset_cents)


def amplitude_to_velocity(amplitude: float) -> int:
    velocity = round(amplitude * MAX_MIDI_VELOCITY)

    return _constrain_to_valid_midi_range(velocity, MIN_MIDI_VELOCITY, MAX_MIDI_VELOCITY)


def duration_to_ticks(duration: float) -> int:
    if duration < 0:
        raise ValueError("Duration cannot be negative.")

    return round(duration * TICKS_PER_SECOND)


def is_rest(tone: Tone) -> bool:
    return tone.frequency == 0 or tone.amplitude == 0


def save_score_to_midi(score: Score, filename: str) -> None:
    if len(score.voices) > (MAX_MIDI_CHANNELS - 1):
        logger.warning(
            f"MIDI export only supports {MAX_MIDI_CHANNELS - 1} microtonal voices. "
            f"Voices 16 and above have been rounded to standard tuning."
        )

    microseconds_per_second = 1_000_000
    midi_file = MidiFile(type=1, ticks_per_beat=TICKS_PER_SECOND)

    # MIDI stores time as ticks. One beat per second makes TICKS_PER_SECOND
    # preserve the app's existing seconds-based Tone durations.
    tempo_track = MidiTrack()
    tempo_track.append(MetaMessage("set_tempo", tempo=microseconds_per_second, time=0))
    midi_file.tracks.append(tempo_track)

    for voice_index, voice in enumerate(score.voices):
        # MIDI only supports 16 channels (0-15). If we have >15 voices, we must 
        # wrap the assignments back to 0 to prevent writing invalid MIDI data.
        # We modulo by 15 (MAX_MIDI_CHANNELS - 1) because Channel 9 is 
        # conventionally reserved for drums and we want to skip it entirely.
        channel = voice_index % (MAX_MIDI_CHANNELS - 1)
        if channel >= DRUM_CHANNEL:
            channel += 1

        voice_track = MidiTrack()
        voice_track.extend(_initialize_pitch_bend_range(channel))
        
        pending_rest_ticks = 0

        for tone in _legacy_flatten_voice_tones(voice):
            if is_rest(tone):
                pending_rest_ticks += duration_to_ticks(tone.duration)
                continue

            pitch = frequency_to_midi_note(tone.frequency)
            
            # Zero and Fallback Strategy:
            # We only have 15 usable channels. Voices beyond index 14 are wrapped 
            # to shared channels. To prevent pitch wheel conflicts on these shared 
            # channels, we must force their microtonal offset to 0.0 (standard 12-TET).
            offset_cents = pitch.offset_cents
            if voice_index >= (MAX_MIDI_CHANNELS - 1):
                offset_cents = 0.0
                
            # Convert cents to the 14-bit pitchwheel range, where +/- 8192 equals +/- 100 cents.
            raw_bend_value = int((offset_cents / CENTS_PER_SEMITONE) * 8192)
            bend_value = _constrain_to_valid_midi_range(
                raw_bend_value, MIN_PITCHWHEEL_VALUE, MAX_PITCHWHEEL_VALUE
            )
                
            midi_note = pitch.note
            velocity = amplitude_to_velocity(tone.amplitude)
            duration_ticks = duration_to_ticks(tone.duration)

            voice_track.append(
                Message("pitchwheel", channel=channel, pitch=bend_value, time=pending_rest_ticks)
            )
            voice_track.append(
                Message("note_on", channel=channel, note=midi_note, velocity=velocity, time=0)
            )
            voice_track.append(
                Message("note_off", channel=channel, note=midi_note, velocity=0, time=duration_ticks)
            )
            pending_rest_ticks = 0

        midi_file.tracks.append(voice_track)

    midi_file.save(filename)
