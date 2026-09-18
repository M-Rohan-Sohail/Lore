import uuid
import datetime
from sqlalchemy import String, Integer, JSON, DateTime, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Recap(Base):
    __tablename__ = "recaps"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String) # user/party
    owner_id: Mapped[uuid.UUID] = mapped_column() # user_id or party_id
    week_start: Mapped[datetime.date] = mapped_column(Date)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True) # RecapV1
    provider: Mapped[str] = mapped_column(String)
    degraded_level: Mapped[str] = mapped_column(String)
    episode_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    
    # Additions
    regen_count: Mapped[int] = mapped_column(Integer, default=0)
    
    __table_args__ = (
        UniqueConstraint("scope", "owner_id", "week_start", name="uix_recap_scope_owner_week"),
    )

class RecapJob(Base):
    __tablename__ = "recap_jobs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String)
    owner_id: Mapped[uuid.UUID] = mapped_column()
    week_start: Mapped[datetime.date] = mapped_column(Date)
    run_after: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    claimed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

class ShareToken(Base):
    __tablename__ = "share_tokens"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String) # ArtifactKind
    artifact_id: Mapped[uuid.UUID] = mapped_column()
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    created_by: Mapped[uuid.UUID] = mapped_column()
    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    
    # Additions
    card_kind: Mapped[str | None] = mapped_column(String, nullable=True)
