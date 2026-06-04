"""Room freshness score and dynamic pricing.

Freshness decays linearly from 1.0 (just cleaned) to 0.0 (stale).
Dynamic price = base_price × (0.85 + 0.30 × freshness_score).
  Score 1.0 → base_price × 1.15  (+15% premium)
  Score 0.0 → base_price × 0.85  (-15% discount)
"""

from __future__ import annotations

from datetime import datetime, timezone

# How many hours until freshness decays from 1.0 to 0.0
FRESHNESS_DECAY_HOURS: float = 24.0


def compute_freshness_score(last_cleaned_at: datetime) -> float:
    """Compute freshness score (0.0 to 1.0) based on time since last cleaning."""
    now = datetime.now(timezone.utc)
    hours_since = (now - last_cleaned_at).total_seconds() / 3600.0
    score = max(0.0, 1.0 - (hours_since / FRESHNESS_DECAY_HOURS))
    return round(score, 4)


def compute_dynamic_price(base_price_minor_units: int, freshness_score: float) -> int:
    """Compute dynamic price based on freshness.

    Formula: base_price × (0.85 + 0.30 × score)
    """
    multiplier = 0.85 + 0.30 * freshness_score
    return round(base_price_minor_units * multiplier)
