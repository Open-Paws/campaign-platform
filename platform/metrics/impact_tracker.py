"""
Impact Tracker - Measure what matters across campaign activities.

Tracks: emails sent, calls made, comments filed, reviews posted,
media coverage instances, and corporate/government responses.

Every metric ties back to the question: did this action move the target
closer to our goal?
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter

from platform.campaigns.models import (
    Campaign,
    Action,
    ActionType,
    ActionStatus,
    CampaignStatus,
)


class ImpactTracker:
    """Track and analyze impact metrics across campaigns."""

    # Weight factors for different action types in impact scoring
    # Higher weight = more pressure per action
    ACTION_IMPACT_WEIGHTS: Dict[ActionType, float] = {
        ActionType.PHONE_CALL: 3.0,       # Direct human contact, logged by offices
        ActionType.EMAIL: 1.0,             # Baseline unit
        ActionType.SOCIAL_POST: 0.5,       # Volume-dependent, low individual impact
        ActionType.PUBLIC_COMMENT: 5.0,    # Legally must be addressed if substantive
        ActionType.FOIA_REQUEST: 8.0,      # Creates legal obligation, yields intel
        ActionType.REVIEW: 2.0,            # Visible to consumers, persistent
        ActionType.TESTIMONY: 10.0,        # Direct legislative impact, public record
        ActionType.SHAREHOLDER_ACTION: 12.0,  # Board-level pressure
        ActionType.BOYCOTT: 1.5,           # Collective impact
        ActionType.CONTENT_CREATION: 2.0,  # Narrative impact, variable reach
        ActionType.SEO_ARTICLE: 3.0,       # Long-term discoverability
        ActionType.OSINT_RESEARCH: 6.0,    # Enables other high-impact actions
        ActionType.SATELLITE_ANALYSIS: 7.0,  # Hard evidence, hard to dispute
        ActionType.CITIZEN_SUIT: 15.0,     # Maximum legal pressure
    }

    def compute_campaign_metrics(
        self,
        campaign: Campaign,
        actions: List[Action],
    ) -> Dict[str, Any]:
        """
        Compute comprehensive impact metrics for a campaign.

        Returns a dictionary with:
        - action_counts: breakdown by type
        - completion_rates: overall and by type
        - impact_score: weighted impact total
        - velocity: actions per week
        - channel_coverage: which channels are active
        - timeline: weekly action counts
        """
        completed = [
            a for a in actions
            if a.status in (ActionStatus.COMPLETED, ActionStatus.VERIFIED)
        ]
        verified = [a for a in actions if a.status == ActionStatus.VERIFIED]

        # Action counts by type
        type_counts = Counter()
        completed_type_counts = Counter()
        for a in actions:
            type_counts[a.action_type] += 1
        for a in completed:
            completed_type_counts[a.action_type] += 1

        # Specific activity metrics
        emails_sent = completed_type_counts.get(ActionType.EMAIL, 0)
        calls_made = completed_type_counts.get(ActionType.PHONE_CALL, 0)
        comments_filed = completed_type_counts.get(ActionType.PUBLIC_COMMENT, 0)
        reviews_posted = completed_type_counts.get(ActionType.REVIEW, 0)
        foia_filed = completed_type_counts.get(ActionType.FOIA_REQUEST, 0)
        testimonies = completed_type_counts.get(ActionType.TESTIMONY, 0)
        social_posts = completed_type_counts.get(ActionType.SOCIAL_POST, 0)

        # Impact score
        total_impact = sum(
            self.ACTION_IMPACT_WEIGHTS.get(ActionType(a.action_type), 1.0)
            for a in completed
        )

        # Velocity (actions per week since campaign start)
        if campaign.start_date and completed:
            days_active = max(1, (datetime.utcnow().date() - campaign.start_date).days)
            weeks_active = max(1, days_active / 7)
            velocity = round(len(completed) / weeks_active, 1)
        else:
            velocity = 0.0

        # Completion rate
        completion_rate = (
            round(len(completed) / len(actions) * 100, 1) if actions else 0.0
        )

        # Verification rate
        verification_rate = (
            round(len(verified) / len(completed) * 100, 1) if completed else 0.0
        )

        # Type completion rates
        type_completion_rates = {}
        for atype in type_counts:
            total = type_counts[atype]
            done = completed_type_counts.get(atype, 0)
            type_completion_rates[atype] = round(done / total * 100, 1) if total else 0.0

        # Overdue tracking
        overdue = [a for a in actions if a.is_overdue]

        # Weekly timeline
        weekly_timeline = self._build_weekly_timeline(completed)

        # Channel coverage
        active_channels = set()
        channel_map = {
            ActionType.EMAIL: "email",
            ActionType.PHONE_CALL: "phone",
            ActionType.SOCIAL_POST: "social_media",
            ActionType.PUBLIC_COMMENT: "regulatory",
            ActionType.FOIA_REQUEST: "legal",
            ActionType.REVIEW: "consumer",
            ActionType.TESTIMONY: "grassroots",
            ActionType.SHAREHOLDER_ACTION: "shareholder",
            ActionType.CONTENT_CREATION: "media",
            ActionType.SEO_ARTICLE: "media",
            ActionType.CITIZEN_SUIT: "legal",
        }
        for a in completed:
            channel = channel_map.get(ActionType(a.action_type))
            if channel:
                active_channels.add(channel)

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "summary": {
                "total_actions": len(actions),
                "completed": len(completed),
                "verified": len(verified),
                "overdue": len(overdue),
                "completion_rate": completion_rate,
                "verification_rate": verification_rate,
            },
            "activity_counts": {
                "emails_sent": emails_sent,
                "calls_made": calls_made,
                "comments_filed": comments_filed,
                "reviews_posted": reviews_posted,
                "foia_filed": foia_filed,
                "testimonies_given": testimonies,
                "social_posts": social_posts,
            },
            "impact": {
                "total_impact_score": round(total_impact, 1),
                "impact_per_action": (
                    round(total_impact / len(completed), 2) if completed else 0
                ),
                "velocity_per_week": velocity,
            },
            "channels": {
                "active": list(active_channels),
                "total_possible": len(set(channel_map.values())),
                "coverage_pct": round(
                    len(active_channels) / len(set(channel_map.values())) * 100, 1
                ),
            },
            "type_breakdown": {
                atype: {
                    "total": type_counts[atype],
                    "completed": completed_type_counts.get(atype, 0),
                    "completion_rate": type_completion_rates.get(atype, 0.0),
                }
                for atype in type_counts
            },
            "weekly_timeline": weekly_timeline,
        }

    def _build_weekly_timeline(self, completed_actions: List[Action]) -> List[Dict]:
        """Build a weekly breakdown of completed actions."""
        if not completed_actions:
            return []

        weekly = defaultdict(int)
        for a in completed_actions:
            if a.completed_at:
                week_start = a.completed_at.date() - timedelta(
                    days=a.completed_at.weekday()
                )
                weekly[week_start.isoformat()] += 1

        return [
            {"week": week, "actions_completed": count}
            for week, count in sorted(weekly.items())
        ]

    def compare_campaigns(
        self, campaigns_with_actions: List[tuple]
    ) -> List[Dict[str, Any]]:
        """
        Compare metrics across multiple campaigns.

        Args:
            campaigns_with_actions: List of (Campaign, List[Action]) tuples

        Returns:
            List of metric dicts, one per campaign, sorted by impact score
        """
        results = []
        for campaign, actions in campaigns_with_actions:
            metrics = self.compute_campaign_metrics(campaign, actions)
            results.append(metrics)

        results.sort(
            key=lambda m: m["impact"]["total_impact_score"], reverse=True
        )
        return results

    def get_media_coverage_score(
        self, mentions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Score media coverage impact from a list of mention records.

        Args:
            mentions: List of dicts with keys:
                - outlet: str (name of media outlet)
                - tier: int (1=national, 2=regional, 3=local, 4=trade, 5=blog)
                - date: str (ISO date)
                - url: str
                - sentiment: str ("positive", "neutral", "negative")

        Returns:
            Media impact summary
        """
        tier_weights = {1: 10.0, 2: 5.0, 3: 3.0, 4: 4.0, 5: 1.0}
        sentiment_multipliers = {"positive": 1.5, "neutral": 1.0, "negative": 0.3}

        total_score = 0.0
        tier_counts = Counter()

        for mention in mentions:
            tier = mention.get("tier", 5)
            sentiment = mention.get("sentiment", "neutral")
            weight = tier_weights.get(tier, 1.0)
            multiplier = sentiment_multipliers.get(sentiment, 1.0)
            total_score += weight * multiplier
            tier_counts[tier] += 1

        return {
            "total_mentions": len(mentions),
            "media_impact_score": round(total_score, 1),
            "by_tier": {
                "national": tier_counts.get(1, 0),
                "regional": tier_counts.get(2, 0),
                "local": tier_counts.get(3, 0),
                "trade": tier_counts.get(4, 0),
                "blog": tier_counts.get(5, 0),
            },
        }

    def track_corporate_response(
        self, responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Track and score corporate responses to campaign pressure.

        Args:
            responses: List of dicts with keys:
                - date: str
                - type: str ("no_response", "form_letter", "meeting_offer",
                             "partial_commitment", "full_commitment",
                             "public_statement", "policy_change")
                - details: str

        Returns:
            Response analysis summary
        """
        response_scores = {
            "no_response": 0,
            "form_letter": 1,
            "meeting_offer": 3,
            "partial_commitment": 5,
            "public_statement": 4,
            "full_commitment": 8,
            "policy_change": 10,
        }

        if not responses:
            return {"total_responses": 0, "engagement_score": 0, "trajectory": "none"}

        scores = [
            response_scores.get(r.get("type", "no_response"), 0) for r in responses
        ]

        # Trajectory: are responses improving over time?
        if len(scores) >= 2:
            if scores[-1] > scores[0]:
                trajectory = "improving"
            elif scores[-1] < scores[0]:
                trajectory = "degrading"
            else:
                trajectory = "flat"
        else:
            trajectory = "insufficient_data"

        return {
            "total_responses": len(responses),
            "engagement_score": round(sum(scores) / len(scores), 1),
            "best_response": max(scores),
            "trajectory": trajectory,
            "latest_response_type": responses[-1].get("type", "unknown"),
        }
