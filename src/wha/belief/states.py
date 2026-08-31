"""Static 4096x12 boolean presence matrix for exact state enumeration."""

import numpy as np

from wha.models import CauseId

# Stable cause ordering used across all belief matrices
CAUSE_ORDER: list[CauseId] = [
    CauseId.INFECTION,
    CauseId.ALCOHOL,
    CauseId.EXERTION,
    CauseId.SLEEP_RESTRICTION,
    CauseId.STRESS,
    CauseId.LUTEAL,
    CauseId.VACCINATION,
    CauseId.TRAVEL,
    CauseId.MEDICATION,
    CauseId.RECOVERY_TAIL,
    CauseId.SENSOR_ARTIFACT,
    CauseId.UNEXPLAINED,
]

NUM_CAUSES = len(CAUSE_ORDER)  # 12
NUM_STATES = 1 << NUM_CAUSES  # 4096

# PRESENT[s, i] is True iff cause i is active in state s (bit i of integer s is 1)
PRESENT: np.ndarray = np.array(
    [[(s >> i) & 1 == 1 for i in range(NUM_CAUSES)] for s in range(NUM_STATES)],
    dtype=bool,
)
