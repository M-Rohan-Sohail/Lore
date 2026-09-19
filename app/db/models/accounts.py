import uuid
import datetime
from sqlalchemy import String, Integer, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, generate_short_code

class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    birth_ym: Mapped[str | None] = mapped_column(String, nullable=True)
    tz: Mapped[str] = mapped_column(String, default="UTC")
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp_total: Mapped[int] = mapped_column(Integer, default=0)
    base_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stat_counts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    streak_current: Mapped[int] = mapped_column(Integer, default=0)
    last_streak_date: Mapped[datetime.date | None] = mapped_column(nullable=True)
    last_freeze_used_date: Mapped[datetime.date | None] = mapped_column(nullable=True)
    ai_personalization: Mapped[bool] = mapped_column(Boolean, default=True)
    referral_code: Mapped[str] = mapped_column(String, default=generate_short_code)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))
    
    # Additions from checkpoints
    age_gate_blocked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_shown_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quiz_progress: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    founding_player: Mapped[bool] = mapped_column(Boolean, default=False)
    founding_player_checked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_invite_nudge_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Referral(Base):
    __tablename__ = "referrals"
    referrer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    referee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    device_token: Mapped[str] = mapped_column(String, unique=True)
    platform: Mapped[str] = mapped_column(String)
    last_success_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

class NotificationPref(Base):
    __tablename__ = "notification_prefs"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    recap_push: Mapped[bool] = mapped_column(Boolean, default=True)
    recap_email: Mapped[bool] = mapped_column(Boolean, default=True)
    streak_reminder: Mapped[bool] = mapped_column(Boolean, default=True)
    party_events: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))

class Entitlement(Base):
    __tablename__ = "entitlements"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), unique=True)
    plan: Mapped[str] = mapped_column(String) # free/plus
    status: Mapped[str] = mapped_column(String) # inactive/active/past_due
    current_period_end: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))
    
    # Additions
    provider_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String, nullable=True)
    past_due_since: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AuthSession(Base):
    """
    CP-3 addition: tracks Supabase sessions directly instead of relying on the Admin API.
    """
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class DeletedAccount(Base):
    __tablename__ = "deleted_accounts"
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    deleted_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
