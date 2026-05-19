import pytest

from composition.parser import parse_motifs


def test_parse_motifs_rejects_non_string_motif_names():
    numeric_motif_name = 123
    motif_definition = {numeric_motif_name: ["440"]}

    with pytest.raises(ValueError):
        parse_motifs(motif_definition)
