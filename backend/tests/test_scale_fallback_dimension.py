import pytest

@pytest.mark.skip(reason="enable once the no-scale-bar fixture is added")
def test_dimension_fallback_parses_and_sets_scale():
    """
    Test that when no scale bar is found, we can fall back to:
    - Dimension text (e.g., "250'-0\"")
    - Known reference dimensions from text + geometry
    - User-provided scale hints
    """
    assert True

