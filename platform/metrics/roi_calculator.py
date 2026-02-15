"""
ROI Calculator - Measure campaign efficiency.

Core question: For every hour of volunteer time invested, what did we achieve?

This matters because volunteer time is the scarcest resource. Every wasted
hour is an hour that could have saved a life. We owe it to both the volunteers
and the animals to optimize relentlessly.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import Counter

from platform.campaigns.models import (
    Campaign,
    Action,
    ActionType,
    ActionStatus,
)


class ROICalculator:
    """Calculate return on investment for campaign activities."""

    # Estimated dollar-equivalent value of outcomes
    # Based on: cost to achieve similar outcomes via paid channels
    OUTCOME_VALUES: Dict[str, float] = {
        "email_to_target": 5.0,        # vs. hiring a letter-writing service
        "phone_call_logged": 15.0,     # high-impact, hard to replicate at scale
        "public_comment_filed": 50.0,  # professional comment prep costs $200+
        "foia_request_filed": 200.0,   # paralegal rates for FOIA prep
        "review_posted": 10.0,         # reputation management baseline
        "testimony_given": 500.0,      # expert witness rates as benchmark
        "media_mention_earned": 1000.0,  # equivalent ad buy for reach
        "shareholder_action": 2000.0,  # proxy advisory firm engagement cost
        "corporate_response": 5000.0,  # signal that pressure is working
        "policy_change": 50000.0,      # the whole point
        "social_post_engagement": 2.0, # CPM equivalent
    }

    # Time cost per action type (in hours), used when actual data unavailable
    ESTIMATED_HOURS: Dict[ActionType, float] = {
        ActionType.PHONE_CALL: 0.1,
        ActionType.EMAIL: 0.25,
        ActionType.SOCIAL_POST: 0.2,
        ActionType.PUBLIC_COMMENT: 0.5,
        ActionType.FOIA_REQUEST: 2.0,
        ActionType.REVIEW: 0.25,
        ActionType.TESTIMONY: 2.0,
        ActionType.SHAREHOLDER_ACTION: 4.0,
        ActionType.BOYCOTT: 0.25,
        ActionType.CONTENT_CREATION: 2.0,
        ActionType.SEO_ARTICLE: 3.0,
        ActionType.OSINT_RESEARCH: 4.0,
        ActionType.SATELLITE_ANALYSIS: 3.0,
        ActionType.CITIZEN_SUIT: 8.0,
    }

    def calculate_campaign_roi(
        self,
        campaign: Campaign,
        actions: List[Action],
        outcomes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate ROI for a campaign.

        Args:
            campaign: The campaign
            actions: All actions in the campaign
            outcomes: Optional list of outcome records:
                [{"type": "corporate_response", "value_override": 5000}, ...]

        Returns:
            ROI analysis with efficiency metrics
        """
        completed = [
            a for a in actions
            if a.status in (ActionStatus.COMPLETED, ActionStatus.VERIFIED)
        ]

        # Total volunteer hours invested
        total_hours = sum(
            a.estimated_minutes / 60.0 for a in completed
        )

        # Value of completed actions
        action_value = 0.0
        action_type_map = {
            ActionType.EMAIL: "email_to_target",
            ActionType.PHONE_CALL: "phone_call_logged",
            ActionType.PUBLIC_COMMENT: "public_comment_filed",
            ActionType.FOIA_REQUEST: "foia_request_filed",
            ActionType.REVIEW: "review_posted",
            ActionType.TESTIMONY: "testimony_given",
            ActionType.SHAREHOLDER_ACTION: "shareholder_action",
            ActionType.SOCIAL_POST: "social_post_engagement",
        }

        type_values = Counter()
        for a in completed:
            outcome_key = action_type_map.get(ActionType(a.action_type))
            if outcome_key:
                val = self.OUTCOME_VALUES.get(outcome_key, 5.0)
                action_value += val
                type_values[a.action_type] += val
            else:
                action_value += 5.0  # minimum value for any completed action
                type_values[a.action_type] += 5.0

        # Add explicit outcome values
        outcome_value = 0.0
        if outcomes:
            for outcome in outcomes:
                val = outcome.get(
                    "value_override",
                    self.OUTCOME_VALUES.get(outcome.get("type", ""), 0),
                )
                outcome_value += val

        total_value = action_value + outcome_value

        # ROI calculation
        # Using volunteer time valued at $30/hr (nonprofit volunteer equivalent)
        volunteer_hour_value = 30.0
        total_cost = total_hours * volunteer_hour_value
        roi_pct = (
            round((total_value - total_cost) / max(total_cost, 1) * 100, 1)
        )

        # Value per hour
        value_per_hour = round(total_value / max(total_hours, 0.1), 2)

        # Efficiency by action type
        type_efficiency = {}
        type_hours = Counter()
        for a in completed:
            type_hours[a.action_type] += a.estimated_minutes / 60.0

        for atype in type_values:
            hours = type_hours.get(atype, 0.1)
            type_efficiency[atype] = {
                "hours_invested": round(hours, 1),
                "value_generated": round(type_values[atype], 2),
                "value_per_hour": round(type_values[atype] / max(hours, 0.1), 2),
            }

        # Sort by efficiency
        ranked_types = sorted(
            type_efficiency.items(),
            key=lambda x: x[1]["value_per_hour"],
            reverse=True,
        )

        # Time allocation analysis
        total_possible_hours = sum(
            a.estimated_minutes / 60.0 for a in actions
        )
        time_utilization = (
            round(total_hours / total_possible_hours * 100, 1)
            if total_possible_hours > 0
            else 0.0
        )

        # Wasted time (overdue + expired unclaimed)
        wasted_actions = [
            a for a in actions
            if a.status == ActionStatus.EXPIRED
            or (a.is_overdue and a.status not in (ActionStatus.COMPLETED, ActionStatus.VERIFIED))
        ]
        wasted_hours = sum(a.estimated_minutes / 60.0 for a in wasted_actions)

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "investment": {
                "total_volunteer_hours": round(total_hours, 1),
                "total_actions_completed": len(completed),
                "total_actions_available": len(actions),
                "time_utilization_pct": time_utilization,
                "wasted_hours": round(wasted_hours, 1),
                "cost_equivalent": round(total_cost, 2),
            },
            "returns": {
                "action_value": round(action_value, 2),
                "outcome_value": round(outcome_value, 2),
                "total_value": round(total_value, 2),
            },
            "efficiency": {
                "roi_pct": roi_pct,
                "value_per_volunteer_hour": value_per_hour,
                "most_efficient_action": (
                    ranked_types[0][0] if ranked_types else None
                ),
                "least_efficient_action": (
                    ranked_types[-1][0] if ranked_types else None
                ),
            },
            "type_breakdown": {
                atype: data for atype, data in ranked_types
            },
            "recommendations": self._generate_recommendations(
                type_efficiency, total_hours, len(completed), len(actions)
            ),
        }

    def _generate_recommendations(
        self,
        type_efficiency: Dict,
        total_hours: float,
        completed_count: int,
        total_count: int,
    ) -> List[str]:
        """Generate actionable recommendations from ROI data."""
        recs = []

        if total_count > 0 and completed_count / total_count < 0.3:
            recs.append(
                "Low completion rate. Consider reducing action count and "
                "increasing urgency signals (deadlines, progress bars)."
            )

        if type_efficiency:
            # Find highest and lowest efficiency types
            sorted_types = sorted(
                type_efficiency.items(),
                key=lambda x: x[1]["value_per_hour"],
                reverse=True,
            )
            if len(sorted_types) >= 2:
                best = sorted_types[0]
                worst = sorted_types[-1]
                if best[1]["value_per_hour"] > worst[1]["value_per_hour"] * 3:
                    recs.append(
                        f"Shift volunteer hours from {worst[0]} "
                        f"(${worst[1]['value_per_hour']}/hr) toward {best[0]} "
                        f"(${best[1]['value_per_hour']}/hr) for 3x+ efficiency gain."
                    )

        if total_hours > 0 and completed_count / max(total_hours, 1) < 1:
            recs.append(
                "Actions are taking longer than estimated. Review templates "
                "and provide more scaffolding to reduce time-per-action."
            )

        if not recs:
            recs.append(
                "Campaign is running efficiently. Consider scaling up "
                "the highest-performing action types."
            )

        return recs

    def project_impact(
        self,
        campaign: Campaign,
        actions: List[Action],
        additional_hours: float,
        focus_type: Optional[ActionType] = None,
    ) -> Dict[str, Any]:
        """
        Project what additional volunteer hours could achieve.

        Args:
            campaign: The campaign
            actions: Current actions
            additional_hours: Hours available to invest
            focus_type: Optional focus on a specific action type

        Returns:
            Projected impact if hours are invested
        """
        completed = [
            a for a in actions
            if a.status in (ActionStatus.COMPLETED, ActionStatus.VERIFIED)
        ]

        if focus_type:
            hours_per = self.ESTIMATED_HOURS.get(focus_type, 0.5)
            projected_actions = int(additional_hours / hours_per)
            action_type_map = {
                ActionType.EMAIL: "email_to_target",
                ActionType.PHONE_CALL: "phone_call_logged",
                ActionType.PUBLIC_COMMENT: "public_comment_filed",
                ActionType.FOIA_REQUEST: "foia_request_filed",
                ActionType.REVIEW: "review_posted",
                ActionType.TESTIMONY: "testimony_given",
                ActionType.SHAREHOLDER_ACTION: "shareholder_action",
                ActionType.SOCIAL_POST: "social_post_engagement",
            }
            outcome_key = action_type_map.get(focus_type, "email_to_target")
            projected_value = projected_actions * self.OUTCOME_VALUES.get(outcome_key, 5.0)
        else:
            # Distribute hours across current campaign action types
            if completed:
                type_distribution = Counter(a.action_type for a in completed)
                total = sum(type_distribution.values())
                projected_actions = 0
                projected_value = 0.0
                for atype, count in type_distribution.items():
                    share = count / total
                    type_hours = additional_hours * share
                    hours_per = self.ESTIMATED_HOURS.get(ActionType(atype), 0.5)
                    actions_count = int(type_hours / hours_per)
                    projected_actions += actions_count
                    action_type_map = {
                        ActionType.EMAIL: "email_to_target",
                        ActionType.PHONE_CALL: "phone_call_logged",
                        ActionType.PUBLIC_COMMENT: "public_comment_filed",
                    }
                    outcome_key = action_type_map.get(ActionType(atype), "email_to_target")
                    projected_value += actions_count * self.OUTCOME_VALUES.get(outcome_key, 5.0)
            else:
                projected_actions = int(additional_hours / 0.5)
                projected_value = projected_actions * 5.0

        return {
            "additional_hours": additional_hours,
            "focus_type": focus_type.value if focus_type else "distributed",
            "projected_additional_actions": projected_actions,
            "projected_additional_value": round(projected_value, 2),
            "projected_new_total_actions": len(completed) + projected_actions,
        }
