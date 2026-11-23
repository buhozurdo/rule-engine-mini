"""
Observability and audit tracing for rule-engine-mini.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TraceStep:
    """Represents a single evaluated AST node in the execution trace."""

    path: str
    node: Any
    result: Any
    elapsed_us: float
    short_circuited: bool = False
    children: List["TraceStep"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace step to a JSON-serializable dictionary."""
        return {
            "path": self.path,
            "node": self.node,
            "result": self.result,
            "elapsed_us": self.elapsed_us,
            "short_circuited": self.short_circuited,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class ExecutionTrace:
    """Comprehensive forensic audit trail of a rule evaluation."""

    result: Any
    passed: bool
    elapsed_us: float
    resolved_vars: Dict[str, Any] = field(default_factory=dict)
    failed_node: Optional[Any] = None
    failed_path: Optional[str] = None
    root_step: Optional[TraceStep] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the entire audit trace to a structured dictionary for SIEM/logging."""
        return {
            "result": self.result,
            "passed": self.passed,
            "elapsed_us": round(self.elapsed_us, 3),
            "failed_path": self.failed_path,
            "failed_node": self.failed_node,
            "resolved_vars": self.resolved_vars,
            "root_step": self.root_step.to_dict() if self.root_step else None,
        }
