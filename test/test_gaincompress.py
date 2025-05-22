import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from audio_filters import gain_compress


rng = np.random.default_rng(42)

def test_clipping_range():
    x = rng.uniform(-2, 2, size=50_000)
    y = gain_compress(x, threshold_db=-6, limiter_db=0)
    assert y.max() <= 1.0  # 0 dBFS
    assert y.min() >= -1.0

def test_below_threshold_untouched():
    x = rng.uniform(-0.5, 0.5, size=10_000)  # ≈ ‑6 dBFS
    y = gain_compress(x, threshold_db=-1, limiter_db=0)
    np.testing.assert_allclose(x, y, atol=1e-6)