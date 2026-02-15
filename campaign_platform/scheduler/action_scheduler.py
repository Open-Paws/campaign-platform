"""
Action Scheduler - Coordinate timing for maximum impact.

Key principles:
1. Stagger emails so targets do not receive 500 identical emails at once
   (which get dismissed as a form campaign). Instead, deliver a sustained
   stream that shows ongoing constituent concern.
2. Coordinate social media bursts so posts arrive simultaneously for
   trending potential.
3. Sequence escalation so each phase builds on the previous one's pressure.
4. Respect volunteer capacity -- do not burn out your people.
"""

from datetime import datetime, date, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random


class ScheduleStrategy(str, Enum):
    """How to distribute actions over time."""
    STAGGER = "stagger"       # Spread evenly over window (emails, calls)
    BURST = "burst"           # Concentrate in short window (social media)
    ESCALATE = "escalate"     # Increasing intensity over time
    SUSTAIN = "sustain"       # Steady pace, long duration
    DEADLINE = "deadline"     # Ramp up as deadline approaches


@dataclass
class ScheduledAction:
    """An action with its scheduled execution window."""
    action_id: int
    action_type: str
    scheduled_start: datetime
    scheduled_end: datetime
    priority: int
    batch_id: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class ScheduleWindow:
    """A time window for scheduling actions."""
    start: datetime
    end: datetime
    peak_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 14, 15, 19, 20])
    # Peak hours: morning (9-11), early afternoon (2-3), evening (7-8)
    blocked_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6, 22, 23])
    # Do not schedule between 10pm and 7am
    timezone_offset: int = 0  # Offset from UTC for target's timezone


class ActionScheduler:
    """Schedule and coordinate campaign actions for maximum impact."""

    def schedule_email_campaign(
        self,
        action_ids: List[int],
        window: ScheduleWindow,
        emails_per_day: int = 20,
        stagger_minutes: int = 15,
        personalization_required: bool = True,
    ) -> List[ScheduledAction]:
        """
        Schedule emails to arrive as a sustained stream, not a flood.

        Why stagger: Targets (CEOs, legislators, regulators) and their staff
        can dismiss a flood of identical emails received in one hour as an
        organized campaign. A steady stream over days/weeks demonstrates
        genuine, ongoing concern from multiple individuals.

        Args:
            action_ids: Email action IDs to schedule
            window: Time window for the campaign
            emails_per_day: Target emails per business day
            stagger_minutes: Minimum minutes between emails
            personalization_required: If True, add reminder to personalize

        Returns:
            Scheduled actions with staggered send times
        """
        scheduled = []
        current_date = window.start.date()
        daily_count = 0
        current_time = self._next_business_hour(window.start, window)

        for i, action_id in enumerate(action_ids):
            if current_date > window.end.date():
                # Wrap around or stop
                break

            # Skip weekends for email campaigns
            while current_time.weekday() >= 5:  # Saturday=5, Sunday=6
                current_time = datetime.combine(
                    current_time.date() + timedelta(days=1),
                    time(9, 0),
                )

            scheduled_action = ScheduledAction(
                action_id=action_id,
                action_type="email",
                scheduled_start=current_time,
                scheduled_end=current_time + timedelta(hours=1),
                priority=max(1, 5 - (i // emails_per_day)),  # Earlier batches = higher priority
                batch_id=f"email-batch-{current_date.isoformat()}",
                notes=(
                    "IMPORTANT: Personalize this email. Do not send the template verbatim. "
                    "Add your personal connection, specific local knowledge, or professional "
                    "expertise. Personalized emails are 10x more effective."
                    if personalization_required
                    else None
                ),
            )
            scheduled.append(scheduled_action)

            # Advance time
            daily_count += 1
            if daily_count >= emails_per_day:
                # Move to next business day
                current_date += timedelta(days=1)
                daily_count = 0
                current_time = datetime.combine(
                    current_date,
                    time(9, random.randint(0, 30)),
                )
            else:
                current_time += timedelta(minutes=stagger_minutes + random.randint(0, 10))
                # If past business hours, roll to next day
                if current_time.hour >= 18:
                    current_date += timedelta(days=1)
                    current_time = datetime.combine(
                        current_date,
                        time(9, random.randint(0, 30)),
                    )

        return scheduled

    def schedule_social_burst(
        self,
        action_ids: List[int],
        burst_time: datetime,
        pre_burst_minutes: int = 5,
        platform: str = "twitter",
    ) -> List[ScheduledAction]:
        """
        Coordinate a social media burst -- all posts within a tight window.

        Why burst: Social media algorithms favor topics with sudden spikes
        in volume. Coordinated posting within a 5-15 minute window maximizes
        the chance of trending and algorithmic amplification.

        Args:
            action_ids: Social post action IDs
            burst_time: Central time for the burst
            pre_burst_minutes: Window before burst_time to start
            platform: Target platform for timing optimization

        Returns:
            Scheduled actions clustered around burst_time
        """
        scheduled = []

        # Optimal posting windows by platform
        platform_windows = {
            "twitter": 10,   # 10-minute window for Twitter trending
            "instagram": 15,  # 15-minute window for Instagram feed
            "tiktok": 20,    # 20-minute window for TikTok algorithm
            "linkedin": 30,  # 30-minute window for LinkedIn feed
        }
        window_minutes = platform_windows.get(platform, 15)

        # Distribute posts across the burst window
        burst_start = burst_time - timedelta(minutes=pre_burst_minutes)
        interval = window_minutes / max(len(action_ids), 1)

        for i, action_id in enumerate(action_ids):
            post_time = burst_start + timedelta(minutes=interval * i)
            scheduled.append(ScheduledAction(
                action_id=action_id,
                action_type="social_post",
                scheduled_start=post_time,
                scheduled_end=post_time + timedelta(minutes=5),
                priority=1,  # All burst posts are high priority
                batch_id=f"social-burst-{burst_time.isoformat()}",
                notes=(
                    f"POST AT EXACTLY {post_time.strftime('%H:%M')}. "
                    f"This is a coordinated action -- timing matters for trending. "
                    f"After posting: engage with replies for 15 minutes to boost algorithm."
                ),
            ))

        return scheduled

    def schedule_phone_bank(
        self,
        action_ids: List[int],
        window: ScheduleWindow,
        calls_per_hour: int = 10,
        target_timezone: str = "US/Eastern",
    ) -> List[ScheduledAction]:
        """
        Schedule phone calls during business hours in the target's timezone.

        Why schedule: Congressional and corporate offices track call volume
        by day. Spreading calls across multiple days shows sustained concern.
        Clustering calls on specific days (e.g., vote day) shows intensity.

        Args:
            action_ids: Phone call action IDs
            window: Overall campaign window
            calls_per_hour: Target calls per hour per office
            target_timezone: Timezone of the target's office
        """
        scheduled = []
        # Business calling hours: 9am-5pm target timezone
        calling_start_hour = 9
        calling_end_hour = 17

        current_time = window.start
        if current_time.hour < calling_start_hour:
            current_time = current_time.replace(hour=calling_start_hour, minute=0)

        for action_id in action_ids:
            # Skip non-business hours
            while (
                current_time.hour < calling_start_hour
                or current_time.hour >= calling_end_hour
                or current_time.weekday() >= 5
            ):
                if current_time.hour >= calling_end_hour or current_time.weekday() >= 5:
                    # Move to next business day
                    next_day = current_time.date() + timedelta(days=1)
                    current_time = datetime.combine(next_day, time(calling_start_hour, 0))
                else:
                    current_time = current_time.replace(hour=calling_start_hour, minute=0)

            if current_time > window.end:
                break

            interval_minutes = 60 // max(calls_per_hour, 1)
            scheduled.append(ScheduledAction(
                action_id=action_id,
                action_type="phone_call",
                scheduled_start=current_time,
                scheduled_end=current_time + timedelta(minutes=10),
                priority=2,
                batch_id=f"calls-{current_time.date().isoformat()}",
                notes=(
                    f"Call during business hours ({calling_start_hour}am-"
                    f"{calling_end_hour - 12}pm {target_timezone}). "
                    f"If voicemail, leave message and count it."
                ),
            ))

            current_time += timedelta(minutes=interval_minutes)

        return scheduled

    def schedule_escalation_sequence(
        self,
        phases: List[Dict[str, Any]],
        campaign_start: date,
        actions_per_phase: Dict[int, List[int]],
    ) -> List[ScheduledAction]:
        """
        Schedule an escalation ladder -- each phase starts when the previous
        phase's window closes (or win condition is met).

        The escalation pattern:
        Phase 1: Direct engagement (low-cost, high-volume)
        Phase 2: Public pressure (medium-cost, medium-volume)
        Phase 3: Institutional pressure (high-cost, targeted)
        Phase 4: Maximum pressure (legal, financial, reputational)

        Args:
            phases: Campaign escalation phases from CampaignBuilder
            campaign_start: Campaign start date
            actions_per_phase: Dict mapping phase number to action IDs

        Returns:
            All actions scheduled across the full escalation timeline
        """
        all_scheduled = []
        phase_start = campaign_start

        for phase in phases:
            phase_num = phase["phase"]
            duration_weeks = phase["duration_weeks"]
            phase_actions = actions_per_phase.get(phase_num, [])

            if not phase_actions:
                phase_start = phase_start + timedelta(weeks=duration_weeks)
                continue

            phase_end = phase_start + timedelta(weeks=duration_weeks)
            window = ScheduleWindow(
                start=datetime.combine(phase_start, time(9, 0)),
                end=datetime.combine(phase_end, time(17, 0)),
            )

            # Distribute actions across the phase window
            days_in_phase = max(1, (phase_end - phase_start).days)
            actions_per_day = max(1, len(phase_actions) // days_in_phase)

            current_date = phase_start
            action_idx = 0

            for day_offset in range(days_in_phase):
                current_date = phase_start + timedelta(days=day_offset)
                if current_date.weekday() >= 5:  # Skip weekends
                    continue

                daily_actions = phase_actions[action_idx:action_idx + actions_per_day]
                action_idx += len(daily_actions)

                for j, action_id in enumerate(daily_actions):
                    action_time = datetime.combine(
                        current_date,
                        time(9 + (j % 8), random.randint(0, 59)),
                    )
                    all_scheduled.append(ScheduledAction(
                        action_id=action_id,
                        action_type="mixed",
                        scheduled_start=action_time,
                        scheduled_end=action_time + timedelta(hours=2),
                        priority=phase_num,
                        batch_id=f"phase-{phase_num}-{current_date.isoformat()}",
                        notes=f"Escalation Phase {phase_num}: {phase['name']}",
                    ))

                if action_idx >= len(phase_actions):
                    break

            phase_start = phase_end

        return all_scheduled

    def schedule_comment_period(
        self,
        action_ids: List[int],
        comment_deadline: datetime,
        ramp_up_days: int = 14,
    ) -> List[ScheduledAction]:
        """
        Schedule regulatory comments with a ramp-up pattern toward deadline.

        Pattern: Slow start (agency sees early substantive comments), then
        increasing volume as deadline approaches (demonstrates public concern).

        The most impactful comments are early (they shape agency thinking)
        and late (they show sustained interest). The middle is less important.

        Args:
            action_ids: Comment action IDs
            comment_deadline: Regulatory comment deadline
            ramp_up_days: Days before deadline to begin ramp-up
        """
        scheduled = []
        total = len(action_ids)
        if total == 0:
            return scheduled

        # Split: 20% early, 20% middle, 60% in final ramp-up
        early_count = max(1, int(total * 0.2))
        middle_count = max(1, int(total * 0.2))
        ramp_count = total - early_count - middle_count

        # Total campaign window: 6 weeks before deadline
        campaign_start = comment_deadline - timedelta(weeks=6)
        ramp_start = comment_deadline - timedelta(days=ramp_up_days)

        idx = 0

        # Early comments (first 2 weeks)
        for i in range(early_count):
            day_offset = int((14 / max(early_count, 1)) * i)
            comment_time = campaign_start + timedelta(days=day_offset, hours=10)
            scheduled.append(ScheduledAction(
                action_id=action_ids[idx],
                action_type="public_comment",
                scheduled_start=comment_time,
                scheduled_end=comment_time + timedelta(hours=2),
                priority=2,  # Early comments are high priority (set the tone)
                batch_id="comment-early",
                notes=(
                    "EARLY COMMENT: Your comment will help shape the agency's "
                    "initial framing. Be thorough and cite primary sources. "
                    "This is the most impactful timing for substantive comments."
                ),
            ))
            idx += 1

        # Middle comments (weeks 3-4)
        middle_start = campaign_start + timedelta(weeks=2)
        for i in range(middle_count):
            day_offset = int((14 / max(middle_count, 1)) * i)
            comment_time = middle_start + timedelta(days=day_offset, hours=14)
            scheduled.append(ScheduledAction(
                action_id=action_ids[idx],
                action_type="public_comment",
                scheduled_start=comment_time,
                scheduled_end=comment_time + timedelta(hours=2),
                priority=5,
                batch_id="comment-middle",
                notes="Sustain comment flow. Cite new evidence or different angles.",
            ))
            idx += 1

        # Ramp-up comments (final 2 weeks, exponential increase)
        for i in range(ramp_count):
            # Exponential distribution: more comments closer to deadline
            fraction = (i / max(ramp_count - 1, 1)) ** 2  # quadratic ramp
            day_offset = int(fraction * (ramp_up_days - 1))  # -1 to stay before deadline
            comment_time = ramp_start + timedelta(days=day_offset, hours=random.randint(9, 16))
            scheduled.append(ScheduledAction(
                action_id=action_ids[idx],
                action_type="public_comment",
                scheduled_start=comment_time,
                scheduled_end=comment_time + timedelta(hours=2),
                priority=3,
                batch_id="comment-rampup",
                notes=(
                    "DEADLINE PUSH: Volume matters now. Ensure your comment is "
                    "still unique and substantive, but prioritize submission over "
                    "perfection. Filed is better than perfect-but-missed."
                ),
            ))
            idx += 1

        return scheduled

    @staticmethod
    def _next_business_hour(dt: datetime, window: ScheduleWindow) -> datetime:
        """Advance to the next valid business hour within the schedule window."""
        result = dt
        while (
            result.hour in window.blocked_hours
            or result.weekday() >= 5
        ):
            if result.weekday() >= 5:
                days_until_monday = 7 - result.weekday()
                result = datetime.combine(
                    result.date() + timedelta(days=days_until_monday),
                    time(9, 0),
                )
            else:
                result = datetime.combine(
                    result.date() + timedelta(days=1),
                    time(9, 0),
                )
        return result

    def get_schedule_summary(
        self, scheduled_actions: List[ScheduledAction]
    ) -> Dict[str, Any]:
        """Get a summary of a schedule for review."""
        if not scheduled_actions:
            return {"total": 0}

        by_date = {}
        by_type = {}
        by_batch = {}

        for sa in scheduled_actions:
            date_key = sa.scheduled_start.date().isoformat()
            by_date[date_key] = by_date.get(date_key, 0) + 1
            by_type[sa.action_type] = by_type.get(sa.action_type, 0) + 1
            if sa.batch_id:
                by_batch[sa.batch_id] = by_batch.get(sa.batch_id, 0) + 1

        dates = [sa.scheduled_start for sa in scheduled_actions]
        return {
            "total": len(scheduled_actions),
            "start": min(dates).isoformat(),
            "end": max(dates).isoformat(),
            "duration_days": (max(dates) - min(dates)).days,
            "by_date": by_date,
            "by_type": by_type,
            "by_batch": by_batch,
            "peak_date": max(by_date, key=by_date.get),
            "peak_count": max(by_date.values()),
        }
