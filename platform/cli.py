"""
Campaign Platform CLI

Usage:
    campaign create --name "..." --type corporate --target "..." --goal "..."
    campaign actions --campaign-id 1 --minutes 15
    campaign track --campaign-id 1
    campaign template --type email --variant corporate_ceo
    campaign export --campaign-id 1 --format json
"""

import json
import sys
from datetime import date, datetime
from typing import Optional

import click
from sqlalchemy.orm import Session

from platform.campaigns.models import (
    Campaign,
    Action,
    Target,
    Participant,
    CampaignType,
    CampaignStatus,
    ActionType,
    ActionStatus,
    create_tables,
    get_session,
)
from platform.campaigns.campaign_builder import CampaignBuilder
from platform.campaigns.action_generator import ActionGenerator
from platform.metrics.impact_tracker import ImpactTracker
from platform.metrics.roi_calculator import ROICalculator


def get_db() -> Session:
    engine = create_tables()
    return get_session(engine)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Campaign Coordination Platform - Multiply impact through coordinated action."""
    pass


# --- Campaign Commands ---


@cli.command()
@click.option("--name", required=True, help="Campaign name")
@click.option(
    "--type",
    "campaign_type",
    required=True,
    type=click.Choice(["corporate", "legislative", "regulatory", "investigation", "cultural"]),
    help="Campaign type (determines template and escalation structure)",
)
@click.option("--target", required=True, help="Who or what is being targeted")
@click.option("--goal", required=True, help="Specific, measurable outcome")
@click.option("--start-date", default=None, help="Start date (YYYY-MM-DD), defaults to today")
def create(name: str, campaign_type: str, target: str, goal: str, start_date: Optional[str]):
    """Create a new campaign from a template."""
    db = get_db()
    try:
        start = date.fromisoformat(start_date) if start_date else None
        campaign = CampaignBuilder.build_campaign(
            name=name,
            campaign_type=CampaignType(campaign_type),
            target_summary=target,
            goal=goal,
            start_date=start,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        click.echo(f"\nCampaign created: {campaign.name}")
        click.echo(f"  ID: {campaign.id}")
        click.echo(f"  Type: {campaign.campaign_type}")
        click.echo(f"  Status: {campaign.status}")
        click.echo(f"  Start: {campaign.start_date}")
        click.echo(f"  Deadline: {campaign.deadline}")
        click.echo(f"  Phases: {len(campaign.escalation_ladder)}")
        click.echo(f"  Channels: {', '.join(campaign.channels)}")
        click.echo()

        # Show escalation ladder
        for phase in campaign.escalation_ladder:
            click.echo(f"  Phase {phase['phase']}: {phase['name']} ({phase['duration_weeks']} weeks)")
            for tactic in phase["tactics"]:
                click.echo(f"    - {tactic}")
            click.echo(f"    Win trigger: {phase['win_trigger']}")
            click.echo()

    finally:
        db.close()


@cli.command()
@click.option("--status", default=None, help="Filter by status")
@click.option("--type", "campaign_type", default=None, help="Filter by type")
def list_campaigns(status: Optional[str], campaign_type: Optional[str]):
    """List all campaigns."""
    db = get_db()
    try:
        query = db.query(Campaign)
        if status:
            query = query.filter(Campaign.status == CampaignStatus(status))
        if campaign_type:
            query = query.filter(Campaign.campaign_type == CampaignType(campaign_type))

        campaigns = query.order_by(Campaign.created_at.desc()).all()

        if not campaigns:
            click.echo("No campaigns found.")
            return

        click.echo(f"\n{'ID':<5} {'Name':<40} {'Type':<15} {'Status':<12} {'Progress'}")
        click.echo("-" * 85)
        for c in campaigns:
            click.echo(
                f"{c.id:<5} {c.name[:38]:<40} {c.campaign_type:<15} "
                f"{c.status:<12} {c.completion_pct}%"
            )
        click.echo()

    finally:
        db.close()


# --- Action Commands ---


@cli.command()
@click.option("--campaign-id", required=True, type=int, help="Campaign ID")
@click.option("--minutes", required=True, type=int, help="Minutes available (5, 15, 30, 120)")
@click.option("--participant-id", default=None, type=int, help="Participant ID for skill matching")
@click.option("--create/--no-create", "create_actions", default=False, help="Create actions in DB")
def actions(campaign_id: int, minutes: int, participant_id: Optional[int], create_actions: bool):
    """Generate actions based on time available."""
    db = get_db()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            click.echo(f"Campaign {campaign_id} not found.", err=True)
            sys.exit(1)

        participant = None
        if participant_id:
            participant = db.query(Participant).filter(
                Participant.id == participant_id
            ).first()

        targets = db.query(Target).filter(Target.campaign_id == campaign_id).all()

        specs = ActionGenerator.generate_for_time(
            campaign=campaign,
            minutes_available=minutes,
            targets=targets,
            participant=participant,
        )

        if not specs:
            click.echo(f"No actions available for {minutes} minutes in this campaign.")
            return

        click.echo(f"\nActions for {minutes} minutes - {campaign.name}:")
        click.echo(f"{'#':<4} {'Type':<18} {'Time':<8} {'Title'}")
        click.echo("-" * 70)

        for i, spec in enumerate(specs, 1):
            click.echo(
                f"{i:<4} {spec.action_type.value:<18} {spec.estimated_minutes}min"
                f"{'':>4} {spec.title}"
            )

        if create_actions:
            click.echo("\nCreating actions in database...")
            for spec in specs:
                action = ActionGenerator.generate_action_from_spec(spec, campaign_id)
                db.add(action)
            db.commit()
            click.echo(f"Created {len(specs)} actions.")

        click.echo()

    finally:
        db.close()


@cli.command()
@click.option("--action-id", required=True, type=int, help="Action ID to complete")
@click.option("--verification-url", default=None, help="URL proving action was taken")
def complete(action_id: int, verification_url: Optional[str]):
    """Mark an action as completed."""
    db = get_db()
    try:
        action = db.query(Action).filter(Action.id == action_id).first()
        if not action:
            click.echo(f"Action {action_id} not found.", err=True)
            sys.exit(1)

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
        click.echo(f"Action {action_id} marked as completed.")

    finally:
        db.close()


# --- Tracking Commands ---


@cli.command()
@click.option("--campaign-id", required=True, type=int, help="Campaign ID")
@click.option("--detailed/--summary", default=False, help="Show detailed breakdown")
def track(campaign_id: int, detailed: bool):
    """Track campaign progress and impact metrics."""
    db = get_db()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            click.echo(f"Campaign {campaign_id} not found.", err=True)
            sys.exit(1)

        actions_list = db.query(Action).filter(Action.campaign_id == campaign_id).all()
        tracker = ImpactTracker()
        metrics = tracker.compute_campaign_metrics(campaign, actions_list)

        click.echo(f"\n{'='*60}")
        click.echo(f"  {campaign.name}")
        click.echo(f"  Status: {campaign.status}  |  Progress: {campaign.completion_pct}%")
        click.echo(f"{'='*60}")

        s = metrics["summary"]
        click.echo(f"\n  Total Actions:  {s['total_actions']}")
        click.echo(f"  Completed:      {s['completed']} ({s['completion_rate']}%)")
        click.echo(f"  Verified:       {s['verified']} ({s['verification_rate']}%)")
        click.echo(f"  Overdue:        {s['overdue']}")

        a = metrics["activity_counts"]
        click.echo(f"\n  Activity Breakdown:")
        click.echo(f"    Emails sent:      {a['emails_sent']}")
        click.echo(f"    Calls made:       {a['calls_made']}")
        click.echo(f"    Comments filed:   {a['comments_filed']}")
        click.echo(f"    Reviews posted:   {a['reviews_posted']}")
        click.echo(f"    FOIAs filed:      {a['foia_filed']}")
        click.echo(f"    Testimonies:      {a['testimonies_given']}")
        click.echo(f"    Social posts:     {a['social_posts']}")

        i = metrics["impact"]
        click.echo(f"\n  Impact Score:       {i['total_impact_score']}")
        click.echo(f"  Impact per Action:  {i['impact_per_action']}")
        click.echo(f"  Velocity:           {i['velocity_per_week']} actions/week")

        ch = metrics["channels"]
        click.echo(f"\n  Channels Active:    {len(ch['active'])}/{ch['total_possible']} ({ch['coverage_pct']}%)")
        click.echo(f"    {', '.join(ch['active'])}")

        if detailed and metrics.get("type_breakdown"):
            click.echo(f"\n  Action Type Details:")
            for atype, data in metrics["type_breakdown"].items():
                click.echo(
                    f"    {atype:<25} {data['completed']}/{data['total']} "
                    f"({data['completion_rate']}%)"
                )

        # ROI
        calculator = ROICalculator()
        roi = calculator.calculate_campaign_roi(campaign, actions_list)

        click.echo(f"\n  ROI Analysis:")
        click.echo(f"    Volunteer hours:  {roi['investment']['total_volunteer_hours']}")
        click.echo(f"    Value generated:  ${roi['returns']['total_value']:.2f}")
        click.echo(f"    ROI:              {roi['efficiency']['roi_pct']}%")
        click.echo(f"    Value per hour:   ${roi['efficiency']['value_per_volunteer_hour']:.2f}")

        if roi.get("recommendations"):
            click.echo(f"\n  Recommendations:")
            for rec in roi["recommendations"]:
                click.echo(f"    > {rec}")

        click.echo()

    finally:
        db.close()


# --- Template Commands ---


@cli.command()
@click.option(
    "--type",
    "template_type",
    required=True,
    type=click.Choice(["email", "phone", "social", "review"]),
    help="Template category",
)
@click.option("--variant", default=None, help="Specific template variant")
@click.option("--list/--no-list", "list_templates", default=False, help="List available templates")
def template(template_type: str, variant: Optional[str], list_templates: bool):
    """View or list action templates."""
    import os

    template_dirs = {
        "email": "email_templates",
        "phone": "phone_scripts",
        "social": "social_templates",
        "review": "review_templates",
    }

    template_dir = os.path.join(
        os.path.dirname(__file__), "templates", template_dirs[template_type]
    )

    if list_templates or not variant:
        if os.path.isdir(template_dir):
            templates = [f for f in os.listdir(template_dir) if f.endswith(".txt")]
            click.echo(f"\nAvailable {template_type} templates:")
            for t in sorted(templates):
                click.echo(f"  - {t.replace('.txt', '')}")
            click.echo()
        else:
            click.echo(f"No templates found for {template_type}")
        return

    template_path = os.path.join(template_dir, f"{variant}.txt")
    if not os.path.isfile(template_path):
        click.echo(f"Template not found: {variant}", err=True)
        click.echo(f"Use --list to see available templates.", err=True)
        sys.exit(1)

    with open(template_path) as f:
        click.echo(f.read())


# --- Export Commands ---


@cli.command()
@click.option("--campaign-id", required=True, type=int, help="Campaign ID")
@click.option(
    "--format",
    "output_format",
    default="json",
    type=click.Choice(["json", "csv"]),
    help="Export format",
)
@click.option("--output", "-o", default=None, help="Output file path")
def export(campaign_id: int, output_format: str, output: Optional[str]):
    """Export campaign data."""
    db = get_db()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            click.echo(f"Campaign {campaign_id} not found.", err=True)
            sys.exit(1)

        actions_list = db.query(Action).filter(Action.campaign_id == campaign_id).all()
        targets = db.query(Target).filter(Target.campaign_id == campaign_id).all()

        if output_format == "json":
            data = {
                "campaign": {
                    "id": campaign.id,
                    "name": campaign.name,
                    "type": campaign.campaign_type,
                    "target": campaign.target_summary,
                    "goal": campaign.goal,
                    "status": campaign.status,
                    "channels": campaign.channels,
                    "escalation_ladder": campaign.escalation_ladder,
                    "start_date": str(campaign.start_date),
                    "deadline": str(campaign.deadline),
                    "completion_pct": campaign.completion_pct,
                },
                "targets": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "type": t.target_type,
                        "organization": t.organization,
                        "vulnerability_score": t.vulnerability_score,
                    }
                    for t in targets
                ],
                "actions": [
                    {
                        "id": a.id,
                        "type": a.action_type,
                        "title": a.title,
                        "status": a.status,
                        "priority": a.priority,
                        "estimated_minutes": a.estimated_minutes,
                        "completed_at": str(a.completed_at) if a.completed_at else None,
                    }
                    for a in actions_list
                ],
            }
            result = json.dumps(data, indent=2)
        else:
            # CSV export of actions
            lines = ["id,type,title,status,priority,minutes,completed_at"]
            for a in actions_list:
                lines.append(
                    f"{a.id},{a.action_type},{a.title},{a.status},"
                    f"{a.priority},{a.estimated_minutes},{a.completed_at or ''}"
                )
            result = "\n".join(lines)

        if output:
            with open(output, "w") as f:
                f.write(result)
            click.echo(f"Exported to {output}")
        else:
            click.echo(result)

    finally:
        db.close()


# --- Campaign Types Info ---


@cli.command()
def types():
    """List available campaign types and their structures."""
    summaries = CampaignBuilder.list_campaign_types()

    click.echo("\nAvailable Campaign Types:")
    click.echo("=" * 60)

    for s in summaries:
        click.echo(f"\n  {s['type'].upper()}")
        click.echo(f"    Phases: {s['phases']} ({s['total_weeks']} weeks total)")
        click.echo(f"    Channels: {', '.join(s['channels'])}")
        click.echo(f"    Action types: {', '.join(s['action_types'])}")

    click.echo()


# --- Add Target ---


@cli.command()
@click.option("--campaign-id", required=True, type=int)
@click.option("--name", required=True, help="Target name")
@click.option(
    "--type",
    "target_type",
    required=True,
    type=click.Choice(["corporation", "executive", "legislator", "regulator", "facility", "brand", "investor"]),
)
@click.option("--org", default=None, help="Organization")
@click.option("--role", default=None, help="Title/role")
@click.option("--email", default=None, help="Contact email")
@click.option("--phone", default=None, help="Contact phone")
@click.option("--vulnerability", default=5.0, type=float, help="Vulnerability score (1-10)")
def add_target(
    campaign_id: int,
    name: str,
    target_type: str,
    org: Optional[str],
    role: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    vulnerability: float,
):
    """Add a target to a campaign."""
    db = get_db()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            click.echo(f"Campaign {campaign_id} not found.", err=True)
            sys.exit(1)

        contacts = {}
        if email:
            contacts["email"] = email
        if phone:
            contacts["phone"] = phone

        from platform.campaigns.models import TargetType
        target = Target(
            campaign_id=campaign_id,
            name=name,
            target_type=TargetType(target_type),
            organization=org,
            title_role=role,
            contacts=contacts if contacts else None,
            vulnerability_score=vulnerability,
        )
        db.add(target)
        db.commit()
        db.refresh(target)

        click.echo(f"\nTarget added: {target.name}")
        click.echo(f"  ID: {target.id}")
        click.echo(f"  Type: {target.target_type}")
        click.echo(f"  Organization: {target.organization or 'N/A'}")
        click.echo(f"  Vulnerability: {target.vulnerability_score}/10")
        click.echo()

    finally:
        db.close()


def main():
    cli()


if __name__ == "__main__":
    main()
