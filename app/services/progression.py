import math
import datetime

# Max 6 quests yield XP per day
MAX_QUESTS_XP_PER_DAY = 6
# Each quest gives 10 XP
XP_PER_QUEST = 10

def xp_for_level(level: int) -> int:
    """Returns the total XP required to reach a given level. (Simple quadratic curve)"""
    # Level 1 = 0 XP
    # Level 2 = 100 XP
    # Level 3 = 300 XP
    # Level N = 100 * sum(1 to N-1) = 50 * (N-1) * N
    if level <= 1:
        return 0
    return 50 * (level - 1) * level

def level_for_xp(xp: int) -> int:
    """Returns the level for a given total XP."""
    if xp <= 0:
        return 1
    # 50 * L^2 - 50 * L - xp = 0
    # L = (50 + sqrt(2500 + 200 * xp)) / 100
    level = math.floor((50 + math.sqrt(2500 + 200 * xp)) / 100)
    return max(1, level)

def calculate_streak_update(
    current_date: datetime.date,
    last_streak_date: datetime.date | None,
    last_freeze_date: datetime.date | None,
    current_streak: int
) -> tuple[int, datetime.date | None, str]:
    """
    Evaluates streak logic.
    Returns (new_streak, new_freeze_date, event_type)
    """
    if last_streak_date is None:
        return 1, last_freeze_date, "earned"

    delta = (current_date - last_streak_date).days

    if delta <= 0:
        return current_streak, last_freeze_date, "none"
    elif delta == 1:
        return current_streak + 1, last_freeze_date, "earned"
    elif delta == 2:
        # Missed 1 day. Check freeze
        missed_day = last_streak_date + datetime.timedelta(days=1)
        if last_freeze_date is None or (missed_day - last_freeze_date).days >= 7:
            return current_streak + 1, missed_day, "freeze_used"
        else:
            return 1, last_freeze_date, "broken_then_earned"
    else:
        # Missed 2+ days
        return 1, last_freeze_date, "broken_then_earned"
