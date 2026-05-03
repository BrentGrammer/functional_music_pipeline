from composition.parser import parse_composition


class TestAccelerandoParserIntegration:
    """Tests that accelerando can be invoked from composition JSON."""

    def test_accelerando_with_preset_params(self):
        composition = {
            "motifs": {
                "theme": ["440:0.5", "494:0.5", "523:0.5"]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["theme"],
                                "transforms": [
                                    {
                                        "name": "accelerando",
                                        "params": {
                                            "strength": "high",
                                            "jaggedness": "low"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        score = parse_composition(composition)
        tones = score.voices[0].tones

        assert len(tones) == 3

        # Accelerando should decrease durations across the phrase
        assert tones[0].duration > tones[1].duration
        assert tones[1].duration > tones[2].duration

    def test_accelerando_with_numeric_params(self):
        composition = {
            "motifs": {
                "theme": ["440:0.5", "494:0.5", "523:0.5"]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["theme"],
                                "transforms": [
                                    {
                                        "name": "accelerando",
                                        "params": {
                                            "strength": 0.75,
                                            "jaggedness": 0.0
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        score = parse_composition(composition)
        tones = score.voices[0].tones

        assert len(tones) == 3
        assert tones[0].duration > tones[2].duration

    def test_accelerando_preserves_frequencies(self):
        composition = {
            "motifs": {
                "theme": ["440:0.5", "494:0.5", "523:0.5"]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["theme"],
                                "transforms": [
                                    {
                                        "name": "accelerando",
                                        "params": {
                                            "strength": "medium",
                                            "jaggedness": "none"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        score = parse_composition(composition)
        tones = score.voices[0].tones

        assert tones[0].frequency == 440
        assert tones[1].frequency == 494
        assert tones[2].frequency == 523


class TestRitardandoParserIntegration:
    """Tests that ritardando can be invoked from composition JSON."""

    def test_ritardando_with_preset_params(self):
        composition = {
            "motifs": {
                "theme": ["440:0.5", "494:0.5", "523:0.5"]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["theme"],
                                "transforms": [
                                    {
                                        "name": "ritardando",
                                        "params": {
                                            "strength": "high",
                                            "jaggedness": "low"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        score = parse_composition(composition)
        tones = score.voices[0].tones

        assert len(tones) == 3

        # Ritardando should increase durations across the phrase
        assert tones[0].duration < tones[1].duration
        assert tones[1].duration < tones[2].duration

    def test_ritardando_with_numeric_params(self):
        composition = {
            "motifs": {
                "theme": ["440:0.5", "494:0.5", "523:0.5"]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["theme"],
                                "transforms": [
                                    {
                                        "name": "ritardando",
                                        "params": {
                                            "strength": 0.75,
                                            "jaggedness": 0.0
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        score = parse_composition(composition)
        tones = score.voices[0].tones

        assert len(tones) == 3
        assert tones[0].duration < tones[2].duration

    def test_ritardando_preserves_frequencies(self):
        composition = {
            "motifs": {
                "theme": ["440:0.5", "494:0.5", "523:0.5"]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["theme"],
                                "transforms": [
                                    {
                                        "name": "ritardando",
                                        "params": {
                                            "strength": "medium",
                                            "jaggedness": "none"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        score = parse_composition(composition)
        tones = score.voices[0].tones

        assert tones[0].frequency == 440
        assert tones[1].frequency == 494
        assert tones[2].frequency == 523
