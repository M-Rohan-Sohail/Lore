import uuid
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, delete
from app.db.models.party import Party, PartyMember
from app.core.errors import AppException

async def create_party(db: AsyncSession, user_id: uuid.UUID, name: str) -> Party:
    # Check if user already in a party
    stmt = select(PartyMember).join(Party, PartyMember.party_id == Party.id).where(
        PartyMember.user_id == user_id,
        Party.archived_at.is_(None)
    )
    if (await db.scalar(stmt)) is not None:
        raise AppException(code="E_ALREADY_IN_PARTY", message="You are already in a party")
        
    party = Party(name=name, lead_id=user_id, member_count=1)
    db.add(party)
    await db.flush()
    
    member = PartyMember(party_id=party.id, user_id=user_id, role="lead")
    db.add(member)
    await db.commit()
    await db.refresh(party)
    
    return party

async def join_party(db: AsyncSession, user_id: uuid.UUID, invite_code: str) -> Party:
    # Lock party row to prevent concurrent joins exceeding cap
    stmt = select(Party).where(Party.invite_code == invite_code, Party.archived_at.is_(None)).with_for_update()
    party = await db.scalar(stmt)
    
    if not party:
        raise AppException(code="E_NOT_FOUND", message="Party not found or archived")
        
    if party.member_count >= 3:
        raise AppException(code="E_PARTY_FULL", message="Party is full (max 3)")
        
    # Check if already in this or another party
    mem_stmt = select(PartyMember).join(Party, PartyMember.party_id == Party.id).where(
        PartyMember.user_id == user_id,
        Party.archived_at.is_(None)
    )
    if (await db.scalar(mem_stmt)) is not None:
        raise AppException(code="E_ALREADY_IN_PARTY", message="You are already in a party")
        
    party.member_count += 1
    
    member = PartyMember(party_id=party.id, user_id=user_id, role="member")
    db.add(member)
    await db.commit()
    await db.refresh(party)
    
    return party

async def _transfer_lead_or_archive(db: AsyncSession, party: Party):
    stmt = select(PartyMember).where(PartyMember.party_id == party.id).order_by(PartyMember.joined_at.asc())
    result = await db.execute(stmt)
    members = result.scalars().all()
    
    if not members:
        # Archive
        party.archived_at = datetime.datetime.now(datetime.timezone.utc)
        party.lead_id = None
    else:
        # Longest-tenured member gets lead
        new_lead = members[0]
        new_lead.role = "lead"
        party.lead_id = new_lead.user_id
        
async def leave_party(db: AsyncSession, user_id: uuid.UUID) -> None:
    # Find active party
    stmt = select(PartyMember).join(Party, PartyMember.party_id == Party.id).where(
        PartyMember.user_id == user_id,
        Party.archived_at.is_(None)
    )
    member = await db.scalar(stmt)
    if not member:
        raise AppException(code="E_NOT_IN_PARTY", message="You are not in a party")
        
    party_stmt = select(Party).where(Party.id == member.party_id).with_for_update()
    party = await db.scalar(party_stmt)
    
    if not party:
        raise AppException(code="E_NOT_FOUND", message="Party not found")
        
    await db.delete(member)
    party.member_count -= 1
    
    if party.lead_id == user_id:
        await _transfer_lead_or_archive(db, party)
    elif party.member_count == 0: # Shouldn't happen if they weren't lead, but defensive
        party.archived_at = datetime.datetime.now(datetime.timezone.utc)
        
    await db.commit()
