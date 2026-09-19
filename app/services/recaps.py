import uuid
import datetime
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.db.models.recaps import Recap
from app.db.models.quests import QuestLog, Quest
from app.db.models.party import PartyMember
from app.db.models.accounts import Profile
from app.ai.gateway import narrate
from app.schemas.ai import AIRequest

def get_stat_deltas(quest_logs: list) -> dict:
    deltas = {"vit": 0, "int": 0, "cha": 0, "grit": 0, "lck": 0}
    # In a real impl, we'd join with Quest or QuestTemplate to get category
    # For now, we mock the logic or expect the queries to join quests
    for category in deltas:
        deltas[category] = sum(1 for ql in quest_logs if ql[1] == category)
    return deltas

async def calculate_deltas(db: AsyncSession, user_id: uuid.UUID, week_start: datetime.date):
    week_end = week_start + datetime.timedelta(days=7)
    
    # We join QuestLog and Quest to get the category
    stmt = (
        select(QuestLog, Quest.category)
        .join(Quest, QuestLog.quest_id == Quest.id)
        .where(
            QuestLog.user_id == user_id,
            QuestLog.local_date >= week_start,
            QuestLog.local_date < week_end,
            QuestLog.excluded_from_recap == False
        )
    )
    result = await db.execute(stmt)
    logs = result.all()
    
    return get_stat_deltas(logs)

async def _get_next_episode_number(db: AsyncSession, scope: str, owner_id: uuid.UUID) -> int:
    stmt = select(func.max(Recap.episode_number)).where(
        Recap.scope == scope,
        Recap.owner_id == owner_id
    )
    max_ep = await db.scalar(stmt)
    return (max_ep or 0) + 1

async def generate_user_recap(db: AsyncSession, user_id: uuid.UUID, week_start: datetime.date, force_regen: bool = False):
    # Check existing
    stmt = select(Recap).where(
        Recap.scope == "user",
        Recap.owner_id == user_id,
        Recap.week_start == week_start
    )
    existing = await db.scalar(stmt)
    
    if existing and not force_regen:
        return existing
        
    deltas = await calculate_deltas(db, user_id, week_start)
    total_quests = sum(deltas.values())
    
    is_quiet = total_quests == 0
    
    if is_quiet:
        episode_number = None
        # Quiet week template
        payload = {
            "title": "A Quiet Week",
            "body_text": "You took a well-deserved rest. The realm awaits your return.",
            "stat_deltas": deltas,
            "episode_number": None
        }
        provider = "template"
        degraded = "none"
    else:
        episode_number = existing.episode_number if existing and existing.episode_number else await _get_next_episode_number(db, "user", user_id)
        
        # We try AI generation
        payload = None
        provider = "gateway"
        degraded = "none"
        
        prompt = (
            f"Generate a weekly recap for a hero. They completed quests giving these stats: {deltas}. "
            f"Output JSON matching: {{\"title\": \"str\", \"body_text\": \"str\"}}"
        )
        
        try:
            req = AIRequest(
                user_id=user_id,
                system_prompt="You are an RPG narrator. Return ONLY JSON.",
                user_prompt=prompt,
                budget_class="recap"
            )
            res = await narrate(req, db)
            ai_data = json.loads(res.content)
            
            payload = {
                "title": ai_data.get("title", f"Episode {episode_number}"),
                "body_text": ai_data.get("body_text", "You went on many adventures."),
                "stat_deltas": deltas,
                "episode_number": episode_number
            }
        except Exception:
            # Fallback to template
            provider = "template"
            degraded = "template"
            payload = {
                "title": f"Episode {episode_number}: Steady Progress",
                "body_text": f"You completed {total_quests} quests this week. Your highest stat was {max(deltas, key=deltas.get).upper()}.",
                "stat_deltas": deltas,
                "episode_number": episode_number
            }
            
    if existing:
        existing.payload = payload
        existing.provider = provider
        existing.degraded_level = degraded
        existing.regen_count += 1
        return existing
    else:
        new_recap = Recap(
            scope="user",
            owner_id=user_id,
            week_start=week_start,
            payload=payload,
            provider=provider,
            degraded_level=degraded,
            episode_number=episode_number,
            regen_count=0
        )
        db.add(new_recap)
        return new_recap

async def generate_party_recap(db: AsyncSession, party_id: uuid.UUID, week_start: datetime.date, force_regen: bool = False):
    stmt = select(Recap).where(
        Recap.scope == "party",
        Recap.owner_id == party_id,
        Recap.week_start == week_start
    )
    existing = await db.scalar(stmt)
    if existing and not force_regen:
        return existing
        
    mem_stmt = select(PartyMember.user_id).where(PartyMember.party_id == party_id)
    members = (await db.execute(mem_stmt)).scalars().all()
    
    overall_deltas = {"vit": 0, "int": 0, "cha": 0, "grit": 0, "lck": 0}
    for m_id in members:
        user_deltas = await calculate_deltas(db, m_id, week_start)
        for k, v in user_deltas.items():
            overall_deltas[k] += v
            
    total_quests = sum(overall_deltas.values())
    is_quiet = total_quests == 0
    
    if is_quiet:
        episode_number = None
        payload = {
            "title": "A Quiet Week for the Squad",
            "body_text": "The party rested at the tavern.",
            "stat_deltas": overall_deltas,
            "episode_number": None
        }
        provider = "template"
        degraded = "none"
    else:
        episode_number = existing.episode_number if existing and existing.episode_number else await _get_next_episode_number(db, "party", party_id)
        provider = "gateway"
        degraded = "none"
        
        prompt = (
            f"Generate a weekly recap for a party. Combined stats: {overall_deltas}. "
            f"Make sure NOT to include any private user notes. Output JSON matching: {{\"title\": \"str\", \"body_text\": \"str\"}}"
        )
        
        try:
            req = AIRequest(
                user_id=party_id, # using party_id as caller
                system_prompt="You are an RPG narrator. Return ONLY JSON.",
                user_prompt=prompt,
                budget_class="recap"
            )
            res = await narrate(req, db)
            ai_data = json.loads(res.content)
            
            payload = {
                "title": ai_data.get("title", f"Party Episode {episode_number}"),
                "body_text": ai_data.get("body_text", "The party went on many adventures."),
                "stat_deltas": overall_deltas,
                "episode_number": episode_number
            }
        except Exception:
            provider = "template"
            degraded = "template"
            payload = {
                "title": f"Party Episode {episode_number}: Steady Progress",
                "body_text": f"The party completed {total_quests} quests this week.",
                "stat_deltas": overall_deltas,
                "episode_number": episode_number
            }
            
    if existing:
        existing.payload = payload
        existing.provider = provider
        existing.degraded_level = degraded
        existing.regen_count += 1
        return existing
    else:
        new_recap = Recap(
            scope="party",
            owner_id=party_id,
            week_start=week_start,
            payload=payload,
            provider=provider,
            degraded_level=degraded,
            episode_number=episode_number,
            regen_count=0
        )
        db.add(new_recap)
        return new_recap
