import math
from collections import Counter


def calculate_entropy(value: str) -> float:
    """Calculate Shannon entropy of a string in bits per character."""
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in counts.values()
    )
