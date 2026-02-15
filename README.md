# Campaign Coordination Platform

Coordinate campaigns. Multiply impact. Every volunteer gets the right action at the right time.

## What This Does

Most advocacy campaigns waste volunteer potential. They send everyone the same form email, or they ask for hours of commitment from people who only have five minutes. This platform fixes that.

**For volunteers**: Tell us how much time you have. Get exactly the right action -- with a script, a template, and clear instructions. Five minutes? Here is a phone script. Thirty minutes? Here is a public comment template with the evidence you need. Two hours? Here is a FOIA request ready to file.

**For organizers**: Build campaigns from proven escalation templates. Track which actions are working. Shift resources from low-impact to high-impact activities. See real-time progress across every channel.

## Campaign Types

- **Corporate** -- Multi-channel pressure: email, social, shareholder, consumer, media. Four-phase escalation from direct engagement to maximum pressure.
- **Legislative** -- Move bills: constituent calls, coalition building, floor push. Phone scripts and testimony templates.
- **Regulatory** -- Shape rulemaking: public comments, FOIA, enforcement push, citizen suits. Substantive comment templates that agencies must address.
- **Investigation** -- Build evidence: OSINT, FOIA, satellite analysis, whistleblower outreach. Feed findings into other campaign types.
- **Cultural** -- Shift narratives: SEO content, social media, influencer outreach, long-form media. Own the search results.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# CLI
campaign types                    # List campaign types
campaign create \
  --name "Example Campaign" \
  --type corporate \
  --target "Target Corp" \
  --goal "Commitment to phase out practice X by 2027"
campaign actions --campaign-id 1 --minutes 15
campaign track --campaign-id 1

# API server
uvicorn platform.dashboard.api:app --reload

# Docker
docker build -t campaign-platform .
docker run -p 8000:8000 -v campaign-data:/data campaign-platform
```

## Architecture

```
platform/
  campaigns/
    models.py            # SQLAlchemy: Campaign, Action, Target, Participant
    campaign_builder.py  # Templates with escalation ladders
    action_generator.py  # Right-sized actions by time available
  templates/
    email_templates/     # CEO letters, IR inquiries, public comments
    phone_scripts/       # Congressional calls, corporate consumer lines
    social_templates/    # Twitter threads, Instagram posts
    review_templates/    # Factual Google reviews
  dashboard/
    api.py               # FastAPI CRUD + progress tracking
    frontend.html        # Campaign dashboard
  metrics/
    impact_tracker.py    # Emails, calls, comments, media, responses
    roi_calculator.py    # Volunteer hours vs. outcomes
  integrations/
    violation_db.py      # Pull from factory farm violation database
  scheduler/
    action_scheduler.py  # Stagger emails, coordinate social bursts
  cli.py                 # Click CLI for all operations
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard |
| POST | `/api/campaigns` | Create campaign |
| GET | `/api/campaigns` | List campaigns |
| GET | `/api/campaigns/{id}` | Get campaign |
| PATCH | `/api/campaigns/{id}` | Update campaign |
| GET | `/api/campaigns/{id}/progress` | Progress metrics |
| POST | `/api/actions` | Create action |
| GET | `/api/actions` | List/filter actions |
| POST | `/api/actions/{id}/claim` | Claim an action |
| POST | `/api/actions/{id}/complete` | Mark completed |
| POST | `/api/actions/{id}/verify` | Verify completion |
| POST | `/api/actions/suggest` | Get actions for time |
| POST | `/api/targets` | Add target |
| GET | `/api/targets` | List targets |
| POST | `/api/participants` | Register volunteer |
| GET | `/api/participants` | List volunteers |
| GET | `/api/metrics/{id}` | Impact metrics |
| GET | `/api/metrics/{id}/roi` | ROI analysis |

## Design Principles

1. **Right action, right time** -- Match actions to available time. A five-minute phone call counts.
2. **Evidence-based templates** -- Every template is built on real persuasion research. Personalized emails outperform form letters 10:1. Substantive regulatory comments must be addressed. Phone calls are logged and reported.
3. **Escalation ladders** -- Start low-cost, high-volume. Escalate to high-impact, targeted. Each phase builds on the last.
4. **Measure what matters** -- Track outputs (emails sent) and outcomes (corporate responses). Calculate ROI. Shift resources to what works.
5. **Scheduling intelligence** -- Stagger emails for sustained pressure. Burst social posts for trending. Ramp comments toward deadlines.
