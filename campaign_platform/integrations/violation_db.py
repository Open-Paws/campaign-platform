"""
Violation Database Integration - Pull from factory-farm-api for campaign targeting.

Connects to the factory farm violation/facility API to identify:
- Facilities with repeat violations
- Companies with the worst compliance records
- Geographic clusters of violations for local campaigns
- Recent inspection failures for timely campaign launches

This data feeds directly into campaign targeting -- the worst offenders
become the highest-priority targets.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import httpx


@dataclass
class Violation:
    """A single violation record from the database."""
    id: str
    facility_id: str
    facility_name: str
    company: str
    violation_type: str
    severity: str  # "critical", "major", "minor"
    description: str
    date: date
    inspector: Optional[str] = None
    statute: Optional[str] = None
    fine_amount: Optional[float] = None
    corrective_action: Optional[str] = None
    status: str = "open"  # "open", "resolved", "contested"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    state: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class Facility:
    """A facility with its violation history."""
    id: str
    name: str
    company: str
    facility_type: str  # "cafo", "slaughterhouse", "processing", "feedlot"
    address: str
    state: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    animal_count: Optional[int] = None
    species: Optional[List[str]] = None
    permits: Optional[List[str]] = None
    violations: List[Violation] = field(default_factory=list)
    violation_count: int = 0
    last_inspection: Optional[date] = None
    compliance_score: Optional[float] = None  # 0-100, lower = worse


class ViolationDBClient:
    """
    Client for the factory farm violation/facility database API.

    Pulls violation data to identify campaign targets and provide
    evidence for campaign materials.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    # --- Violation Queries ---

    async def get_violations(
        self,
        company: Optional[str] = None,
        state: Optional[str] = None,
        severity: Optional[str] = None,
        since: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Violation]:
        """
        Query violations with filters.

        Args:
            company: Filter by company name (partial match)
            state: Filter by state code (e.g., "NC", "IA")
            severity: Filter by severity ("critical", "major", "minor")
            since: Only violations after this date
            limit: Max results
            offset: Pagination offset

        Returns:
            List of Violation records
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if company:
            params["company"] = company
        if state:
            params["state"] = state
        if severity:
            params["severity"] = severity
        if since:
            params["since"] = since.isoformat()

        response = await self.client.get("/api/violations", params=params)
        response.raise_for_status()
        data = response.json()

        return [self._parse_violation(v) for v in data.get("violations", [])]

    async def get_repeat_offenders(
        self,
        min_violations: int = 5,
        period_months: int = 24,
        state: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get companies/facilities with the most violations.

        These are prime campaign targets -- repeat offenders demonstrate
        systemic problems, not one-off failures.

        Args:
            min_violations: Minimum violation count to include
            period_months: Look-back period in months
            state: Optional state filter

        Returns:
            List of offender summaries sorted by violation count
        """
        since = date.today() - timedelta(days=period_months * 30)
        params = {
            "min_violations": min_violations,
            "since": since.isoformat(),
        }
        if state:
            params["state"] = state

        response = await self.client.get("/api/violations/repeat-offenders", params=params)
        response.raise_for_status()
        return response.json().get("offenders", [])

    async def get_recent_critical(
        self,
        days: int = 30,
        state: Optional[str] = None,
    ) -> List[Violation]:
        """
        Get recent critical violations -- opportunities for timely campaigns.

        Recent critical violations are ideal for campaign launches because:
        - They are newsworthy (recency)
        - They demonstrate current harm (not historical)
        - Regulators may be receptive to complaints
        """
        since = date.today() - timedelta(days=days)
        return await self.get_violations(
            severity="critical",
            since=since,
            state=state,
            limit=50,
        )

    # --- Facility Queries ---

    async def get_facility(self, facility_id: str) -> Optional[Facility]:
        """Get detailed facility information including violation history."""
        response = await self.client.get(f"/api/facilities/{facility_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return self._parse_facility(response.json())

    async def search_facilities(
        self,
        company: Optional[str] = None,
        state: Optional[str] = None,
        facility_type: Optional[str] = None,
        species: Optional[str] = None,
        max_compliance_score: Optional[float] = None,
        limit: int = 50,
    ) -> List[Facility]:
        """
        Search facilities with filters.

        Use max_compliance_score to find the worst facilities:
        - Score < 30: Severe compliance issues
        - Score 30-60: Moderate issues
        - Score > 60: Relatively compliant
        """
        params: Dict[str, Any] = {"limit": limit}
        if company:
            params["company"] = company
        if state:
            params["state"] = state
        if facility_type:
            params["facility_type"] = facility_type
        if species:
            params["species"] = species
        if max_compliance_score is not None:
            params["max_compliance_score"] = max_compliance_score

        response = await self.client.get("/api/facilities", params=params)
        response.raise_for_status()
        data = response.json()

        return [self._parse_facility(f) for f in data.get("facilities", [])]

    async def get_facilities_near(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float = 50.0,
        limit: int = 20,
    ) -> List[Facility]:
        """Find facilities near a location -- for community organizing."""
        params = {
            "lat": latitude,
            "lon": longitude,
            "radius": radius_miles,
            "limit": limit,
        }
        response = await self.client.get("/api/facilities/nearby", params=params)
        response.raise_for_status()
        data = response.json()
        return [self._parse_facility(f) for f in data.get("facilities", [])]

    # --- Campaign Targeting ---

    async def build_target_profile(
        self, company: str
    ) -> Dict[str, Any]:
        """
        Build a comprehensive target profile for a company.

        Aggregates all available data into a campaign-ready profile:
        - Violation history and patterns
        - Facility locations
        - Vulnerability assessment
        - Suggested campaign angles
        """
        facilities = await self.search_facilities(company=company, limit=100)
        violations = await self.get_violations(company=company, limit=500)

        # Aggregate statistics
        total_violations = len(violations)
        critical_violations = len([v for v in violations if v.severity == "critical"])
        states_operating = list(set(f.state for f in facilities if f.state))
        total_animals = sum(f.animal_count or 0 for f in facilities)

        # Violation trends
        recent_violations = [
            v for v in violations
            if v.date >= date.today() - timedelta(days=365)
        ]
        older_violations = [
            v for v in violations
            if v.date < date.today() - timedelta(days=365)
        ]

        trend = "unknown"
        if recent_violations and older_violations:
            if len(recent_violations) > len(older_violations):
                trend = "worsening"
            elif len(recent_violations) < len(older_violations):
                trend = "improving"
            else:
                trend = "stable"

        # Vulnerability score (higher = more vulnerable to campaign pressure)
        vulnerability = self._calculate_vulnerability(
            total_violations=total_violations,
            critical_count=critical_violations,
            facility_count=len(facilities),
            states=states_operating,
            trend=trend,
        )

        # Suggested campaign angles
        angles = self._suggest_campaign_angles(
            violations=violations,
            facilities=facilities,
            vulnerability=vulnerability,
        )

        return {
            "company": company,
            "facilities": len(facilities),
            "states": states_operating,
            "total_animals": total_animals,
            "violations": {
                "total": total_violations,
                "critical": critical_violations,
                "recent_12mo": len(recent_violations),
                "trend": trend,
            },
            "vulnerability_score": vulnerability,
            "suggested_campaign_angles": angles,
            "worst_facilities": sorted(
                [
                    {
                        "id": f.id,
                        "name": f.name,
                        "state": f.state,
                        "compliance_score": f.compliance_score,
                        "violation_count": f.violation_count,
                    }
                    for f in facilities
                ],
                key=lambda x: x.get("compliance_score", 100),
            )[:5],
        }

    @staticmethod
    def _calculate_vulnerability(
        total_violations: int,
        critical_count: int,
        facility_count: int,
        states: List[str],
        trend: str,
    ) -> float:
        """
        Calculate a 1-10 vulnerability score.

        Factors that increase vulnerability (susceptibility to campaign pressure):
        - More violations = more evidence to cite
        - Critical violations = stronger regulatory angle
        - Multi-state = more jurisdictions to file complaints in
        - Worsening trend = demonstrates systemic failure
        """
        score = 5.0  # baseline

        # Violation volume
        if total_violations >= 50:
            score += 2.0
        elif total_violations >= 20:
            score += 1.0
        elif total_violations < 5:
            score -= 1.0

        # Critical violations
        if critical_count >= 10:
            score += 1.5
        elif critical_count >= 3:
            score += 0.5

        # Multi-state exposure (more regulatory surfaces)
        if len(states) >= 10:
            score += 1.0
        elif len(states) >= 5:
            score += 0.5

        # Trend
        if trend == "worsening":
            score += 1.0
        elif trend == "improving":
            score -= 0.5

        return max(1.0, min(10.0, round(score, 1)))

    @staticmethod
    def _suggest_campaign_angles(
        violations: List[Violation],
        facilities: List[Facility],
        vulnerability: float,
    ) -> List[str]:
        """Suggest campaign angles based on the data."""
        angles = []

        # Check for environmental violations
        env_violations = [
            v for v in violations
            if any(
                term in (v.violation_type or "").lower()
                for term in ["water", "air", "waste", "pollution", "discharge", "runoff"]
            )
        ]
        if env_violations:
            angles.append(
                f"Environmental: {len(env_violations)} environmental violations. "
                f"Clean Water Act / Clean Air Act citizen suit potential."
            )

        # Check for worker safety
        safety_violations = [
            v for v in violations
            if any(
                term in (v.violation_type or "").lower()
                for term in ["safety", "osha", "injury", "worker"]
            )
        ]
        if safety_violations:
            angles.append(
                f"Worker safety: {len(safety_violations)} safety violations. "
                f"Coalition angle with labor organizations."
            )

        # Check for animal welfare
        welfare_violations = [
            v for v in violations
            if any(
                term in (v.violation_type or "").lower()
                for term in ["animal", "welfare", "cruelty", "humane", "handling"]
            )
        ]
        if welfare_violations:
            angles.append(
                f"Animal welfare: {len(welfare_violations)} welfare violations. "
                f"Direct public pressure and media angle."
            )

        # Geographic concentration
        state_counts = {}
        for f in facilities:
            if f.state:
                state_counts[f.state] = state_counts.get(f.state, 0) + 1
        concentrated_states = [
            s for s, c in state_counts.items() if c >= 3
        ]
        if concentrated_states:
            angles.append(
                f"Geographic focus: concentrated in {', '.join(concentrated_states)}. "
                f"State-level regulatory campaign viable."
            )

        # Brand vulnerability
        if vulnerability >= 7:
            angles.append(
                "High vulnerability score -- consumer/brand pressure "
                "campaign is most likely to succeed."
            )

        if not angles:
            angles.append(
                "Insufficient data for targeted angle recommendation. "
                "Start with OSINT investigation to build evidence base."
            )

        return angles

    # --- Parsing ---

    @staticmethod
    def _parse_violation(data: Dict[str, Any]) -> Violation:
        """Parse API response into Violation dataclass."""
        return Violation(
            id=data.get("id", ""),
            facility_id=data.get("facility_id", ""),
            facility_name=data.get("facility_name", ""),
            company=data.get("company", ""),
            violation_type=data.get("violation_type", ""),
            severity=data.get("severity", "minor"),
            description=data.get("description", ""),
            date=date.fromisoformat(data["date"]) if data.get("date") else date.today(),
            inspector=data.get("inspector"),
            statute=data.get("statute"),
            fine_amount=data.get("fine_amount"),
            corrective_action=data.get("corrective_action"),
            status=data.get("status", "open"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            state=data.get("state"),
            source_url=data.get("source_url"),
        )

    @staticmethod
    def _parse_facility(data: Dict[str, Any]) -> Facility:
        """Parse API response into Facility dataclass."""
        return Facility(
            id=data.get("id", ""),
            name=data.get("name", ""),
            company=data.get("company", ""),
            facility_type=data.get("facility_type", ""),
            address=data.get("address", ""),
            state=data.get("state", ""),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            animal_count=data.get("animal_count"),
            species=data.get("species"),
            permits=data.get("permits"),
            violation_count=data.get("violation_count", 0),
            last_inspection=(
                date.fromisoformat(data["last_inspection"])
                if data.get("last_inspection")
                else None
            ),
            compliance_score=data.get("compliance_score"),
        )
