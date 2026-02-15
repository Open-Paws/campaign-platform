"""
Campaign Builder - Generate structured campaign plans from templates.

Each campaign type follows a proven escalation model:
1. Start with low-cost, high-volume actions (emails, social)
2. Escalate to higher-impact actions (media, shareholder, legal)
3. Maintain sustained pressure across multiple channels simultaneously

Templates encode real campaign structures used by effective advocacy orgs.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Any

from .models import (
    Campaign,
    Action,
    Target,
    CampaignType,
    CampaignStatus,
    ActionType,
    TargetType,
    TacticChannel,
)


class CampaignBuilder:
    """Build campaigns from proven templates with escalation ladders."""

    TEMPLATES: Dict[str, Dict[str, Any]] = {
        # --- CORPORATE CAMPAIGN ---
        # Pressure a company to change practices via multi-channel escalation
        CampaignType.CORPORATE: {
            "channels": [
                TacticChannel.EMAIL,
                TacticChannel.SOCIAL_MEDIA,
                TacticChannel.SHAREHOLDER,
                TacticChannel.CONSUMER,
                TacticChannel.MEDIA,
            ],
            "escalation_ladder": [
                {
                    "phase": 1,
                    "name": "Direct Engagement",
                    "duration_weeks": 2,
                    "tactics": [
                        "Email CEO and sustainability team with specific asks",
                        "Social media tagging of brand accounts with evidence",
                        "Online reviews citing specific documented conditions",
                    ],
                    "win_trigger": "Company agrees to meeting or issues statement",
                },
                {
                    "phase": 2,
                    "name": "Public Pressure",
                    "duration_weeks": 4,
                    "tactics": [
                        "Coordinated social media campaign with hashtag",
                        "Investor/shareholder inquiry letters",
                        "Media pitches to business and industry reporters",
                        "Consumer boycott launch with alternative recommendations",
                    ],
                    "win_trigger": "Media coverage or investor inquiry initiated",
                },
                {
                    "phase": 3,
                    "name": "Institutional Pressure",
                    "duration_weeks": 6,
                    "tactics": [
                        "Shareholder resolution filing",
                        "ESG rating agency complaints with documentation",
                        "Retailer/supplier pressure letters",
                        "Celebrity/influencer amplification",
                    ],
                    "win_trigger": "Board-level discussion or policy change announced",
                },
                {
                    "phase": 4,
                    "name": "Maximum Pressure",
                    "duration_weeks": 8,
                    "tactics": [
                        "Proxy vote campaign at annual meeting",
                        "Regulatory complaints (EPA, USDA, state AG)",
                        "Class action or citizen suit exploration",
                        "Documentary/long-form investigation partnership",
                    ],
                    "win_trigger": "Binding commitment with verification mechanism",
                },
            ],
            "action_types": [
                ActionType.EMAIL,
                ActionType.PHONE_CALL,
                ActionType.SOCIAL_POST,
                ActionType.REVIEW,
                ActionType.SHAREHOLDER_ACTION,
                ActionType.BOYCOTT,
            ],
        },
        # --- LEGISLATIVE CAMPAIGN ---
        # Move a bill or block harmful legislation
        CampaignType.LEGISLATIVE: {
            "channels": [
                TacticChannel.PHONE,
                TacticChannel.EMAIL,
                TacticChannel.GRASSROOTS,
                TacticChannel.MEDIA,
            ],
            "escalation_ladder": [
                {
                    "phase": 1,
                    "name": "Constituent Pressure",
                    "duration_weeks": 3,
                    "tactics": [
                        "Phone calls to target legislators (district + DC offices)",
                        "Constituent emails with personal stories",
                        "Town hall attendance and recorded questions",
                    ],
                    "win_trigger": "Legislator's office acknowledges volume of contact",
                },
                {
                    "phase": 2,
                    "name": "Coalition Building",
                    "duration_weeks": 4,
                    "tactics": [
                        "Sign-on letters from allied organizations",
                        "Expert testimony recruitment for committee hearings",
                        "Op-eds in district newspapers",
                        "Social media targeting of swing votes",
                    ],
                    "win_trigger": "Co-sponsor gained or committee hearing scheduled",
                },
                {
                    "phase": 3,
                    "name": "Floor Push",
                    "duration_weeks": 6,
                    "tactics": [
                        "Coordinated call-in days (500+ calls per office)",
                        "Lobby day with constituent meetings",
                        "Paid media in swing districts",
                        "Grasstops pressure (donors, local leaders)",
                    ],
                    "win_trigger": "Floor vote scheduled or amendment accepted",
                },
            ],
            "action_types": [
                ActionType.PHONE_CALL,
                ActionType.EMAIL,
                ActionType.TESTIMONY,
                ActionType.SOCIAL_POST,
                ActionType.CONTENT_CREATION,
            ],
        },
        # --- REGULATORY CAMPAIGN ---
        # Shape rulemaking or enforce existing regulations
        CampaignType.REGULATORY: {
            "channels": [
                TacticChannel.REGULATORY,
                TacticChannel.LEGAL,
                TacticChannel.MEDIA,
                TacticChannel.EMAIL,
            ],
            "escalation_ladder": [
                {
                    "phase": 1,
                    "name": "Comment Period Blitz",
                    "duration_weeks": 4,
                    "tactics": [
                        "File substantive public comments (unique, not form letters)",
                        "FOIA requests for agency communications with industry",
                        "Expert comment recruitment from scientists and vets",
                    ],
                    "win_trigger": "Agency acknowledges substantive comments requiring response",
                },
                {
                    "phase": 2,
                    "name": "Enforcement Push",
                    "duration_weeks": 6,
                    "tactics": [
                        "Complaints to inspectors general",
                        "State attorney general petitions",
                        "Media coverage of enforcement gaps",
                        "Congressional oversight requests",
                    ],
                    "win_trigger": "Investigation opened or enforcement action initiated",
                },
                {
                    "phase": 3,
                    "name": "Legal Action",
                    "duration_weeks": 12,
                    "tactics": [
                        "Citizen suit under Clean Water Act / Clean Air Act",
                        "Administrative Procedure Act challenge",
                        "State-level regulatory petitions",
                        "International trade complaint if applicable",
                    ],
                    "win_trigger": "Court order or consent decree",
                },
            ],
            "action_types": [
                ActionType.PUBLIC_COMMENT,
                ActionType.FOIA_REQUEST,
                ActionType.CITIZEN_SUIT,
                ActionType.EMAIL,
                ActionType.CONTENT_CREATION,
            ],
        },
        # --- INVESTIGATION CAMPAIGN ---
        # Build an evidence base for future action
        CampaignType.INVESTIGATION: {
            "channels": [
                TacticChannel.LEGAL,
                TacticChannel.MEDIA,
                TacticChannel.REGULATORY,
            ],
            "escalation_ladder": [
                {
                    "phase": 1,
                    "name": "Open Source Intelligence",
                    "duration_weeks": 4,
                    "tactics": [
                        "Corporate filing analysis (SEC, state registrations)",
                        "Permit and inspection record FOIA",
                        "Satellite imagery analysis of facility changes",
                        "Social media monitoring of employees and contractors",
                    ],
                    "win_trigger": "Pattern of violations or concealment documented",
                },
                {
                    "phase": 2,
                    "name": "Deep Investigation",
                    "duration_weeks": 8,
                    "tactics": [
                        "Targeted FOIA for agency-industry communications",
                        "Whistleblower outreach via secure channels",
                        "Supply chain mapping and verification",
                        "Water/air quality testing near facilities",
                    ],
                    "win_trigger": "Evidence package sufficient for legal or media action",
                },
                {
                    "phase": 3,
                    "name": "Publication & Action",
                    "duration_weeks": 4,
                    "tactics": [
                        "Investigative media partnership for publication",
                        "Regulatory complaint filing with evidence",
                        "Shareholder/investor briefing on findings",
                        "Public report release with recommendations",
                    ],
                    "win_trigger": "Investigation triggers enforcement or corporate change",
                },
            ],
            "action_types": [
                ActionType.OSINT_RESEARCH,
                ActionType.FOIA_REQUEST,
                ActionType.SATELLITE_ANALYSIS,
                ActionType.CONTENT_CREATION,
            ],
        },
        # --- CULTURAL CAMPAIGN ---
        # Shift public narratives and search results
        CampaignType.CULTURAL: {
            "channels": [
                TacticChannel.SOCIAL_MEDIA,
                TacticChannel.MEDIA,
                TacticChannel.CONSUMER,
                TacticChannel.GRASSROOTS,
            ],
            "escalation_ladder": [
                {
                    "phase": 1,
                    "name": "Content Seeding",
                    "duration_weeks": 4,
                    "tactics": [
                        "SEO-optimized articles targeting industry search terms",
                        "Social media content series with shareable assets",
                        "Influencer outreach with talking points and evidence",
                        "Reddit/forum engagement in relevant communities",
                    ],
                    "win_trigger": "Content ranking for target keywords or viral reach",
                },
                {
                    "phase": 2,
                    "name": "Narrative Amplification",
                    "duration_weeks": 6,
                    "tactics": [
                        "Op-ed placement in major outlets",
                        "Podcast guest appearances on aligned shows",
                        "Short-form video series for TikTok/Instagram/YouTube",
                        "Coordinated social sharing with engagement pods",
                    ],
                    "win_trigger": "Mainstream media adoption of framing or terminology",
                },
                {
                    "phase": 3,
                    "name": "Cultural Anchoring",
                    "duration_weeks": 8,
                    "tactics": [
                        "Documentary or long-form video production",
                        "Curriculum or educational material development",
                        "Celebrity/public figure endorsement",
                        "Annual awareness event or day establishment",
                    ],
                    "win_trigger": "Sustained shift in public discourse metrics",
                },
            ],
            "action_types": [
                ActionType.CONTENT_CREATION,
                ActionType.SEO_ARTICLE,
                ActionType.SOCIAL_POST,
            ],
        },
    }

    @classmethod
    def get_template(cls, campaign_type: CampaignType) -> Dict[str, Any]:
        """Get the full template for a campaign type."""
        return cls.TEMPLATES[campaign_type]

    @classmethod
    def build_campaign(
        cls,
        name: str,
        campaign_type: CampaignType,
        target_summary: str,
        goal: str,
        start_date: Optional[date] = None,
        custom_escalation: Optional[List[dict]] = None,
    ) -> Campaign:
        """
        Build a campaign instance from a template.

        Args:
            name: Campaign name (e.g., "Smithfield Gestation Crate Phase-Out")
            campaign_type: Type determines template and escalation structure
            target_summary: Who/what we're targeting
            goal: Specific, measurable outcome we want
            start_date: When to begin (defaults to today)
            custom_escalation: Override default escalation ladder

        Returns:
            Campaign object ready to be added to a session
        """
        template = cls.TEMPLATES[campaign_type]
        start = start_date or date.today()

        # Calculate deadline from escalation phases
        total_weeks = sum(
            phase["duration_weeks"]
            for phase in (custom_escalation or template["escalation_ladder"])
        )
        deadline = start + timedelta(weeks=total_weeks)

        # Build slug from name
        slug = name.lower().replace(" ", "-").replace("'", "")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")

        campaign = Campaign(
            name=name,
            slug=slug,
            campaign_type=campaign_type,
            target_summary=target_summary,
            goal=goal,
            status=CampaignStatus.DRAFT,
            channels=[ch.value for ch in template["channels"]],
            tactics=[at.value for at in template["action_types"]],
            escalation_ladder=custom_escalation or template["escalation_ladder"],
            win_conditions=[
                phase["win_trigger"]
                for phase in (custom_escalation or template["escalation_ladder"])
            ],
            start_date=start,
            deadline=deadline,
        )

        return campaign

    @classmethod
    def generate_phase_actions(
        cls,
        campaign: Campaign,
        phase_number: int,
        targets: Optional[List[Target]] = None,
    ) -> List[Action]:
        """
        Generate concrete actions for a specific escalation phase.

        Each tactic in the phase becomes one or more actions, parameterized
        by the targets provided.
        """
        if not campaign.escalation_ladder:
            return []

        phase = None
        for p in campaign.escalation_ladder:
            if p["phase"] == phase_number:
                phase = p
                break

        if phase is None:
            raise ValueError(f"Phase {phase_number} not found in campaign escalation ladder")

        actions = []
        priority = phase_number  # earlier phases = higher priority

        for i, tactic in enumerate(phase["tactics"]):
            action_type = cls._infer_action_type(tactic)
            estimated_minutes = cls._estimate_minutes(action_type)
            template_name = cls._suggest_template(action_type)

            if targets:
                for target in targets:
                    action = Action(
                        campaign_id=campaign.id,
                        action_type=action_type,
                        title=f"Phase {phase_number}: {tactic[:80]}",
                        description=(
                            f"{tactic}\n\nTarget: {target.name}"
                            f"{f' ({target.organization})' if target.organization else ''}"
                        ),
                        template_name=template_name,
                        template_vars={
                            "target_name": target.name,
                            "target_org": target.organization,
                            "target_role": target.title_role,
                            "contacts": target.contacts,
                            "social": target.social_accounts,
                        },
                        estimated_minutes=estimated_minutes,
                        priority=priority,
                    )
                    actions.append(action)
            else:
                action = Action(
                    campaign_id=campaign.id,
                    action_type=action_type,
                    title=f"Phase {phase_number}: {tactic[:80]}",
                    description=tactic,
                    template_name=template_name,
                    estimated_minutes=estimated_minutes,
                    priority=priority,
                )
                actions.append(action)

        return actions

    @staticmethod
    def _infer_action_type(tactic: str) -> ActionType:
        """Infer the best action type from tactic description text."""
        tactic_lower = tactic.lower()
        mapping = [
            (["email", "letter"], ActionType.EMAIL),
            (["phone", "call"], ActionType.PHONE_CALL),
            (["social media", "twitter", "instagram", "hashtag", "tiktok"], ActionType.SOCIAL_POST),
            (["public comment", "comment period", "rulemaking"], ActionType.PUBLIC_COMMENT),
            (["foia", "freedom of information"], ActionType.FOIA_REQUEST),
            (["review", "google review", "yelp"], ActionType.REVIEW),
            (["testimony", "hearing", "town hall"], ActionType.TESTIMONY),
            (["shareholder", "proxy", "investor", "esg"], ActionType.SHAREHOLDER_ACTION),
            (["boycott", "alternative"], ActionType.BOYCOTT),
            (["seo", "article", "blog"], ActionType.SEO_ARTICLE),
            (["osint", "corporate filing", "permit", "record"], ActionType.OSINT_RESEARCH),
            (["satellite", "imagery"], ActionType.SATELLITE_ANALYSIS),
            (["citizen suit", "lawsuit", "legal action", "court"], ActionType.CITIZEN_SUIT),
            (["content", "video", "op-ed", "documentary", "podcast"], ActionType.CONTENT_CREATION),
        ]
        for keywords, action_type in mapping:
            if any(kw in tactic_lower for kw in keywords):
                return action_type
        return ActionType.CONTENT_CREATION  # fallback

    @staticmethod
    def _estimate_minutes(action_type: ActionType) -> int:
        """Estimate minutes needed for an action type."""
        estimates = {
            ActionType.PHONE_CALL: 5,
            ActionType.EMAIL: 15,
            ActionType.SOCIAL_POST: 10,
            ActionType.REVIEW: 15,
            ActionType.PUBLIC_COMMENT: 30,
            ActionType.TESTIMONY: 120,
            ActionType.FOIA_REQUEST: 120,
            ActionType.SHAREHOLDER_ACTION: 240,
            ActionType.BOYCOTT: 15,
            ActionType.CONTENT_CREATION: 120,
            ActionType.SEO_ARTICLE: 180,
            ActionType.OSINT_RESEARCH: 240,
            ActionType.SATELLITE_ANALYSIS: 180,
            ActionType.CITIZEN_SUIT: 480,
        }
        return estimates.get(action_type, 30)

    @staticmethod
    def _suggest_template(action_type: ActionType) -> Optional[str]:
        """Suggest a template file for an action type."""
        templates = {
            ActionType.EMAIL: "email_templates/corporate_ceo.txt",
            ActionType.PHONE_CALL: "phone_scripts/congressional_call.txt",
            ActionType.SOCIAL_POST: "social_templates/twitter_thread.txt",
            ActionType.PUBLIC_COMMENT: "email_templates/public_comment.txt",
            ActionType.REVIEW: "review_templates/google_review.txt",
        }
        return templates.get(action_type)

    @classmethod
    def list_campaign_types(cls) -> List[Dict[str, Any]]:
        """List all available campaign types with summaries."""
        summaries = []
        for ctype, template in cls.TEMPLATES.items():
            summaries.append({
                "type": ctype.value,
                "channels": [ch.value for ch in template["channels"]],
                "phases": len(template["escalation_ladder"]),
                "total_weeks": sum(
                    p["duration_weeks"] for p in template["escalation_ladder"]
                ),
                "action_types": [at.value for at in template["action_types"]],
            })
        return summaries
