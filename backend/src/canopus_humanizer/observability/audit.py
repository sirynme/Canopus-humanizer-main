"""Structured audit logging without leaking confidential document content."""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AuditEvent:
    """Privacy-preserving structured audit event record."""
    timestamp: float
    request_id: str
    engine_version: str
    ruleset_versions: Tuple[str, ...]
    duration_ms: float
    status: str
    input_char_count: int
    output_char_count: int
    modifications_count: int
    rules_applied: Tuple[str, ...]
    issues_count: int
    error_code: Optional[str] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class AuditLogger:
    """Logger recording operational metrics and security events without document text."""

    def __init__(self, logger_name: str = "canopus_humanizer.audit", log_document_content: bool = False):
        self.logger = logging.getLogger(logger_name)
        self.log_document_content = log_document_content

    def record_event(self, event: AuditEvent) -> None:
        """Records the structured audit event."""
        if event.status == "success":
            self.logger.info("AUDIT_EVENT: %s", event.to_json())
        elif event.status in ("rejected", "warning"):
            self.logger.warning("AUDIT_EVENT: %s", event.to_json())
        else:
            self.logger.error("AUDIT_EVENT: %s", event.to_json())
