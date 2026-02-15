"""
Action Generator - Match volunteers to actions based on time available.

The core insight: most people have 5 minutes, not 5 hours. A platform that
only offers heavyweight actions loses 90% of potential participants. This
generator produces right-sized actions that respect people's time while
maximizing collective impact.

Time tiers:
  5 min  -> Phone call with script, social media share, sign petition
  15 min -> Personalized email, review, social media post with original content
  30 min -> Public comment, detailed letter, research task
  2 hr   -> FOIA request, testimony prep, investigative research, content creation
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .models import (
    Campaign,
    Action,
    Target,
    Participant,
    ActionType,
    ActionStatus,
    CampaignStatus,
)


@dataclass
class ActionSpec:
    """Specification for generating a concrete action."""
    action_type: ActionType
    title: str
    description: str
    template_name: Optional[str] = None
    template_vars: Optional[Dict[str, Any]] = None
    estimated_minutes: int = 15
    priority: int = 5
    requires_skills: List[str] = field(default_factory=list)


class ActionGenerator:
    """Generate right-sized actions for volunteers based on available time."""

    # Time tier definitions: (max_minutes, available_action_types)
    TIME_TIERS: Dict[str, Tuple[int, List[ActionType]]] = {
        "quick": (
            5,
            [ActionType.PHONE_CALL, ActionType.SOCIAL_POST],
        ),
        "short": (
            15,
            [
                ActionType.EMAIL,
                ActionType.REVIEW,
                ActionType.SOCIAL_POST,
                ActionType.PHONE_CALL,
            ],
        ),
        "medium": (
            30,
            [
                ActionType.PUBLIC_COMMENT,
                ActionType.EMAIL,
                ActionType.REVIEW,
                ActionType.SOCIAL_POST,
                ActionType.PHONE_CALL,
                ActionType.CONTENT_CREATION,
            ],
        ),
        "long": (
            120,
            [
                ActionType.FOIA_REQUEST,
                ActionType.TESTIMONY,
                ActionType.CONTENT_CREATION,
                ActionType.SEO_ARTICLE,
                ActionType.OSINT_RESEARCH,
                ActionType.SHAREHOLDER_ACTION,
                ActionType.PUBLIC_COMMENT,
                ActionType.EMAIL,
                ActionType.REVIEW,
                ActionType.SOCIAL_POST,
                ActionType.PHONE_CALL,
            ],
        ),
    }

    # Action generation templates by type
    ACTION_BLUEPRINTS: Dict[ActionType, Dict[str, Any]] = {
        ActionType.PHONE_CALL: {
            "estimated_minutes": 5,
            "template_name": "phone_scripts/congressional_call.txt",
            "description_template": (
                "Call {target_name} at {phone_number}.\n\n"
                "Use the provided phone script. Key points:\n"
                "1. Identify yourself as a constituent/customer/stakeholder\n"
                "2. State your specific ask clearly\n"
                "3. Ask for a commitment or timeline\n"
                "4. Log the response\n\n"
                "Expected duration: 3-5 minutes including hold time."
            ),
            "requires_skills": [],
        },
        ActionType.EMAIL: {
            "estimated_minutes": 15,
            "template_name": "email_templates/corporate_ceo.txt",
            "description_template": (
                "Send a personalized email to {target_name} ({target_email}).\n\n"
                "Use the template as a starting point but personalize:\n"
                "- Reference a specific incident, report, or finding\n"
                "- Include your personal connection to the issue\n"
                "- Make one clear, specific ask\n"
                "- Be professional but direct\n\n"
                "Personalizing emails 10x more effective than form letters."
            ),
            "requires_skills": ["writing"],
        },
        ActionType.SOCIAL_POST: {
            "estimated_minutes": 10,
            "template_name": "social_templates/twitter_thread.txt",
            "description_template": (
                "Post about {campaign_name} on social media.\n\n"
                "Effective social pressure tactics:\n"
                "- Tag the company/official directly\n"
                "- Include specific evidence (photos, data, documents)\n"
                "- Use campaign hashtag: #{hashtag}\n"
                "- Tag journalists and allied orgs for amplification\n"
                "- Post during peak hours (9-11am, 7-9pm target timezone)\n\n"
                "Social posts are most effective when coordinated with others."
            ),
            "requires_skills": ["social_media"],
        },
        ActionType.PUBLIC_COMMENT: {
            "estimated_minutes": 30,
            "template_name": "email_templates/public_comment.txt",
            "description_template": (
                "Submit a public comment on {regulation_name}.\n\n"
                "Docket: {docket_number}\n"
                "Deadline: {comment_deadline}\n\n"
                "Substantive comments that agencies must respond to:\n"
                "- Cite specific data, studies, or documented conditions\n"
                "- Reference the agency's own stated goals or legal mandates\n"
                "- Propose specific regulatory language or standards\n"
                "- Describe concrete harms from current policy\n\n"
                "IMPORTANT: Each comment must be unique. Do not copy templates verbatim.\n"
                "Agencies weigh substantive comments, not volume of form letters."
            ),
            "requires_skills": ["writing", "research"],
        },
        ActionType.FOIA_REQUEST: {
            "estimated_minutes": 120,
            "template_name": None,
            "description_template": (
                "File a FOIA request with {agency_name}.\n\n"
                "Requesting: {foia_subject}\n\n"
                "Key elements for an effective FOIA:\n"
                "- Be specific about records sought (dates, topics, officials)\n"
                "- Request fee waiver citing public interest\n"
                "- Request expedited processing if deadline-relevant\n"
                "- Include all required elements per agency regulations\n"
                "- File with the correct FOIA office for the records sought\n\n"
                "Track your request number and follow up at 20-day mark."
            ),
            "requires_skills": ["legal", "research"],
        },
        ActionType.REVIEW: {
            "estimated_minutes": 15,
            "template_name": "review_templates/google_review.txt",
            "description_template": (
                "Post a factual review about {target_name}.\n\n"
                "Review guidelines:\n"
                "- Base every claim on documented facts\n"
                "- Reference specific reports, inspections, or incidents\n"
                "- Include dates and sources where possible\n"
                "- Describe personal experience or documented conditions\n"
                "- Stay factual -- emotional but accurate\n\n"
                "Reviews that cite verifiable facts are harder to remove."
            ),
            "requires_skills": [],
        },
        ActionType.TESTIMONY: {
            "estimated_minutes": 120,
            "template_name": None,
            "description_template": (
                "Prepare testimony for {hearing_name}.\n\n"
                "Hearing date: {hearing_date}\n"
                "Committee: {committee_name}\n\n"
                "Effective testimony structure:\n"
                "1. Personal introduction and standing\n"
                "2. One clear main point (repeat it)\n"
                "3. Supporting evidence (3 specific examples max)\n"
                "4. Concrete policy recommendation\n"
                "5. Memorable closing statement\n\n"
                "Keep to 3 minutes unless allocated more time.\n"
                "Practice aloud. Bring printed copies for committee members."
            ),
            "requires_skills": ["writing", "research"],
        },
        ActionType.CONTENT_CREATION: {
            "estimated_minutes": 120,
            "template_name": None,
            "description_template": (
                "Create content for {campaign_name}.\n\n"
                "Content type: {content_type}\n"
                "Target audience: {audience}\n\n"
                "Content should:\n"
                "- Lead with the most compelling evidence\n"
                "- Include a clear call to action\n"
                "- Be shareable (under 3 min for video, scannable for text)\n"
                "- Cite sources for all claims\n"
                "- Use accessible language (8th grade reading level)"
            ),
            "requires_skills": ["writing", "design"],
        },
        ActionType.SEO_ARTICLE: {
            "estimated_minutes": 180,
            "template_name": None,
            "description_template": (
                "Write an SEO-optimized article targeting: '{target_keyword}'.\n\n"
                "Goal: Rank on first page for searches about {topic}.\n\n"
                "Article requirements:\n"
                "- 1500-2500 words\n"
                "- Primary keyword in title, H1, first paragraph, and conclusion\n"
                "- 3-5 secondary keywords naturally integrated\n"
                "- At least 5 authoritative outbound links\n"
                "- Meta description under 160 characters\n"
                "- Include original data, charts, or images\n\n"
                "Publish on: {publication_target}"
            ),
            "requires_skills": ["writing", "research"],
        },
        ActionType.OSINT_RESEARCH: {
            "estimated_minutes": 240,
            "template_name": None,
            "description_template": (
                "Conduct open-source research on {research_target}.\n\n"
                "Research areas:\n"
                "- Corporate filings (SEC EDGAR, state registrations)\n"
                "- Permit records and inspection reports\n"
                "- Environmental compliance databases\n"
                "- Lobbying disclosures and political donations\n"
                "- Social media presence of key executives\n"
                "- News archive search for past incidents\n\n"
                "Document all findings with source URLs and screenshots.\n"
                "Use the evidence template for consistent formatting."
            ),
            "requires_skills": ["research", "data_analysis"],
        },
        ActionType.SHAREHOLDER_ACTION: {
            "estimated_minutes": 240,
            "template_name": "email_templates/investor_relations.txt",
            "description_template": (
                "Take shareholder action regarding {target_name}.\n\n"
                "Options based on share ownership:\n"
                "- Direct inquiry to investor relations\n"
                "- Proxy statement analysis and vote recommendation\n"
                "- ESG rating agency submission\n"
                "- Shareholder resolution drafting (requires $2K+ in shares)\n\n"
                "Even non-shareholders can contact investor relations with\n"
                "factual inquiries about ESG risks and material disclosures."
            ),
            "requires_skills": ["research"],
        },
        ActionType.SATELLITE_ANALYSIS: {
            "estimated_minutes": 180,
            "template_name": None,
            "description_template": (
                "Analyze satellite imagery of {facility_name}.\n\n"
                "Location: {coordinates}\n\n"
                "Look for:\n"
                "- Facility expansion beyond permitted boundaries\n"
                "- Waste lagoon conditions and overflow indicators\n"
                "- Changes over time (compare historical imagery)\n"
                "- Environmental impact on surrounding land/water\n\n"
                "Tools: Google Earth Pro (free), Sentinel Hub, Planet Explorer\n"
                "Document findings with timestamped screenshots."
            ),
            "requires_skills": ["research", "data_analysis"],
        },
        ActionType.CITIZEN_SUIT: {
            "estimated_minutes": 480,
            "template_name": None,
            "description_template": (
                "Evaluate citizen suit potential against {target_name}.\n\n"
                "Statute: {applicable_statute}\n"
                "Violation: {violation_description}\n\n"
                "Citizen suit checklist:\n"
                "1. Confirm statutory standing (CWA, CAA, RCRA allow citizen suits)\n"
                "2. Document ongoing or repeated violations\n"
                "3. Verify 60-day notice requirement\n"
                "4. Check for government diligent prosecution bar\n"
                "5. Identify potential legal partners (environmental law clinics)\n\n"
                "This is a research/evaluation task. Do not file without legal counsel."
            ),
            "requires_skills": ["legal", "research"],
        },
        ActionType.BOYCOTT: {
            "estimated_minutes": 15,
            "template_name": None,
            "description_template": (
                "Participate in boycott of {target_name}.\n\n"
                "Actions:\n"
                "- Switch to alternatives: {alternatives}\n"
                "- Share boycott information on social media\n"
                "- Contact company to explain why you are boycotting\n"
                "- Track and report your participation\n\n"
                "Boycotts work when companies see measurable revenue impact."
            ),
            "requires_skills": [],
        },
    }

    @classmethod
    def get_time_tier(cls, minutes_available: int) -> str:
        """Determine which time tier fits the available minutes."""
        if minutes_available <= 5:
            return "quick"
        elif minutes_available <= 15:
            return "short"
        elif minutes_available <= 30:
            return "medium"
        else:
            return "long"

    @classmethod
    def generate_for_time(
        cls,
        campaign: Campaign,
        minutes_available: int,
        targets: Optional[List[Target]] = None,
        participant: Optional[Participant] = None,
        max_actions: int = 5,
    ) -> List[ActionSpec]:
        """
        Generate actions that fit within the volunteer's available time.

        Args:
            campaign: The campaign to generate actions for
            minutes_available: How many minutes the volunteer has
            targets: Campaign targets to parameterize actions against
            participant: Optional participant for skill matching
            max_actions: Maximum number of actions to return

        Returns:
            List of ActionSpec objects, highest impact first
        """
        tier = cls.get_time_tier(minutes_available)
        _, eligible_types = cls.TIME_TIERS[tier]

        # Filter to action types that are both in the tier and in the campaign
        campaign_types = set()
        if campaign.tactics:
            for tactic in campaign.tactics:
                try:
                    campaign_types.add(ActionType(tactic))
                except ValueError:
                    pass

        available_types = [at for at in eligible_types if at in campaign_types] if campaign_types else eligible_types

        # Generate specs
        specs = []
        for action_type in available_types:
            blueprint = cls.ACTION_BLUEPRINTS.get(action_type)
            if not blueprint:
                continue

            # Skip if over time budget
            if blueprint["estimated_minutes"] > minutes_available:
                continue

            # Skip if participant lacks required skills
            if participant and blueprint["requires_skills"]:
                participant_skills = set(participant.skills or [])
                if not any(s in participant_skills for s in blueprint["requires_skills"]):
                    continue

            # Generate with target parameterization
            target_list = targets or [None]
            for target in target_list[:3]:  # cap targets per action type
                template_vars = cls._build_template_vars(
                    campaign, target, action_type
                )
                description = cls._fill_description(
                    blueprint["description_template"], template_vars
                )
                title = cls._generate_title(action_type, campaign, target)

                spec = ActionSpec(
                    action_type=action_type,
                    title=title,
                    description=description,
                    template_name=blueprint["template_name"],
                    template_vars=template_vars,
                    estimated_minutes=blueprint["estimated_minutes"],
                    priority=cls._calculate_priority(action_type, campaign, target),
                    requires_skills=blueprint["requires_skills"],
                )
                specs.append(spec)

        # Sort by priority (lower = more important) and return top N
        specs.sort(key=lambda s: s.priority)
        return specs[:max_actions]

    @classmethod
    def generate_action_from_spec(
        cls, spec: ActionSpec, campaign_id: int
    ) -> Action:
        """Convert an ActionSpec into an Action model instance."""
        return Action(
            campaign_id=campaign_id,
            action_type=spec.action_type,
            title=spec.title,
            description=spec.description,
            template_name=spec.template_name,
            template_vars=spec.template_vars,
            estimated_minutes=spec.estimated_minutes,
            priority=spec.priority,
        )

    @classmethod
    def suggest_next_action(
        cls,
        participant: Participant,
        campaigns: List[Campaign],
    ) -> Optional[ActionSpec]:
        """
        Suggest the single highest-impact action for a participant right now.

        Considers: participant skills, available time, campaign priority,
        and action urgency.
        """
        all_specs = []
        for campaign in campaigns:
            if campaign.status not in (CampaignStatus.ACTIVE, CampaignStatus.ESCALATING):
                continue
            specs = cls.generate_for_time(
                campaign=campaign,
                minutes_available=participant.availability_minutes_per_week,
                participant=participant,
                max_actions=3,
            )
            all_specs.extend(specs)

        if not all_specs:
            return None

        # Best action = lowest priority number (highest actual priority)
        all_specs.sort(key=lambda s: s.priority)
        return all_specs[0]

    @staticmethod
    def _build_template_vars(
        campaign: Campaign,
        target: Optional[Target],
        action_type: ActionType,
    ) -> Dict[str, Any]:
        """Build template variables from campaign and target data."""
        vars = {
            "campaign_name": campaign.name,
            "campaign_goal": campaign.goal,
            "hashtag": campaign.slug.replace("-", ""),
        }
        if target:
            vars.update({
                "target_name": target.name,
                "target_org": target.organization or "",
                "target_role": target.title_role or "",
                "target_email": (target.contacts or {}).get("email", "[email]"),
                "phone_number": (target.contacts or {}).get("phone", "[phone]"),
                "social": target.social_accounts or {},
            })
        return vars

    @staticmethod
    def _fill_description(template: str, vars: Dict[str, Any]) -> str:
        """Fill in description template, leaving unfilled vars as placeholders."""
        result = template
        for key, value in vars.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    @staticmethod
    def _generate_title(
        action_type: ActionType,
        campaign: Campaign,
        target: Optional[Target],
    ) -> str:
        """Generate a concise action title."""
        type_labels = {
            ActionType.PHONE_CALL: "Call",
            ActionType.EMAIL: "Email",
            ActionType.SOCIAL_POST: "Post about",
            ActionType.PUBLIC_COMMENT: "Comment on",
            ActionType.FOIA_REQUEST: "FOIA",
            ActionType.REVIEW: "Review",
            ActionType.TESTIMONY: "Testify on",
            ActionType.SHAREHOLDER_ACTION: "Shareholder action:",
            ActionType.BOYCOTT: "Boycott",
            ActionType.CONTENT_CREATION: "Create content:",
            ActionType.SEO_ARTICLE: "Write article:",
            ActionType.OSINT_RESEARCH: "Research",
            ActionType.SATELLITE_ANALYSIS: "Analyze",
            ActionType.CITIZEN_SUIT: "Legal evaluation:",
        }
        label = type_labels.get(action_type, action_type.value)
        target_str = target.name if target else campaign.target_summary[:40]
        return f"{label} {target_str}"

    @staticmethod
    def _calculate_priority(
        action_type: ActionType,
        campaign: Campaign,
        target: Optional[Target],
    ) -> int:
        """
        Calculate action priority (1=highest, 10=lowest).

        Factors:
        - Campaign status (escalating = higher priority)
        - Target vulnerability score (higher = more likely to yield)
        - Action type impact weight
        """
        base_priority = 5

        # Campaign urgency
        if campaign.status == CampaignStatus.ESCALATING:
            base_priority -= 2
        elif campaign.status == CampaignStatus.ACTIVE:
            base_priority -= 1

        # Target vulnerability
        if target and target.vulnerability_score:
            if target.vulnerability_score >= 8:
                base_priority -= 2
            elif target.vulnerability_score >= 6:
                base_priority -= 1

        # Action type impact weighting
        high_impact = {
            ActionType.TESTIMONY,
            ActionType.CITIZEN_SUIT,
            ActionType.SHAREHOLDER_ACTION,
            ActionType.FOIA_REQUEST,
        }
        medium_impact = {
            ActionType.PUBLIC_COMMENT,
            ActionType.EMAIL,
            ActionType.OSINT_RESEARCH,
        }

        if action_type in high_impact:
            base_priority -= 1
        elif action_type in medium_impact:
            pass  # neutral
        else:
            base_priority += 1

        return max(1, min(10, base_priority))
