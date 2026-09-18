import uuid
import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Character(Base):
    __tablename__ = "characters"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    class_name: Mapped[str] = mapped_column(String)
    tagline: Mapped[str] = mapped_column(String)
    origin_blurb: Mapped[str] = mapped_column(String)
    generated_by: Mapped[str] = mapped_column(String) # ai/fallback
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
