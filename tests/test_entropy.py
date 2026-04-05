from keyguard.entropy import calculate_entropy


def test_empty_string_returns_zero():
    assert calculate_entropy("") == 0.0


def test_uniform_string_returns_zero():
    # All same character — zero entropy
    assert calculate_entropy("aaaaaaaaaa") == 0.0


def test_high_entropy_string():
    # A realistic Google API key has entropy ~4.5-5.0
    key = "AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q"
    assert calculate_entropy(key) > 4.0


def test_low_entropy_placeholder():
    # A placeholder like "REPLACE_ME_WITH_KEY" has low entropy
    assert calculate_entropy("REPLACE_ME_WITH_KEY") < 3.6


def test_known_entropy():
    # "ab" has exactly 1 bit of entropy (two equally likely chars)
    result = calculate_entropy("aabb")
    assert abs(result - 1.0) < 0.001
