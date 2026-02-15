"""
SQLAlchemy models for campaigns, actions, targets, and participants.
"""

from datetime import datetime, date
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Enum,
    JSON,
    Table,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    Session,
    sessionmaker,
)


class Base(DeclarativeBase):
    pass


# --- Enums ---


class CampaignStatus(str, PyEnum):
    DRAFT = "draft"
    PLANNING = "planning"
    ACTIVE = "active"
    ESCALATING = "escalating"
    PAUSED = "paused"
    WON = "won"
    LOST = "lost"
    ARCHIVED = "archived"


class CampaignType(str, PyEnum):
    CORPORATE = "corporate"
    LEGISLATIVE = "legislative"
    REGULATORY = "regulatory"
    INVESTIGATION = "investigation"
    CULTURAL = "cultural"


class ActionType(str, PyEnum):
    EMAIL = "email"
    PHONE_CALL = "phone_call"
    SOCIAL_POST = "social_post"
    PUBLIC_COMMENT = "public_comment"
    FOIA_REQUEST = "foia_request"
    REVIEW = "review"
    TESTIMONY = "testimony"
    SHAREHOLDER_ACTION = "shareholder_action"
    BOYCOTT = "boycott"
    CONTENT_CREATION = "content_creation"
    SEO_ARTICLE = "seo_article"
    OSINT_RESEARCH = "osint_research"
    SATELLITE_ANALYSIS = "satellite_analysis"
    CITIZEN_SUIT = "citizen_suit"


class ActionStatus(str, PyEnum):
    AVAILABLE = "available"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    EXPIRED = "expired"


class TargetType(str, PyEnum):
    CORPORATION = "corporation"
    EXECUTIVE = "executive"
    LEGISLATOR = "legislator"
    REGULATOR = "regulator"
    FACILITY = "facility"
    BRAND = "brand"
    INVESTOR = "investor"


class TacticChannel(str, PyEnum):
    EMAIL = "email"
    PHONE = "phone"
    SOCIAL_MEDIA = "social_media"
    LEGAL = "legal"
    MEDIA = "media"
    SHAREHOLDER = "shareholder"
    CONSUMER = "consumer"
    REGULATORY = "regulatory"
    GRASSROOTS = "grassroots"


# --- Association Tables ---

campaign_channels = Table(
    "campaign_channels",
    Base.metadata,
    Column("campaign_id", Integer, ForeignKey("campaigns.id"), primary_key=True),
    Column("channel", String(50), primary_key=True),
)

campaign_tactics = Table(
    "campaign_tactics",
    Base.metadata,
    Column("campaign_id", Integer, ForeignKey("campaigns.id"), primary_key=True),
    Column("tactic", String(100), primary_key=True),
)

participant_actions = Table(
    "participant_actions",
    Base.metadata,
    Column("participant_id", Integer, ForeignKey("participants.id"), primary_key=True),
    Column("action_id", Integer, ForeignKey("actions.id"), primary_key=True),
    Column("completed_at", DateTime, nullable=True),
)

participant_skills = Table(
    "participant_skills",
    Base.metadata,
    Column("participant_id", Integer, ForeignKey("participants.id"), primary_key=True),
    Column("skill", String(100), primary_key=True),
)


# --- Models ---


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    campaign_type: Mapped[str] = mapped_column(
        Enum(CampaignType), nullable=False
    )
    target_summary: Mapped[str] = mapped_column(Text, nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.DRAFT
    )
    channels: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    tactics: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    escalation_ladder: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    win_conditions: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    actions: Mapped[List["Action"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    targets: Mapped[List["Target"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"

    @property
    def completion_pct(self) -> float:
        if not self.actions:
            return 0.0
        completed = sum(
            1 for a in self.actions if a.status in (ActionStatus.COMPLETED, ActionStatus.VERIFIED)
        )
        return round((completed / len(self.actions)) * 100, 1)


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(Enum(ActionType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    template_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    template_vars: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=15)
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1=highest, 10=lowest
    status: Mapped[str] = mapped_column(
        Enum(ActionStatus), default=ActionStatus.AVAILABLE
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    assigned_to: Mapped[Optional[int]] = mapped_column(
        ForeignKey("participants.id"), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verification_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    impact_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign: Mapped["Campaign"] = relationship(back_populates="actions")

    def __repr__(self):
        return f"<Action(id={self.id}, type='{self.action_type}', status='{self.status}')>"

    @property
    def is_overdue(self) -> bool:
        if self.deadline and self.status not in (ActionStatus.COMPLETED, ActionStatus.VERIFIED):
            return datetime.utcnow() > self.deadline
        return False


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[str] = mapped_column(Enum(TargetType), nullable=False)
    organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contacts: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # contacts schema: {"email": str, "phone": str, "address": str, "assistant": str}
    social_accounts: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # social_accounts schema: {"twitter": str, "linkedin": str, "instagram": str}
    vulnerability_score: Mapped[float] = mapped_column(Float, default=5.0)
    # 1-10 scale: brand sensitivity, ESG pressure, regulatory exposure, public scrutiny
    vulnerability_factors: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # factors schema: {"brand_sensitivity": float, "esg_pressure": float,
    #                   "regulatory_exposure": float, "public_scrutiny": float}
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign: Mapped["Campaign"] = relationship(back_populates="targets")

    def __repr__(self):
        return f"<Target(id={self.id}, name='{self.name}', type='{self.target_type}')>"


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    skills: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    # skills list: ["writing", "legal", "research", "social_media", "design",
    #               "video", "data_analysis", "phone_calls", "organizing"]
    availability_minutes_per_week: Mapped[int] = mapped_column(Integer, default=60)
    actions_completed: Mapped[int] = mapped_column(Integer, default=0)
    actions_verified: Mapped[int] = mapped_column(Integer, default=0)
    total_impact_score: Mapped[float] = mapped_column(Float, default=0.0)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    preferences: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # preferences schema: {"preferred_action_types": list, "max_minutes_per_action": int,
    #                       "notification_frequency": str}

    def __repr__(self):
        return (
            f"<Participant(id={self.id}, name='{self.name}', "
            f"completed={self.actions_completed})>"
        )

    @property
    def reliability_score(self) -> float:
        if not self.actions_completed:
            return 0.5  # neutral for new participants
        return min(1.0, self.actions_verified / max(1, self.actions_completed))


# --- Database Setup ---


def get_engine(database_url: str = "sqlite:///campaign_platform.db"):
    return create_engine(database_url, echo=False)


def create_tables(engine=None):
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session(engine=None) -> Session:
    if engine is None:
        engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
