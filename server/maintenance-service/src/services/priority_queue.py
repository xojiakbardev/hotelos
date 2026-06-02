"""Maintenance priority queue.

The brief's third required data structure — `heapq` — lives here. Issues
are persisted in Postgres; whenever someone (a technician's "what's next?"
request, the manager's dashboard) needs the ordered queue, we read the
unassigned rows from the DB and rank them in-memory using `heapq`.

Ranking rules (brief 1.2):

  1. Urgency: Critical > High > Normal > Low.
  2. Tiebreaker: earliest `reported_at` first (FIFO inside a priority).

`heapq` is a min-heap, so we encode urgency as a numeric rank where
Critical = 0 (lowest number → highest priority).

A separate position-index is appended to each tuple so that ties are
broken deterministically *and* `Issue` instances never need to be
compared by Python's default ordering rules (they have none).
"""

from __future__ import annotations

import heapq

from src.domain.enums import Urgency
from src.domain.models import Issue

URGENCY_RANK: dict[Urgency, int] = {
    Urgency.CRITICAL: 0,
    Urgency.HIGH: 1,
    Urgency.NORMAL: 2,
    Urgency.LOW: 3,
}


def rank_by_priority(issues: list[Issue]) -> list[Issue]:
    """Return `issues` reordered so the head is "what to work on next"."""
    heap: list[tuple] = []
    for idx, issue in enumerate(issues):
        heapq.heappush(
            heap,
            (
                URGENCY_RANK[Urgency(issue.urgency)],
                issue.reported_at,
                idx,
                issue,
            ),
        )

    ordered: list[Issue] = []
    while heap:
        _, _, _, issue = heapq.heappop(heap)
        ordered.append(issue)
    return ordered
