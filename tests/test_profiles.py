from transforms.profiles import StochasticProfile


class ConformingProfile:
    def generate(self, length: int) -> list[float]:
        return [0.0] * length


class NonConformingProfile:
    def produce(self, length: int) -> list[float]:
        return [0.0] * length


def test_stochastic_profile_is_importable():
    assert StochasticProfile is not None


def test_conforming_class_matches_protocol_structure():
    instance = ConformingProfile()
    assert isinstance(instance, StochasticProfile)


def test_non_conforming_class_does_not_match_protocol_structure():
    instance = NonConformingProfile()
    assert not isinstance(instance, StochasticProfile)
