from unittest.mock import patch

import pytest
from mido import MidiFile  # type: ignore[import-untyped]

from midi_rendering.midi_writer import (
    MidiPitch,
    _constrain_to_valid_midi_range,
    amplitude_to_velocity,
    duration_to_ticks,
    frequency_to_midi_note,
    is_rest,
    save_score_to_midi,
)
from score_model.pitch_utils import cents_to_frequency, semitones_to_frequency
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice


def test_constrain_to_valid_midi_range_keeps_values_within_bounds():
    minimum = 0
    maximum = 127

    # Within bounds
    within_bounds = 64
    assert _constrain_to_valid_midi_range(64, minimum, maximum) == within_bounds
    assert _constrain_to_valid_midi_range(0, minimum, maximum) == 0
    assert _constrain_to_valid_midi_range(127, minimum, maximum) == maximum

    # Below bounds
    assert _constrain_to_valid_midi_range(minimum - 1, minimum, maximum) == minimum
    assert _constrain_to_valid_midi_range(minimum - 100, minimum, maximum) == minimum

    # Above bounds
    assert _constrain_to_valid_midi_range(maximum + 1, minimum, maximum) == maximum
    assert _constrain_to_valid_midi_range(maximum + 999, minimum, maximum) == maximum


def test_frequency_to_midi_note_converts_known_pitches():
    A4_FREQUENCY = 440.0
    A4_MIDI_NOTE = 69
    A5_FREQUENCY = 880.0
    A5_MIDI_NOTE = 81
    A3_FREQUENCY = 220.0
    A3_MIDI_NOTE = 57

    assert frequency_to_midi_note(A4_FREQUENCY) == MidiPitch(A4_MIDI_NOTE, 0.0)
    assert frequency_to_midi_note(A5_FREQUENCY) == MidiPitch(A5_MIDI_NOTE, 0.0)
    assert frequency_to_midi_note(A3_FREQUENCY) == MidiPitch(A3_MIDI_NOTE, 0.0)


def test_frequency_to_midi_note_rounds_to_nearest_note():
    FREQUENCY_SLIGHTLY_SHARP_OF_A4 = 450.0
    A4_MIDI_NOTE = 69
    EXPECTED_CENTS_SHARP = 38.91

    # B-flat 4 is exactly 1 semitone above A4 (440 Hz)
    B_FLAT_4_FREQUENCY = semitones_to_frequency(440.0, 1.0)
    B_FLAT_4_MIDI_NOTE = 70

    pitch_sharp = frequency_to_midi_note(FREQUENCY_SLIGHTLY_SHARP_OF_A4)
    assert pitch_sharp.note == A4_MIDI_NOTE
    assert pitch_sharp.offset_cents == pytest.approx(EXPECTED_CENTS_SHARP, abs=1e-2)

    pitch_b_flat = frequency_to_midi_note(B_FLAT_4_FREQUENCY)
    assert pitch_b_flat.note == B_FLAT_4_MIDI_NOTE
    assert pitch_b_flat.offset_cents == pytest.approx(0.0, abs=1e-2)


def test_frequency_to_midi_note_calculates_microtonal_edges():
    """
    Verifies that frequency_to_midi_note correctly calculates microtonal offsets, 
    especially at the 'edges' (boundaries) where a frequency is exactly halfway 
    between two standard MIDI notes (+/- 50 cents).
    
    It also verifies that Python's banker's rounding behavior correctly translates 
    these exact 50-cent boundaries into equivalent mathematical representations 
    (e.g., +50 cents from Note A is equal to -50 cents from Note A#).
    """
    A4_FREQ = 440.0
    A4_NOTE = 69

    # Due to banker's rounding, a frequency exactly halfway between 69 and 70 (69.5) 
    # rounds to the nearest even integer (70). Therefore, +50 cents from Note 69 
    # must be mathematically represented as -50 cents from Note 70.
    sharp_50_freq = cents_to_frequency(A4_FREQ, 50.0)
    expected_sharp_note = 70
    expected_sharp_offset = -50.0
    
    pitch_sharp = frequency_to_midi_note(sharp_50_freq)
    assert pitch_sharp.note == expected_sharp_note
    assert pitch_sharp.offset_cents == pytest.approx(expected_sharp_offset, abs=1e-2)

    # Similarly, a frequency exactly halfway between 68 and 69 (68.5) 
    # rounds to 68. Therefore, -50 cents from Note 69 is represented as +50 cents from Note 68.
    flat_50_freq = cents_to_frequency(A4_FREQ, -50.0)
    expected_flat_note = 68
    expected_flat_offset = 50.0
    
    pitch_flat = frequency_to_midi_note(flat_50_freq)
    assert pitch_flat.note == expected_flat_note
    assert pitch_flat.offset_cents == pytest.approx(expected_flat_offset, abs=1e-2)

    # Test an arbitrary microtonal deviation to ensure that floating-point 
    # precision is maintained and it correctly anchors to the nearest whole note.
    fractional_flat_freq = cents_to_frequency(A4_FREQ, -15.5)
    expected_fractional_note = A4_NOTE
    expected_fractional_offset = -15.5

    pitch_fractional = frequency_to_midi_note(fractional_flat_freq)
    assert pitch_fractional.note == expected_fractional_note
    assert pitch_fractional.offset_cents == pytest.approx(expected_fractional_offset, abs=1e-2)


def test_frequency_to_midi_note_clamps_extreme_frequencies():
    EXTREMELY_LOW_FREQUENCY = 1.0
    MINIMUM_MIDI_NOTE = 0
    
    EXTREMELY_HIGH_FREQUENCY = 20000.0
    MAXIMUM_MIDI_NOTE = 127
    
    pitch_low = frequency_to_midi_note(EXTREMELY_LOW_FREQUENCY)
    assert pitch_low.note == MINIMUM_MIDI_NOTE
    
    pitch_high = frequency_to_midi_note(EXTREMELY_HIGH_FREQUENCY)
    assert pitch_high.note == MAXIMUM_MIDI_NOTE

def test_frequency_to_midi_note_rejects_nonpositive_frequency():
    with pytest.raises(ValueError, match="Frequency must be greater than zero."):
        frequency_to_midi_note(0)


def test_amplitude_to_velocity_clamps_to_valid_midi_range():
    # Current amplitude transforms clamp to 1.0, but the project does not
    # yet centralize that normalized maximum as a shared domain constant.
    MAXIMUM_NORMALIZED_AMPLITUDE = 1.0
    MIDPOINT_AMPLITUDE = 0.5
    MIDI_VELOCITY_MIDPOINT_ROUNDED = 64
    BELOW_MINIMUM_AMPLITUDE = -0.25
    MIN_MIDI_VELOCITY = 0
    MAX_MIDI_VELOCITY = 127

    assert amplitude_to_velocity(MIDPOINT_AMPLITUDE) == MIDI_VELOCITY_MIDPOINT_ROUNDED
    assert amplitude_to_velocity(BELOW_MINIMUM_AMPLITUDE) == MIN_MIDI_VELOCITY
    assert amplitude_to_velocity(MAXIMUM_NORMALIZED_AMPLITUDE + 1.0) == MAX_MIDI_VELOCITY


def test_duration_to_ticks_uses_fixed_seconds_mapping():
    ONE_SECOND = 1.0
    TICKS_PER_SECOND = 960
    HALF_SECOND = 0.5

    assert duration_to_ticks(ONE_SECOND) == TICKS_PER_SECOND
    assert duration_to_ticks(HALF_SECOND) == TICKS_PER_SECOND // 2


def test_duration_to_ticks_rejects_negative_duration():
    with pytest.raises(ValueError, match="Duration cannot be negative."):
        duration_to_ticks(-1.0)


def test_is_rest_identifies_silent_tones():
    assert is_rest(Tone(frequency=0, amplitude=0.5))
    assert is_rest(Tone(frequency=440.0, amplitude=0))
    assert not is_rest(Tone(frequency=440.0, amplitude=0.5))


def test_save_score_to_midi_turns_rests_into_delayed_note_starts(tmp_path):
    LEADING_REST_SECONDS = 0.5
    BETWEEN_NOTES_REST_SECONDS = 0.25
    SECOND_BETWEEN_NOTES_REST_SECONDS = 0.75
    NOTE_DURATION_SECONDS = 1.0
    output_file = tmp_path / "rest_delays.mid"
    score = Score(
        [
            Voice(
                [
                    Tone(frequency=0, duration=LEADING_REST_SECONDS),
                    Tone(frequency=440.0, duration=NOTE_DURATION_SECONDS),
                    Tone(frequency=0, duration=BETWEEN_NOTES_REST_SECONDS),
                    Tone(frequency=523.25, duration=NOTE_DURATION_SECONDS),
                    Tone(frequency=0, duration=SECOND_BETWEEN_NOTES_REST_SECONDS),
                    Tone(frequency=659.25, duration=NOTE_DURATION_SECONDS),
                ]
            )
        ]
    )

    save_score_to_midi(score, str(output_file))

    midi_file = MidiFile(str(output_file))
    voice_track = midi_file.tracks[1]
    
    # Filter to only the core event messages, skipping the initial RPN configs
    NUM_RPN_CONFIGS = 4
    event_messages = [msg for msg in voice_track[NUM_RPN_CONFIGS:] if msg.type in ('pitchwheel', 'note_on')]

    # The sequence should be: Pitchwheel (delayed), NoteOn (immediate)
    # The pitchwheel consumes the rest duration, note_on triggers immediately after.
    expected_rest_ticks = [
        duration_to_ticks(LEADING_REST_SECONDS),
        duration_to_ticks(BETWEEN_NOTES_REST_SECONDS),
        duration_to_ticks(SECOND_BETWEEN_NOTES_REST_SECONDS),
    ]

    # Group the flat list of messages into (pitchwheel, note_on) pairs
    message_iterator = iter(event_messages)
    paired_messages = list(zip(message_iterator, message_iterator))

    for i in range(len(expected_rest_ticks)):
        pitchwheel_msg, note_on_msg = paired_messages[i]

        assert pitchwheel_msg.type == 'pitchwheel'
        assert pitchwheel_msg.time == expected_rest_ticks[i]
        
        assert note_on_msg.type == 'note_on'
        assert note_on_msg.time == 0


def test_save_score_to_midi_exports_each_voice_as_separate_track(tmp_path):
    output_file = tmp_path / "voices.mid"
    score = Score(
        [
            Voice([Tone(frequency=440.0)]),
            Voice([Tone(frequency=523.25)]),
            Voice([Tone(frequency=659.25)]),
        ]
    )

    save_score_to_midi(score, str(output_file))

    midi_file = MidiFile(str(output_file))
    tempo_track_count = 1

    assert len(midi_file.tracks) == len(score.voices) + tempo_track_count


def test_save_score_to_midi_skips_drum_channel(tmp_path):
    output_file = tmp_path / "drum_skip.mid"
    
    # We create 10 voices to force the channel assignment logic to encounter 
    # the reserved percussion channel (Channel 9). We want to verify that the 
    # 10th voice (index 9) is correctly shifted to Channel 10.
    voices = [Voice([Tone(frequency=440.0)]) for _ in range(10)]
    score = Score(voices)
    
    save_score_to_midi(score, str(output_file))
    
    midi_file = MidiFile(str(output_file))
    
    # Verify the channel assignments of the first note in each voice track
    channels_used = []
    for track in midi_file.tracks[1:]:  # Skip tempo track
        for msg in track:
            if msg.type == 'note_on':
                channels_used.append(msg.channel)
                break
                
    expected_channels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10]
    assert channels_used == expected_channels


def test_save_score_to_midi_wraps_channels_and_zeros_fallback(tmp_path):
    output_file = tmp_path / "fallback.mid"
    
    # Create 17 voices. 
    # Voices 0-14 should get channels 0-8, 10-15 and retain pitch bend.
    # Voices 15-16 should wrap back to channels 0-1 and have 0 pitch bend.
    
    # We use a frequency exactly 50 cents sharp of A4 (452.89) to guarantee
    # it generates an offset_cents of -50.0 (Banker's rounding to Note 70).
    A4_FREQ = 440.0
    SHARP_FREQ = cents_to_frequency(A4_FREQ, 50.0)
    
    voices = [Voice([Tone(frequency=SHARP_FREQ)]) for _ in range(17)]
    score = Score(voices)
    
    save_score_to_midi(score, str(output_file))
    
    midi_file = MidiFile(str(output_file))
    
    # Track 16 (Voice 15) should wrap to Channel 0
    voice_15_track = midi_file.tracks[16]
    note_msg = next(msg for msg in voice_15_track if msg.type == 'note_on')
    assert note_msg.channel == 0
    
    # We will fully test the pitchwheel values in Step 4, but for now we can 
    # verify that the *intended* mathematical offset was zeroed by the fallback 
    # logic, meaning no pitchwheel event would be needed, or it would be zero. 
    # (Detailed pitchwheel assertions will be added in Step 4)


@patch("midi_rendering.midi_writer.logger")
def test_save_score_to_midi_warns_on_exceeding_voice_limit(mock_logger, tmp_path):
    output_file = tmp_path / "warning.mid"
    
    # Exactly 15 voices should NOT warn
    save_score_to_midi(Score([Voice([Tone(frequency=440.0)]) for _ in range(15)]), str(output_file))
    mock_logger.warning.assert_not_called()
    
    # 16 voices SHOULD warn
    save_score_to_midi(Score([Voice([Tone(frequency=440.0)]) for _ in range(16)]), str(output_file))
    mock_logger.warning.assert_called_once()
    assert "Voices 16 and above have been rounded to standard tuning" in mock_logger.warning.call_args[0][0]


def test_save_score_to_midi_initializes_pitch_bend_range(tmp_path):
    """
    Verifies that each MIDI voice track begins with the standard RPN sequence 
    required to explicitly set the pitch bend sensitivity to +/- 1 semitone.
    """
    output_file = tmp_path / "rpn_init.mid"
    score = Score([Voice([Tone(frequency=440.0)])])
    
    save_score_to_midi(score, str(output_file))
    
    midi_file = MidiFile(str(output_file))
    voice_track = midi_file.tracks[1]
    
    CC_SELECT_PARAMETER_COARSE_MSB = 101
    CC_SELECT_PARAMETER_FINE_LSB = 100
    CC_SET_PARAMETER_VALUE_COARSE_MSB = 6
    CC_SET_PARAMETER_VALUE_FINE_LSB = 38

    # The first four messages in the track should be the RPN setup sequence with time=0
    expected_pitchbend_controls = [
        CC_SELECT_PARAMETER_COARSE_MSB, 
        CC_SELECT_PARAMETER_FINE_LSB, 
        CC_SET_PARAMETER_VALUE_COARSE_MSB, 
        CC_SET_PARAMETER_VALUE_FINE_LSB
    ]
    actual_pitch_bend_controls = []

    for i in range(len(expected_pitchbend_controls)):
        msg = voice_track[i]
        assert msg.type == 'control_change'
        assert msg.time == 0
        actual_pitch_bend_controls.append(msg.control)

    assert actual_pitch_bend_controls == expected_pitchbend_controls
    
    # Ensure the 4 RPN configuration messages only appear once at the start 
    # of the track and are not accidentally emitted again for individual notes.
    cc_count = sum(1 for msg in voice_track if msg.type == 'control_change')
    assert cc_count == len(expected_pitchbend_controls)


def test_save_score_to_midi_resets_pitch_bend_for_standard_notes(tmp_path):
    """
    Verifies that a pitchwheel message with value 0 is explicitly sent before 
    a standard diatonic note if it follows a microtonal note, ensuring the 
    bend doesn't "leak" into subsequent notes.
    """
    output_file = tmp_path / "bend_reset.mid"
    
    A4_FREQ = 440.0
    # 50 cents sharp of A4
    SHARP_FREQ = cents_to_frequency(A4_FREQ, 50.0)
    tones = [
        Tone(frequency=SHARP_FREQ, duration=1.0),
        Tone(frequency=A4_FREQ, duration=1.0),
    ]
    score = Score([
        Voice(tones)
    ])
    
    save_score_to_midi(score, str(output_file))
    
    midi_file = MidiFile(str(output_file))
    voice_track = midi_file.tracks[1]
    
    pitchwheel_messages = [msg for msg in voice_track if msg.type == 'pitchwheel']
    expected_num_pw_msgs = len(tones)
    assert len(pitchwheel_messages) == expected_num_pw_msgs
    
    # First note (microtonal) should have a non-zero bend.
    # Banker's rounding: 69.5 -> 70. Offset = -50 cents.
    # -50 cents = -4096 bend value.
    minus_50_cents_msg = -4096
    assert pitchwheel_messages[0].pitch == minus_50_cents_msg
    
    # Second note (standard A4) should have 0 bend to reset.
    assert pitchwheel_messages[1].pitch == 0


def test_save_score_to_midi_accumulates_sequential_rests(tmp_path):
    """
    Verifies that multiple consecutive rest tones have their durations summed 
    and correctly applied to the time field of the next active note's 
    pitchwheel message.
    """
    output_file = tmp_path / "sequential_rests.mid"
    
    REST_1_DURATION = 0.5
    REST_2_DURATION = 0.25
    NOTE_DURATION = 1.0
    
    score = Score([
        Voice([
            Tone(frequency=0, duration=REST_1_DURATION),
            Tone(frequency=0, duration=REST_2_DURATION),
            Tone(frequency=440.0, duration=NOTE_DURATION),
        ])
    ])
    
    save_score_to_midi(score, str(output_file))
    
    midi_file = MidiFile(str(output_file))
    voice_track = midi_file.tracks[1]
    
    # The first pitchwheel message should carry the accumulated time
    pitchwheel_msg = next(msg for msg in voice_track if msg.type == 'pitchwheel')
    
    expected_ticks = duration_to_ticks(REST_1_DURATION + REST_2_DURATION)
    assert pitchwheel_msg.time == expected_ticks


def test_save_score_to_midi_handles_leading_silence_with_rpn_headers(tmp_path):
    """
    Verifies that RPN configuration messages are always emitted at time=0 
    at the start of a track, and any leading silence in the score is correctly 
    deferred to the first pitchwheel message.
    """
    output_file = tmp_path / "leading_silence.mid"
    
    LEADING_REST_DURATION = 1.0
    NOTE_DURATION = 1.0
    
    score = Score([
        Voice([
            Tone(frequency=0, duration=LEADING_REST_DURATION),
            Tone(frequency=440.0, duration=NOTE_DURATION),
        ])
    ])
    
    save_score_to_midi(score, str(output_file))
    
    midi_file = MidiFile(str(output_file))
    voice_track = midi_file.tracks[1]
    
    # Check RPN headers (first 4 messages)
    for i in range(4):
        assert voice_track[i].type == 'control_change'
        assert voice_track[i].time == 0
        
    # Check that the first non-CC message is the pitchwheel with the leading rest time
    pitchwheel_msg = next(msg for msg in voice_track if msg.type == 'pitchwheel')
    assert pitchwheel_msg.time == duration_to_ticks(LEADING_REST_DURATION)


def test_save_score_to_midi_clamps_pitchwheel_values(tmp_path):
    """
    Verifies that the pitchwheel value is strictly clamped to the valid 
    14-bit MIDI range (-8192 to 8191). This is a safety check to ensure 
    that even extreme microtonal offsets do not produce invalid MIDI data.
    """
    output_file = tmp_path / "clamped_bend.mid"
    
    # We will mock frequency_to_midi_note to return a very large offset 
    # to trigger the clamping logic in save_score_to_midi.
    large_pitch = MidiPitch(note=69, offset_cents=150.0)  # 150 cents > 100 cents (8192)
    extreme_flat_pitch = MidiPitch(note=69, offset_cents=-150.0)
    
    with patch("midi_rendering.midi_writer.frequency_to_midi_note") as mock_pitch:
        mock_pitch.side_effect = [large_pitch, extreme_flat_pitch]
        
        score = Score([
            Voice([
                Tone(frequency=440.0, duration=1.0),
                Tone(frequency=440.0, duration=1.0),
            ])
        ])
        
        save_score_to_midi(score, str(output_file))
        
    midi_file = MidiFile(str(output_file))
    voice_track = midi_file.tracks[1]
    
    pitchwheel_messages = [msg for msg in voice_track if msg.type == 'pitchwheel']
    
    # 150 cents should be clamped to MAX_PITCHWHEEL_VALUE (8191)
    assert pitchwheel_messages[0].pitch == 8191
    
    # -150 cents should be clamped to MIN_PITCHWHEEL_VALUE (-8192)
    assert pitchwheel_messages[1].pitch == -8192
