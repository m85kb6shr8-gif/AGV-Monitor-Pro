"""Data models for AGV monitoring."""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class AlarmType(str, Enum):
    """Alarm types."""
    MANUAL = "MANUAL"
    ERROR = "ERROR"
    FAULT = "FAULT"


@dataclass
class AGVStatus:
    """Status of a single AGV from MQTT."""
    agv_id: int
    auto: bool
    error: bool
    event_fault: List[str] = field(default_factory=list)
    agv_state: str = ""
    raw_data: dict = field(default_factory=dict)


@dataclass
class AlarmState:
    """Track alarm state per AGV per alarm type."""
    agv_id: int
    alarm_type: AlarmType
    is_active: bool = False
    last_triggered: Optional[float] = None
    
    def __hash__(self):
        return hash((self.agv_id, self.alarm_type))
    
    def __eq__(self, other):
        if not isinstance(other, AlarmState):
            return False
        return self.agv_id == other.agv_id and self.alarm_type == other.alarm_type


@dataclass
class AGVMonitorState:
    """UI state for a single AGV."""
    agv_id: int
    agv_state: str = "NONE"
    auto: bool = True
    monitor_enabled: bool = True
    is_alarming: bool = False
    alarm_type: Optional[AlarmType] = None
    fault_codes: List[str] = field(default_factory=list)
