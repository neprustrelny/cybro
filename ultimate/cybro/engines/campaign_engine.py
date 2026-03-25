from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class Campaign:
    name: str
    objectives: List[str]
    constraints: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    aar_completed: bool = False
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def record_action(self, label: str, intent) -> None:
        self.actions.append(
            {"label": label, "intent": intent.to_dict(), "timestamp": datetime.utcnow()}
        )


class CampaignEngine:
    """Orchestrates long-running campaigns with AAR enforcement."""

    def __init__(self, audit_logger) -> None:
        self.current_campaign: Optional[Campaign] = None
        self.audit_logger = audit_logger

    def start(self, name: str, objectives: List[str], constraints: Dict[str, Any]) -> Campaign:
        if self.current_campaign and not self.current_campaign.aar_completed:
            raise RuntimeError("Cannot start new campaign before completing AAR.")
        self.current_campaign = Campaign(name=name, objectives=objectives, constraints=constraints)
        self.audit_logger.log_decision(
            {"phase": "campaign_start", "name": name, "objectives": objectives}
        )
        return self.current_campaign

    def complete_after_action_review(self, summary: str) -> None:
        if not self.current_campaign:
            raise RuntimeError("No campaign to review.")
        self.current_campaign.completed_at = datetime.utcnow()
        self.current_campaign.aar_completed = True
        self.audit_logger.log_decision(
            {
                "phase": "campaign_aar",
                "name": self.current_campaign.name,
                "summary": summary,
                "actions": len(self.current_campaign.actions),
            }
        )

    def record_action(self, label: str, intent) -> None:
        if not self.current_campaign:
            # Auto bootstrap a lightweight campaign if none running.
            self.start("default_campaign", ["maintain visibility"], {})
        self.current_campaign.record_action(label, intent)
