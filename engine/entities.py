from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class EntityType(str, Enum):
    CLUSTER = "cluster"
    NODE = "node"
    NAMESPACE = "namespace"
    SERVICE = "service"
    CONTAINER = "container"
    PROCESS = "process"
    AGENT = "agent"
    SESSION = "session"
    QUEUE = "queue"
    DATABASE = "database"
    CUSTOM = "custom"

class EntityState(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    RUNNING = "running"
    IDLE = "idle"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    STOPPED = "stopped"
    PENDING = "pending"
    SCALING = "scaling"

@dataclass
class Entity:
    id: str
    type: EntityType
    name: str
    state: EntityState = EntityState.UNKNOWN
    metrics: dict[str, Any] = field(default_factory=dict)
    children: list[str] = field(default_factory=list)
    parent: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "state": self.state.value,
            "metrics": self.metrics,
            "children": self.children,
            "parent": self.parent,
            "labels": self.labels,
            "annotations": self.annotations,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entity:
        return cls(
            id=data["id"],
            type=EntityType(data["type"]),
            name=data["name"],
            state=EntityState(data.get("state", "unknown")),
            metrics=data.get("metrics", {}),
            children=data.get("children", []),
            parent=data.get("parent"),
            labels=data.get("labels", {}),
            annotations=data.get("annotations", {}),
            source=data.get("source", ""),
        )
