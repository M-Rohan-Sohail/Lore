import pytest
import json
import datetime
from zoneinfo import ZoneInfo
from app.services.progression import calculate_streak_update, level_for_xp

def test_level_curve():
    assert level_for_xp(0) == 1
    assert level_for_xp(50) == 1
    assert level_for_xp(100) == 2
    assert level_for_xp(299) == 2
    assert level_for_xp(300) == 3

def test_streak_vectors():
    with open("/home/rohan/Desktop/Startup-Plan-II/lore-pack/fixtures/streak_vectors.json") as f:
        data = json.load(f)
        
    for vector in data["vectors"]:
        streak = 0
        last_streak_date = None
        last_freeze = None
        
        for idx, log in enumerate(vector["logs"]):
            tz = ZoneInfo(log["tz"])
            # parse t e.g. "2026-03-02T18:00:00+05:00"
            dt = datetime.datetime.fromisoformat(log["t"]).astimezone(tz)
            current_date = dt.date()
            
            # The test case might have 'n' representing multiple logs
            n = log.get("n", 1)
            for i in range(n):
                new_streak, new_freeze, event = calculate_streak_update(
                    current_date, last_streak_date, last_freeze, streak
                )
                
                # Apply update
                if event != "none":
                    streak = new_streak
                    last_streak_date = current_date
                    last_freeze = new_freeze
                    
            expected = vector["expect"][idx]
            
            # Only assert things that the progression module calculates:
            # We don't assert xp_awarded_last or replay logic here since that belongs to quests.py
            if "streak" in expected:
                assert streak == expected["streak"], f"Vector {vector['id']} failed: streak was {streak}, expected {expected['streak']}"
            if "event" in expected:
                assert event == expected["event"], f"Vector {vector['id']} failed: event was {event}, expected {expected['event']}"
