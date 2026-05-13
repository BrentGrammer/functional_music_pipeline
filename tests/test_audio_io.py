import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from audio_rendering.wav_writer import mix_waveforms, save_score_to_wav
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice


class TestMixWaveforms:
    def test_mix_empty(self):
        result = mix_waveforms([])
        assert len(result) == 0
        assert result.dtype == np.int16

    def test_mix_different_lengths_padding(self):
        w1 = np.array([100, 200, 300], dtype=np.int16)
        w2 = np.array([50, 50], dtype=np.int16)
        
        result = mix_waveforms([w1, w2])
        
        expected_length = max(len(w1), len(w2))
        assert len(result) == expected_length
        np.testing.assert_array_equal(result, np.array([150, 250, 300], dtype=np.int16))

    def test_mix_with_normalization(self):
        loud_track_1 = np.array([20000, -20000], dtype=np.int16)
        loud_track_2 = np.array([20000, -20000], dtype=np.int16)
        
        result = mix_waveforms([loud_track_1, loud_track_2])
        
        assert len(result) == 2
        assert result[0] == 32767
        assert result[1] == -32767

class TestSaveScoreToWav:
    def test_save_score_to_wav(self, tmp_path):
        tone1 = Tone(frequency=440.0, duration=0.1)
        tone2 = Tone(frequency=880.0, duration=0.1)
        score = Score([Voice([tone1]), Voice([tone2])])
        
        output_file = tmp_path / "test_output.wav"
        
        save_score_to_wav(score, filename=str(output_file))
        
        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_save_score_exceeds_max_duration(self, tmp_path):
        from audio_rendering.wav_writer import MAX_DURATION_SECONDS
        
        long_tone = Tone(frequency=440.0, duration=MAX_DURATION_SECONDS + 1.0)
        score = Score([Voice([long_tone])])
        
        output_file = tmp_path / "test_output_too_long.wav"
        
        with pytest.raises(ValueError, match="exceeds the maximum allowed duration"):
            save_score_to_wav(score, filename=str(output_file))
