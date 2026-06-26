from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TraceNode:
    node_id: str
    node_type: str
    label: str
    actor: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TraceEdge:
    source: str
    target: str
    relation: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TraceGraph:
    trace_id: str
    nodes: list[TraceNode]
    edges: list[TraceEdge]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


@dataclass(frozen=True)
class TraceReport:
    trace_id: str
    graph: TraceGraph
    trigger_source: dict[str, Any]
    chain_nodes: list[dict[str, Any]]
    context_sources: list[dict[str, Any]]
    call_details: list[dict[str, Any]]
    impact_scope: dict[str, Any]
    evidence_refs: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "graph": self.graph.to_dict(),
            "trigger_source": self.trigger_source,
            "chain_nodes": self.chain_nodes,
            "context_sources": self.context_sources,
            "call_details": self.call_details,
            "impact_scope": self.impact_scope,
            "evidence_refs": self.evidence_refs,
        }
