"""
Tests for the Campaign Coordination Platform.
"""

import pytest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from campaign_platform.campaigns.models import (
    Base,
    Campaign,
    Action,
    Target,
    Participant,
    CampaignType,
    CampaignStatus,
    ActionType,
    ActionStatus,
    TargetType,
    create_tables,
)
from campaign_platform.campaigns.campaign_builder import CampaignBuilder
from campaign_platform.campaigns.action_generator import ActionGenerator, ActionSpec
from campaign_platform.metrics.impact_tracker import ImpactTracker
from campaign_platform.metrics.roi_calculator import ROICalculator
from campaign_platform.scheduler.action_scheduler import ActionScheduler, ScheduleWindow


# --- Fixtures ---


@pytest.fixture
def engine():
    """Create an in-memory SQLite database for testing."""
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db(engine) -> Session:
    """Create a test database session."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_campaign(db: Session) -> Campaign:
    """Create a sample corporate campaign."""
    campaign = CampaignBuilder.build_campaign(
        name="Test Corporate Campaign",
        campaign_type=CampaignType.CORPORATE,
        target_summary="TestCorp Inc.",
        goal="Commit to phasing out practice X by 2027 with independent verification",
        start_date=date.today(),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@pytest.fixture
def sample_target(db: Session, sample_campaign: Campaign) -> Target:
    """Create a sample target."""
    target = Target(
        campaign_id=sample_campaign.id,
        name="John Smith",
        target_type=TargetType.EXECUTIVE,
        organization="TestCorp Inc.",
        title_role="CEO",
        contacts={"email": "ceo@testcorp.com", "phone": "555-0100"},
        social_accounts={"twitter": "@testcorp"},
        vulnerability_score=7.5,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@pytest.fixture
def sample_participant(db: Session) -> Participant:
    """Create a sample participant."""
    participant = Participant(
        name="Jane Volunteer",
        email="jane@example.com",
        skills=["writing", "research", "social_media"],
        availability_minutes_per_week=120,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


@pytest.fixture
def sample_actions(db: Session, sample_campaign: Campaign) -> list:
    """Create sample actions across different types and statuses."""
    actions = [
        Action(
            campaign_id=sample_campaign.id,
            action_type=ActionType.EMAIL,
            title="Email CEO about practice X",
            description="Send personalized email to CEO",
            estimated_minutes=15,
            priority=2,
            status=ActionStatus.COMPLETED,
            completed_at=datetime.utcnow() - timedelta(days=3),
        ),
        Action(
            campaign_id=sample_campaign.id,
            action_type=ActionType.PHONE_CALL,
            title="Call investor relations",
            description="Call IR about ESG concerns",
            estimated_minutes=5,
            priority=2,
            status=ActionStatus.COMPLETED,
            completed_at=datetime.utcnow() - timedelta(days=2),
        ),
        Action(
            campaign_id=sample_campaign.id,
            action_type=ActionType.SOCIAL_POST,
            title="Post about TestCorp practices",
            description="Tweet thread about findings",
            estimated_minutes=10,
            priority=3,
            status=ActionStatus.VERIFIED,
            completed_at=datetime.utcnow() - timedelta(days=1),
        ),
        Action(
            campaign_id=sample_campaign.id,
            action_type=ActionType.PUBLIC_COMMENT,
            title="Comment on EPA rule",
            description="Submit substantive comment on proposed rule",
            estimated_minutes=30,
            priority=4,
            status=ActionStatus.AVAILABLE,
        ),
        Action(
            campaign_id=sample_campaign.id,
            action_type=ActionType.REVIEW,
            title="Post factual Google review",
            description="Review based on documented findings",
            estimated_minutes=15,
            priority=5,
            status=ActionStatus.AVAILABLE,
        ),
    ]
    for a in actions:
        db.add(a)
    db.commit()
    for a in actions:
        db.refresh(a)
    return actions


# --- Campaign Builder Tests ---


class TestCampaignBuilder:
    def test_build_corporate_campaign(self, db):
        campaign = CampaignBuilder.build_campaign(
            name="Smithfield Gestation Crates",
            campaign_type=CampaignType.CORPORATE,
            target_summary="Smithfield Foods",
            goal="Phase out gestation crates across all facilities by 2028",
        )
        assert campaign.name == "Smithfield Gestation Crates"
        assert campaign.campaign_type == CampaignType.CORPORATE
        assert campaign.status == CampaignStatus.DRAFT
        assert len(campaign.escalation_ladder) == 4
        assert len(campaign.channels) > 0
        assert campaign.start_date == date.today()
        assert campaign.deadline > date.today()

    def test_build_legislative_campaign(self, db):
        campaign = CampaignBuilder.build_campaign(
            name="Farm System Reform Act",
            campaign_type=CampaignType.LEGISLATIVE,
            target_summary="US Congress",
            goal="Pass the Farm System Reform Act",
        )
        assert campaign.campaign_type == CampaignType.LEGISLATIVE
        assert len(campaign.escalation_ladder) == 3

    def test_build_regulatory_campaign(self, db):
        campaign = CampaignBuilder.build_campaign(
            name="USDA Inspection Standards",
            campaign_type=CampaignType.REGULATORY,
            target_summary="USDA FSIS",
            goal="Strengthen line speed regulations",
        )
        assert campaign.campaign_type == CampaignType.REGULATORY
        assert "regulatory" in campaign.channels

    def test_build_investigation_campaign(self, db):
        campaign = CampaignBuilder.build_campaign(
            name="Tyson Water Pollution",
            campaign_type=CampaignType.INVESTIGATION,
            target_summary="Tyson Foods facilities in Arkansas",
            goal="Document Clean Water Act violations for citizen suit",
        )
        assert campaign.campaign_type == CampaignType.INVESTIGATION

    def test_build_cultural_campaign(self, db):
        campaign = CampaignBuilder.build_campaign(
            name="Factory Farm Search Results",
            campaign_type=CampaignType.CULTURAL,
            target_summary="Public narrative about factory farming",
            goal="Own first page of Google for 'factory farm conditions'",
        )
        assert campaign.campaign_type == CampaignType.CULTURAL
        assert "social_media" in campaign.channels

    def test_campaign_slug_generation(self, db):
        campaign = CampaignBuilder.build_campaign(
            name="Test Campaign's Name!",
            campaign_type=CampaignType.CORPORATE,
            target_summary="test",
            goal="test",
        )
        assert " " not in campaign.slug
        assert "'" not in campaign.slug
        assert "!" not in campaign.slug

    def test_deadline_calculated_from_phases(self, db):
        campaign = CampaignBuilder.build_campaign(
            name="Timeline Test",
            campaign_type=CampaignType.CORPORATE,
            target_summary="test",
            goal="test",
            start_date=date(2026, 1, 1),
        )
        template = CampaignBuilder.TEMPLATES[CampaignType.CORPORATE]
        total_weeks = sum(p["duration_weeks"] for p in template["escalation_ladder"])
        expected_deadline = date(2026, 1, 1) + timedelta(weeks=total_weeks)
        assert campaign.deadline == expected_deadline

    def test_list_campaign_types(self):
        types = CampaignBuilder.list_campaign_types()
        assert len(types) == 5
        for t in types:
            assert "type" in t
            assert "channels" in t
            assert "phases" in t
            assert "total_weeks" in t

    def test_generate_phase_actions(self, db, sample_campaign, sample_target):
        actions = CampaignBuilder.generate_phase_actions(
            campaign=sample_campaign,
            phase_number=1,
            targets=[sample_target],
        )
        assert len(actions) > 0
        for action in actions:
            assert action.campaign_id == sample_campaign.id
            assert "Phase 1" in action.title

    def test_generate_phase_actions_without_targets(self, db, sample_campaign):
        actions = CampaignBuilder.generate_phase_actions(
            campaign=sample_campaign,
            phase_number=1,
        )
        assert len(actions) > 0


# --- Action Generator Tests ---


class TestActionGenerator:
    def test_get_time_tier(self):
        assert ActionGenerator.get_time_tier(3) == "quick"
        assert ActionGenerator.get_time_tier(5) == "quick"
        assert ActionGenerator.get_time_tier(10) == "short"
        assert ActionGenerator.get_time_tier(15) == "short"
        assert ActionGenerator.get_time_tier(25) == "medium"
        assert ActionGenerator.get_time_tier(30) == "medium"
        assert ActionGenerator.get_time_tier(60) == "long"
        assert ActionGenerator.get_time_tier(120) == "long"

    def test_generate_5min_actions(self, sample_campaign):
        specs = ActionGenerator.generate_for_time(
            campaign=sample_campaign,
            minutes_available=5,
        )
        for spec in specs:
            assert spec.estimated_minutes <= 5

    def test_generate_15min_actions(self, sample_campaign):
        specs = ActionGenerator.generate_for_time(
            campaign=sample_campaign,
            minutes_available=15,
        )
        for spec in specs:
            assert spec.estimated_minutes <= 15

    def test_generate_30min_actions(self, sample_campaign):
        specs = ActionGenerator.generate_for_time(
            campaign=sample_campaign,
            minutes_available=30,
        )
        for spec in specs:
            assert spec.estimated_minutes <= 30

    def test_generate_2hr_actions(self, sample_campaign):
        specs = ActionGenerator.generate_for_time(
            campaign=sample_campaign,
            minutes_available=120,
        )
        assert len(specs) > 0

    def test_generate_with_targets(self, sample_campaign, sample_target):
        specs = ActionGenerator.generate_for_time(
            campaign=sample_campaign,
            minutes_available=30,
            targets=[sample_target],
        )
        # At least some specs should reference the target
        target_refs = [s for s in specs if "John Smith" in s.title or "TestCorp" in s.description]
        assert len(target_refs) > 0

    def test_generate_with_participant_skills(self, sample_campaign, sample_participant):
        specs = ActionGenerator.generate_for_time(
            campaign=sample_campaign,
            minutes_available=120,
            participant=sample_participant,
        )
        # Participant has writing, research, social_media skills
        for spec in specs:
            if spec.requires_skills:
                assert any(
                    s in sample_participant.skills for s in spec.requires_skills
                )

    def test_generate_action_from_spec(self, sample_campaign):
        spec = ActionSpec(
            action_type=ActionType.EMAIL,
            title="Test Email",
            description="Test description",
            estimated_minutes=15,
            priority=3,
        )
        action = ActionGenerator.generate_action_from_spec(spec, sample_campaign.id)
        assert action.campaign_id == sample_campaign.id
        assert action.action_type == ActionType.EMAIL
        assert action.title == "Test Email"

    def test_priority_calculation(self, sample_campaign, sample_target):
        # High vulnerability target should yield lower priority number (= higher priority)
        sample_target.vulnerability_score = 9.0
        specs = ActionGenerator.generate_for_time(
            campaign=sample_campaign,
            minutes_available=30,
            targets=[sample_target],
        )
        if specs:
            assert specs[0].priority <= 5  # Should be prioritized

    def test_max_actions_limit(self, sample_campaign):
        specs = ActionGenerator.generate_for_time(
            campaign=sample_campaign,
            minutes_available=120,
            max_actions=2,
        )
        assert len(specs) <= 2


# --- Model Tests ---


class TestModels:
    def test_campaign_completion_pct(self, sample_campaign, sample_actions):
        # 3 of 5 actions are completed/verified
        assert sample_campaign.completion_pct == 60.0

    def test_campaign_completion_pct_no_actions(self, db):
        campaign = CampaignBuilder.build_campaign(
            name="Empty",
            campaign_type=CampaignType.CORPORATE,
            target_summary="test",
            goal="test",
        )
        db.add(campaign)
        db.commit()
        assert campaign.completion_pct == 0.0

    def test_action_overdue(self, db, sample_campaign):
        overdue_action = Action(
            campaign_id=sample_campaign.id,
            action_type=ActionType.EMAIL,
            title="Overdue action",
            description="This should be overdue",
            deadline=datetime.utcnow() - timedelta(days=1),
            status=ActionStatus.AVAILABLE,
        )
        db.add(overdue_action)
        db.commit()
        assert overdue_action.is_overdue is True

    def test_action_not_overdue_when_completed(self, db, sample_campaign):
        action = Action(
            campaign_id=sample_campaign.id,
            action_type=ActionType.EMAIL,
            title="Completed on time",
            description="Done",
            deadline=datetime.utcnow() - timedelta(days=1),
            status=ActionStatus.COMPLETED,
        )
        db.add(action)
        db.commit()
        assert action.is_overdue is False

    def test_participant_reliability_score(self, db):
        p = Participant(
            name="Test",
            email="test@test.com",
            actions_completed=10,
            actions_verified=8,
        )
        assert p.reliability_score == 0.8

    def test_participant_reliability_new(self, db):
        p = Participant(name="New", email="new@test.com")
        assert p.reliability_score == 0.5  # neutral for new participants

    def test_target_vulnerability_score(self, sample_target):
        assert sample_target.vulnerability_score == 7.5


# --- Impact Tracker Tests ---


class TestImpactTracker:
    def test_compute_campaign_metrics(self, sample_campaign, sample_actions):
        tracker = ImpactTracker()
        metrics = tracker.compute_campaign_metrics(sample_campaign, sample_actions)

        assert metrics["campaign_id"] == sample_campaign.id
        assert metrics["summary"]["total_actions"] == 5
        assert metrics["summary"]["completed"] == 3  # 2 completed + 1 verified
        assert metrics["summary"]["verified"] == 1
        assert metrics["activity_counts"]["emails_sent"] == 1
        assert metrics["activity_counts"]["calls_made"] == 1
        assert metrics["activity_counts"]["social_posts"] == 1
        assert metrics["impact"]["total_impact_score"] > 0

    def test_empty_campaign_metrics(self, sample_campaign):
        tracker = ImpactTracker()
        metrics = tracker.compute_campaign_metrics(sample_campaign, [])
        assert metrics["summary"]["total_actions"] == 0
        assert metrics["summary"]["completion_rate"] == 0.0

    def test_channel_coverage(self, sample_campaign, sample_actions):
        tracker = ImpactTracker()
        metrics = tracker.compute_campaign_metrics(sample_campaign, sample_actions)
        assert len(metrics["channels"]["active"]) > 0
        assert metrics["channels"]["coverage_pct"] > 0

    def test_media_coverage_scoring(self):
        tracker = ImpactTracker()
        mentions = [
            {"outlet": "NYT", "tier": 1, "sentiment": "positive"},
            {"outlet": "Local Paper", "tier": 3, "sentiment": "neutral"},
            {"outlet": "Trade Journal", "tier": 4, "sentiment": "positive"},
        ]
        result = tracker.get_media_coverage_score(mentions)
        assert result["total_mentions"] == 3
        assert result["media_impact_score"] > 0
        assert result["by_tier"]["national"] == 1

    def test_corporate_response_tracking(self):
        tracker = ImpactTracker()
        responses = [
            {"date": "2026-01-01", "type": "no_response", "details": "No reply"},
            {"date": "2026-01-15", "type": "form_letter", "details": "Generic response"},
            {"date": "2026-02-01", "type": "meeting_offer", "details": "VP offered call"},
        ]
        result = tracker.track_corporate_response(responses)
        assert result["total_responses"] == 3
        assert result["trajectory"] == "improving"


# --- ROI Calculator Tests ---


class TestROICalculator:
    def test_calculate_campaign_roi(self, sample_campaign, sample_actions):
        calculator = ROICalculator()
        roi = calculator.calculate_campaign_roi(sample_campaign, sample_actions)

        assert roi["campaign_id"] == sample_campaign.id
        assert roi["investment"]["total_volunteer_hours"] > 0
        assert roi["returns"]["total_value"] > 0
        assert "roi_pct" in roi["efficiency"]
        assert "value_per_volunteer_hour" in roi["efficiency"]
        assert len(roi["recommendations"]) > 0

    def test_empty_campaign_roi(self, sample_campaign):
        calculator = ROICalculator()
        roi = calculator.calculate_campaign_roi(sample_campaign, [])
        assert roi["investment"]["total_volunteer_hours"] == 0.0

    def test_project_impact(self, sample_campaign, sample_actions):
        calculator = ROICalculator()
        projection = calculator.project_impact(
            campaign=sample_campaign,
            actions=sample_actions,
            additional_hours=10.0,
        )
        assert projection["additional_hours"] == 10.0
        assert projection["projected_additional_actions"] > 0
        assert projection["projected_additional_value"] > 0

    def test_project_impact_focused(self, sample_campaign, sample_actions):
        calculator = ROICalculator()
        projection = calculator.project_impact(
            campaign=sample_campaign,
            actions=sample_actions,
            additional_hours=10.0,
            focus_type=ActionType.PHONE_CALL,
        )
        assert projection["focus_type"] == "phone_call"
        assert projection["projected_additional_actions"] > 0


# --- Scheduler Tests ---


class TestActionScheduler:
    def test_schedule_email_campaign(self):
        scheduler = ActionScheduler()
        window = ScheduleWindow(
            start=datetime(2026, 3, 2, 9, 0),  # Monday
            end=datetime(2026, 3, 13, 17, 0),   # Friday
        )
        scheduled = scheduler.schedule_email_campaign(
            action_ids=list(range(1, 21)),
            window=window,
            emails_per_day=5,
        )
        assert len(scheduled) > 0
        # All scheduled during business hours
        for sa in scheduled:
            assert 6 <= sa.scheduled_start.hour <= 18
            assert sa.scheduled_start.weekday() < 5  # weekday

    def test_schedule_social_burst(self):
        scheduler = ActionScheduler()
        burst_time = datetime(2026, 3, 5, 19, 0)  # Thursday 7pm
        scheduled = scheduler.schedule_social_burst(
            action_ids=list(range(1, 11)),
            burst_time=burst_time,
        )
        assert len(scheduled) == 10
        # All within burst window
        for sa in scheduled:
            delta = abs((sa.scheduled_start - burst_time).total_seconds())
            assert delta < 900  # within 15 minutes

    def test_schedule_phone_bank(self):
        scheduler = ActionScheduler()
        window = ScheduleWindow(
            start=datetime(2026, 3, 2, 9, 0),
            end=datetime(2026, 3, 6, 17, 0),
        )
        scheduled = scheduler.schedule_phone_bank(
            action_ids=list(range(1, 11)),
            window=window,
        )
        assert len(scheduled) > 0
        for sa in scheduled:
            assert 9 <= sa.scheduled_start.hour < 17

    def test_schedule_comment_period(self):
        scheduler = ActionScheduler()
        deadline = datetime(2026, 4, 15, 23, 59)
        scheduled = scheduler.schedule_comment_period(
            action_ids=list(range(1, 31)),
            comment_deadline=deadline,
        )
        assert len(scheduled) == 30
        # All before deadline
        for sa in scheduled:
            assert sa.scheduled_start < deadline
        # Should have early, middle, and ramp-up batches
        batch_ids = set(sa.batch_id for sa in scheduled)
        assert "comment-early" in batch_ids
        assert "comment-rampup" in batch_ids

    def test_schedule_escalation_sequence(self):
        scheduler = ActionScheduler()
        phases = [
            {"phase": 1, "name": "Direct Engagement", "duration_weeks": 2, "tactics": []},
            {"phase": 2, "name": "Public Pressure", "duration_weeks": 4, "tactics": []},
        ]
        actions_per_phase = {
            1: list(range(1, 6)),
            2: list(range(6, 16)),
        }
        scheduled = scheduler.schedule_escalation_sequence(
            phases=phases,
            campaign_start=date(2026, 3, 2),
            actions_per_phase=actions_per_phase,
        )
        assert len(scheduled) > 0
        # Phase 1 actions should come before phase 2
        phase1 = [sa for sa in scheduled if sa.batch_id and "phase-1" in sa.batch_id]
        phase2 = [sa for sa in scheduled if sa.batch_id and "phase-2" in sa.batch_id]
        if phase1 and phase2:
            assert max(sa.scheduled_start for sa in phase1) < min(sa.scheduled_start for sa in phase2)

    def test_schedule_summary(self):
        scheduler = ActionScheduler()
        window = ScheduleWindow(
            start=datetime(2026, 3, 2, 9, 0),
            end=datetime(2026, 3, 6, 17, 0),
        )
        scheduled = scheduler.schedule_email_campaign(
            action_ids=list(range(1, 11)),
            window=window,
        )
        summary = scheduler.get_schedule_summary(scheduled)
        assert summary["total"] > 0
        assert "start" in summary
        assert "end" in summary
        assert "peak_date" in summary
