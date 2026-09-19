import json
from app.db.seed.fallback_classes import FALLBACK_CLASSES

QUIZ_SCORING = [
    [{"cha": 2}, {"cha": 1, "int": 1}, {"int": 2}, {"vit": 2}, {"lck": 2}], # Q1
    [{"grit": 2}, {"cha": 1, "lck": 1}, {"int": 1, "lck": 1}, {"cha": 2}, {"lck": 1, "vit": 1}], # Q2
    [{"vit": 2}, {"int": 1, "grit": 1}, {"cha": 1, "int": 1}, {"grit": 2}, {"lck": 2}], # Q3
    [{"cha": 2}, {"int": 1, "lck": 1}, {"grit": 2}, {"vit": 2}, {"lck": 2}], # Q4
    [{"vit": 1, "lck": 1}, {"int": 2}, {"cha": 2}, {"vit": 1, "grit": 1}, {"lck": 2}], # Q5
    [{"grit": 1}, {"cha": 1}, {"int": 1}, {"grit": 1}, {"lck": 1}], # Q6
    [{"int": 2}, {"lck": 2}, {"grit": 2}, {"vit": 2}, {"cha": 2}], # Q7
]

def evaluate_quiz(answers: list[int]) -> dict[str, int]:
    stats = {"vit": 1, "int": 1, "cha": 1, "grit": 1, "lck": 1}
    
    for q_idx, a_idx in enumerate(answers):
        if a_idx < 0 or a_idx >= len(QUIZ_SCORING[q_idx]):
            a_idx = 0 # default fallback
        points = QUIZ_SCORING[q_idx][a_idx]
        for stat, val in points.items():
            stats[stat] += val
            
    # Cap at 5
    for stat in stats:
        if stats[stat] > 5:
            stats[stat] = 5
            
    # Normalize to 15
    while sum(stats.values()) < 15:
        # add to lowest
        lowest_stat = min([s for s in stats if stats[s] < 5], key=lambda x: (stats[x], x))
        stats[lowest_stat] += 1
        
    while sum(stats.values()) > 15:
        # subtract from highest
        highest_stat = max([s for s in stats if stats[s] > 1], key=lambda x: (stats[x], x))
        stats[highest_stat] -= 1
        
    return stats

def get_fallback_class(stats: dict[str, int]) -> dict:
    sorted_stats = sorted(stats.items(), key=lambda x: (-x[1], x[0]))
    dominant = sorted_stats[0][0].upper()
    secondary = sorted_stats[1][0].upper()
    
    # Check for ties
    if sorted_stats[0][1] == sorted_stats[1][1]:
        if sorted_stats[0][1] == sorted_stats[2][1] == sorted_stats[3][1] == sorted_stats[4][1]:
            key = "tie_all"
        else:
            key = f"tie_{dominant}"
    else:
        key = f"{dominant}/{secondary}"
        
    return FALLBACK_CLASSES.get(key, FALLBACK_CLASSES["tie_all"])

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
import uuid
from app.db.models.accounts import Profile
from app.schemas.characters import QuizSubmission, CharacterResponse
from app.ai.gateway import narrate
from app.schemas.ai import AIRequest
from app.core.analytics import track_event

async def process_quiz(db: AsyncSession, user_id: uuid.UUID, submission: QuizSubmission) -> CharacterResponse:
    stats = evaluate_quiz(submission.answers)
    
    # Check if AI personalization is enabled for user (could query DB, but we just pass it generally or fetch)
    profile = await db.get(Profile, user_id)
    if not profile:
        raise ValueError("Profile not found")
        
    fallback = get_fallback_class(stats)
    char_data = {
        "class_name": fallback["name"],
        "class_tagline": fallback["tagline"],
        "origin_blurb": fallback["blurb"],
        "base_stats": stats
    }
    
    if profile.ai_personalization:
        try:
            prompt = (
                "You are the LORE system. Generate a CharacterV1 JSON response based on these stats: "
                f"{json.dumps(stats)}. Base it roughly on the archetype: {fallback['name']}. "
                "Output ONLY valid JSON matching this schema: "
                '{"class_name": "str", "class_tagline": "str", "origin_blurb": "str <60 words", "base_stats": { "vit": int, "int": int, "cha": int, "grit": int, "lck": int }}'
                "\nDo not use existing IP."
            )
            
            ai_req = AIRequest(
                user_id=user_id,
                system_prompt="You are an RPG character generator. Return ONLY JSON.",
                user_prompt=prompt,
                budget_class="onboarding"
            )
            ai_res = await narrate(ai_req, db)
            
            # The gateway validates output structurally, but we should parse JSON
            parsed = json.loads(ai_res.content)
            # Ensure it matches schema and sums to 15
            parsed_stats = parsed.get("base_stats", {})
            if sum(parsed_stats.values()) == 15 and all(1 <= v <= 5 for v in parsed_stats.values()):
                char_data = parsed
        except Exception as e:
            # Silent fallback
            pass
            
    # Update DB
    stmt = update(Profile).where(Profile.id == user_id).values(
        base_stats=char_data["base_stats"],
        quiz_progress={
            "answers": submission.answers,
            "class_name": char_data["class_name"],
            "class_tagline": char_data.get("class_tagline", ""),
            "origin_blurb": char_data.get("origin_blurb", "")
        }
    )
    await db.execute(stmt)
    await db.commit()
    
    await track_event(user_id, "quiz_completed", {"class_name": char_data["class_name"]})
    
    return CharacterResponse(**char_data)

