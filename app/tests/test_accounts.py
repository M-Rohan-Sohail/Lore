import pytest
import uuid
import datetime
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.accounts import OnboardingRequest
from app.services.accounts import complete_onboarding
from app.db.models.accounts import Profile

@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)

@pytest.mark.asyncio
@patch("app.services.accounts.track_event")
async def test_onboarding_age_gate(mock_track, mock_db):
    user_id = uuid.uuid4()
    
    # Test blocked (under 13)
    today = datetime.datetime.now(datetime.timezone.utc).date()
    birth_year = today.year - 10
    req_blocked = OnboardingRequest(birth_ym=f"{birth_year}-01", tz="America/New_York", consent=True)
    
    blocked = await complete_onboarding(mock_db, user_id, req_blocked)
    assert blocked is True
    
    # Verify execute was called with correct values
    mock_db.execute.assert_called()
    mock_db.commit.assert_called()
    mock_track.assert_called_with(user_id, "onboarding_completed", {"age_gate_blocked": True, "tz": "America/New_York"})
    
    # Test passed (over 13)
    birth_year2 = today.year - 20
    req_pass = OnboardingRequest(birth_ym=f"{birth_year2}-01", tz="Europe/London", consent=True)
    
    blocked2 = await complete_onboarding(mock_db, user_id, req_pass)
    assert blocked2 is False
