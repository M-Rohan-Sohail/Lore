import uuid
import datetime
from sqlalchemy import String, Integer, Boolean, JSON, DateTime, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY # left for backward compat if needed
from app.db.base import Base

class Quest(Base):
    __tablename__ = "quests"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String) # main/side/party
    title: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    difficulty: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String) # ai/template
    status: Mapped[str] = mapped_column(String)
    due_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))
    
    # Additions
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("quests.id", ondelete="CASCADE"), nullable=True)

class QuestLog(Base):
    __tablename__ = "quest_logs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    quest_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quests.id", ondelete="CASCADE"))
    completed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    tz_at_log: Mapped[str] = mapped_column(String)
    local_date: Mapped[datetime.date] = mapped_column(Date)
    note_text: Mapped[str | None] = mapped_column(String, nullable=True)
    xp_awarded: Mapped[int] = mapped_column(Integer)
    counted_for_xp: Mapped[bool] = mapped_column(Boolean)
    client_key: Mapped[str] = mapped_column(String)
    
    # Additions
    excluded_from_recap: Mapped[bool] = mapped_column(Boolean, default=False)
    
    __table_args__ = (
        UniqueConstraint("user_id", "client_key", name="uix_user_client_key"),
    )

class StreakEvent(Base):
    __tablename__ = "streak_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    local_date: Mapped[datetime.date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String) # earned/freeze_used/broken
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

class QuestTemplate(Base):
    __tablename__ = "quest_templates"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String)
    difficulty: Mapped[str] = mapped_column(String)
    class_affinity: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    title_tpl: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

class NarratorLine(Base):
    __tablename__ = "narrator_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    class_name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    outcome: Mapped[str] = mapped_column(String)
    line: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
