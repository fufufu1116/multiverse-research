from dataclasses import dataclass, field
from typing import List

@dataclass(frozen=True)
class MissionPacket:
    mission_id: str
    objective: str
    inputs: List[str] = field(default_factory=list)
    canonical_refs: List[str] = field(default_factory=list)
    current_state: str = ""
    assumptions: List[str] = field(default_factory=list)
    allowed_actions: List[str] = field(default_factory=list)
    prohibited_actions: List[str] = field(default_factory=list)
    required_evidence: List[str] = field(default_factory=list)
    output_schema: str = ""
    completion_condition: str = ""
    stop_conditions: List[str] = field(default_factory=list)
    continuous_execution: bool = True

    def validate(self) -> None:
        if not self.mission_id.strip(): raise ValueError("mission_id required")
        if not self.objective.strip(): raise ValueError("objective required")
        if not self.completion_condition.strip(): raise ValueError("completion_condition required")
        if not self.required_evidence: raise ValueError("required_evidence required")
        if not self.stop_conditions: raise ValueError("stop_conditions required")
        if not self.prohibited_actions: raise ValueError("prohibited_actions required")
