"""
FastAPI dashboard API - CRUD for campaigns, actions, targets, and progress tracking.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import os

from platform.campaigns.models import (
    Campaign,
    Action,
    Target,
    Participant,
    CampaignStatus,
    CampaignType,
    ActionType,
    ActionStatus,
    TargetType,
    get_engine,
    get_session,
    create_tables,
)
from platform.campaigns.campaign_builder import CampaignBuilder
from platform.campaigns.action_generator import ActionGenerator
from platform.metrics.impact_tracker import ImpactTracker
from platform.metrics.roi_calculator import ROICalculator

app = FastAPI(
    title="Campaign Coordination Platform",
    description="Coordinate campaigns. Multiply impact. Every volunteer gets the right action at the right time.",
    version="0.1.0",
)

# --- Database dependency ---

_engine = None


def get_db() -> Session:
    global _engine
    if _engine is None:
        _engine = create_tables()
    session = get_session(_engine)
    try:
        yield session
    finally:
        session.close()


# --- Pydantic Schemas ---


class CampaignCreate(BaseModel):
    name: str
    campaign_type: CampaignType
    target_summary: str
    goal: str
    start_date: Optional[date] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[CampaignStatus] = None
    goal: Optional[str] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    slug: str
    campaign_type: str
    target_summary: str
    goal: str
    status: str
    channels: Optional[list] = None
    tactics: Optional[list] = None
    escalation_ladder: Optional[list] = None
    win_conditions: Optional[list] = None
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    completion_pct: float
    created_at: datetime

    class Config:
        from_attributes = True


class ActionCreate(BaseModel):
    campaign_id: int
    action_type: ActionType
    title: str
    description: str
    template_name: Optional[str] = None
    estimated_minutes: int = 15
    priority: int = 5
    deadline: Optional[datetime] = None


class ActionResponse(BaseModel):
    id: int
    campaign_id: int
    action_type: str
    title: str
    description: str
    template_name: Optional[str] = None
    estimated_minutes: int
    priority: int
    status: str
    deadline: Optional[datetime] = None
    assigned_to: Optional[int] = None
    completed_at: Optional[datetime] = None
    is_overdue: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TargetCreate(BaseModel):
    campaign_id: int
    name: str
    target_type: TargetType
    organization: Optional[str] = None
    title_role: Optional[str] = None
    contacts: Optional[dict] = None
    social_accounts: Optional[dict] = None
    vulnerability_score: float = 5.0
    vulnerability_factors: Optional[dict] = None
    notes: Optional[str] = None


class TargetResponse(BaseModel):
    id: int
    campaign_id: int
    name: str
    target_type: str
    organization: Optional[str] = None
    title_role: Optional[str] = None
    contacts: Optional[dict] = None
    social_accounts: Optional[dict] = None
    vulnerability_score: float
    vulnerability_factors: Optional[dict] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ParticipantCreate(BaseModel):
    name: str
    email: str
    skills: Optional[list] = None
    availability_minutes_per_week: int = 60


class ParticipantResponse(BaseModel):
    id: int
    name: str
    email: str
    skills: Optional[list] = None
    availability_minutes_per_week: int
    actions_completed: int
    actions_verified: int
    total_impact_score: float
    reliability_score: float

    class Config:
        from_attributes = True


class ActionSuggestionRequest(BaseModel):
    campaign_id: int
    minutes_available: int
    participant_id: Optional[int] = None


class ProgressResponse(BaseModel):
    campaign_id: int
    campaign_name: str
    total_actions: int
    completed_actions: int
    verified_actions: int
    overdue_actions: int
    completion_pct: float
    participants_active: int
    current_phase: Optional[int] = None


# --- Campaign Endpoints ---


@app.get("/")
async def root():
    """Serve the dashboard frontend."""
    frontend_path = os.path.join(
        os.path.dirname(__file__), "frontend.html"
    )
    return FileResponse(frontend_path, media_type="text/html")


@app.post("/api/campaigns", response_model=CampaignResponse)
async def create_campaign(data: CampaignCreate, db: Session = Depends(get_db)):
    """Create a new campaign from a template."""
    campaign = CampaignBuilder.build_campaign(
        name=data.name,
        campaign_type=data.campaign_type,
        target_summary=data.target_summary,
        goal=data.goal,
        start_date=data.start_date,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@app.get("/api/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(
    status: Optional[CampaignStatus] = None,
    campaign_type: Optional[CampaignType] = None,
    db: Session = Depends(get_db),
):
    """List all campaigns, optionally filtered by status or type."""
    query = db.query(Campaign)
    if status:
        query = query.filter(Campaign.status == status)
    if campaign_type:
        query = query.filter(Campaign.campaign_type == campaign_type)
    campaigns = query.order_by(Campaign.created_at.desc()).all()
    return campaigns


@app.get("/api/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Get a specific campaign by ID."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@app.patch("/api/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int, data: CampaignUpdate, db: Session = Depends(get_db)
):
    """Update a campaign's status, name, or goal."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if data.name is not None:
        campaign.name = data.name
    if data.status is not None:
        campaign.status = data.status
    if data.goal is not None:
        campaign.goal = data.goal
    db.commit()
    db.refresh(campaign)
    return campaign


@app.get("/api/campaigns/{campaign_id}/progress", response_model=ProgressResponse)
async def get_campaign_progress(campaign_id: int, db: Session = Depends(get_db)):
    """Get progress metrics for a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    actions = db.query(Action).filter(Action.campaign_id == campaign_id).all()
    completed = [a for a in actions if a.status in (ActionStatus.COMPLETED, ActionStatus.VERIFIED)]
    verified = [a for a in actions if a.status == ActionStatus.VERIFIED]
    overdue = [a for a in actions if a.is_overdue]
    assigned_participants = set(a.assigned_to for a in actions if a.assigned_to)

    return ProgressResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        total_actions=len(actions),
        completed_actions=len(completed),
        verified_actions=len(verified),
        overdue_actions=len(overdue),
        completion_pct=campaign.completion_pct,
        participants_active=len(assigned_participants),
    )


# --- Action Endpoints ---


@app.post("/api/actions", response_model=ActionResponse)
async def create_action(data: ActionCreate, db: Session = Depends(get_db)):
    """Create a new action for a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == data.campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    action = Action(
        campaign_id=data.campaign_id,
        action_type=data.action_type,
        title=data.title,
        description=data.description,
        template_name=data.template_name,
        estimated_minutes=data.estimated_minutes,
        priority=data.priority,
        deadline=data.deadline,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


@app.get("/api/actions", response_model=List[ActionResponse])
async def list_actions(
    campaign_id: Optional[int] = None,
    status: Optional[ActionStatus] = None,
    action_type: Optional[ActionType] = None,
    max_minutes: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List actions with optional filters."""
    query = db.query(Action)
    if campaign_id:
        query = query.filter(Action.campaign_id == campaign_id)
    if status:
        query = query.filter(Action.status == status)
    if action_type:
        query = query.filter(Action.action_type == action_type)
    if max_minutes:
        query = query.filter(Action.estimated_minutes <= max_minutes)
    return query.order_by(Action.priority.asc()).all()


@app.post("/api/actions/{action_id}/claim")
async def claim_action(
    action_id: int, participant_id: int, db: Session = Depends(get_db)
):
    """Claim an action for a participant."""
    action = db.query(Action).filter(Action.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != ActionStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="Action not available")
    participant = db.query(Participant).filter(Participant.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    action.status = ActionStatus.CLAIMED
    action.assigned_to = participant_id
    db.commit()
    return {"status": "claimed", "action_id": action_id, "participant_id": participant_id}


@app.post("/api/actions/{action_id}/complete")
async def complete_action(
    action_id: int,
    verification_url: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Mark an action as completed."""
    action = db.query(Action).filter(Action.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    action.status = ActionStatus.COMPLETED
    action.completed_at = datetime.utcnow()
    if verification_url:
        action.verification_url = verification_url
    if action.assigned_to:
        participant = db.query(Participant).filter(
            Participant.id == action.assigned_to
        ).first()
        if participant:
            participant.actions_completed += 1
            participant.last_active = datetime.utcnow()
    db.commit()
    return {"status": "completed", "action_id": action_id}


@app.post("/api/actions/{action_id}/verify")
async def verify_action(action_id: int, db: Session = Depends(get_db)):
    """Verify a completed action."""
    action = db.query(Action).filter(Action.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != ActionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Action must be completed first")
    action.status = ActionStatus.VERIFIED
    if action.assigned_to:
        participant = db.query(Participant).filter(
            Participant.id == action.assigned_to
        ).first()
        if participant:
            participant.actions_verified += 1
    db.commit()
    return {"status": "verified", "action_id": action_id}


@app.post("/api/actions/suggest", response_model=List[dict])
async def suggest_actions(data: ActionSuggestionRequest, db: Session = Depends(get_db)):
    """Suggest actions for a volunteer based on available time."""
    campaign = db.query(Campaign).filter(Campaign.id == data.campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    participant = None
    if data.participant_id:
        participant = db.query(Participant).filter(
            Participant.id == data.participant_id
        ).first()

    targets = db.query(Target).filter(Target.campaign_id == data.campaign_id).all()

    specs = ActionGenerator.generate_for_time(
        campaign=campaign,
        minutes_available=data.minutes_available,
        targets=targets,
        participant=participant,
    )

    return [
        {
            "action_type": s.action_type.value,
            "title": s.title,
            "description": s.description,
            "estimated_minutes": s.estimated_minutes,
            "priority": s.priority,
            "template_name": s.template_name,
        }
        for s in specs
    ]


# --- Target Endpoints ---


@app.post("/api/targets", response_model=TargetResponse)
async def create_target(data: TargetCreate, db: Session = Depends(get_db)):
    """Add a target to a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == data.campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    target = Target(**data.model_dump())
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@app.get("/api/targets", response_model=List[TargetResponse])
async def list_targets(
    campaign_id: Optional[int] = None,
    target_type: Optional[TargetType] = None,
    db: Session = Depends(get_db),
):
    """List targets, optionally filtered."""
    query = db.query(Target)
    if campaign_id:
        query = query.filter(Target.campaign_id == campaign_id)
    if target_type:
        query = query.filter(Target.target_type == target_type)
    return query.all()


# --- Participant Endpoints ---


@app.post("/api/participants", response_model=ParticipantResponse)
async def create_participant(data: ParticipantCreate, db: Session = Depends(get_db)):
    """Register a new participant."""
    existing = db.query(Participant).filter(Participant.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    participant = Participant(**data.model_dump())
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


@app.get("/api/participants", response_model=List[ParticipantResponse])
async def list_participants(db: Session = Depends(get_db)):
    """List all participants."""
    return db.query(Participant).order_by(Participant.actions_completed.desc()).all()


@app.get("/api/participants/{participant_id}", response_model=ParticipantResponse)
async def get_participant(participant_id: int, db: Session = Depends(get_db)):
    """Get a specific participant."""
    participant = db.query(Participant).filter(Participant.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    return participant


# --- Campaign Templates Info ---


@app.get("/api/templates/campaign-types")
async def list_campaign_types():
    """List available campaign types and their structures."""
    return CampaignBuilder.list_campaign_types()


# --- Metrics Endpoints ---


@app.get("/api/metrics/{campaign_id}")
async def get_campaign_metrics(campaign_id: int, db: Session = Depends(get_db)):
    """Get impact metrics for a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    actions = db.query(Action).filter(Action.campaign_id == campaign_id).all()
    tracker = ImpactTracker()
    return tracker.compute_campaign_metrics(campaign, actions)


@app.get("/api/metrics/{campaign_id}/roi")
async def get_campaign_roi(campaign_id: int, db: Session = Depends(get_db)):
    """Get ROI analysis for a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    actions = db.query(Action).filter(Action.campaign_id == campaign_id).all()
    calculator = ROICalculator()
    return calculator.calculate_campaign_roi(campaign, actions)
