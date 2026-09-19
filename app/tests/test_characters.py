import pytest
import uuid
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.characters import QuizSubmission
from app.services.characters import process_quiz, evaluate_quiz
from app.db.models.accounts import Profile

def test_quiz_normalization_exhaustive():
    # Exhaustive test of all 78,125 possible quiz combinations
    # to ensure the normalization logic ALWAYS produces exactly sum=15
    # and all stats are between 1 and 5.
    # Note: running 78k Python function calls might take a fraction of a second.
    import itertools
    
    options = [0, 1, 2, 3, 4]
    combinations = itertools.product(options, repeat=7)
    
    count = 0
    for combo in combinations:
        stats = evaluate_quiz(list(combo))
        total = sum(stats.values())
        assert total == 15, f"Combo {combo} produced sum {total} instead of 15. Stats: {stats}"
        for s, v in stats.items():
            assert 1 <= v <= 5, f"Combo {combo} produced out-of-bounds stat {s}={v}"
        count += 1
    
    assert count == 78125

@pytest.mark.asyncio
@patch("app.services.characters.track_event")
@patch("app.services.characters.narrate")
async def test_process_quiz_fallback(mock_narrate, mock_track):
    mock_db = AsyncMock(spec=AsyncSession)
    user_id = uuid.uuid4()
    
    # Mock profile fetch
    profile = Profile(id=user_id, ai_personalization=False)
    mock_db.get.return_value = profile
    
    submission = QuizSubmission(answers=[0, 0, 0, 0, 0, 0, 0])
    
    char = await process_quiz(mock_db, user_id, submission)
    
    # Check fallback values (since ai_personalization=False)
    assert char.class_name is not None
    assert char.class_tagline is not None
    assert char.origin_blurb is not None
    assert sum(char.base_stats.values()) == 15
    
    mock_db.execute.assert_called()
    mock_db.commit.assert_called()
    mock_track.assert_called_with(user_id, "quiz_completed", {"class_name": char.class_name})
    mock_narrate.assert_not_called()
