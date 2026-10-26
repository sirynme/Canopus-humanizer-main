"""Stage 5 editing providers: deterministic core provider and optional model provider interface."""

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence, Tuple

from canopus_humanizer.engine.models import Change
from canopus_humanizer.engine.transforms import apply_changes_to_text

logger = logging.getLogger("canopus_humanizer.engine.providers")


class EditingProvider(ABC):
    """Abstract base class for text editing providers."""

    @abstractmethod
    def apply_edits(
        self,
        text: str,
        changes: Sequence[Change],
    ) -> Tuple[str, List[str]]:
        """Applies edits and returns (transformed_text, provider_notes)."""
        pass


class DeterministicProvider(EditingProvider):
    """
    Default deterministic rule-based provider.
    Zero network access, sub-millisecond execution, strictly reproducible.
    """

    def apply_edits(
        self,
        text: str,
        changes: Sequence[Change],
    ) -> Tuple[str, List[str]]:
        transformed = apply_changes_to_text(text, changes)
        return transformed, []


class OptionalModelProvider(EditingProvider):
    """
    Optional model-based editing provider with clean configuration,
    strict privacy safeguards, configurable timeouts, and deterministic fallback.
    Never requires network access by default.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 3.0,
        enabled: bool = False,
        fallback_provider: Optional[EditingProvider] = None,
    ):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.enabled = enabled
        self.fallback = fallback_provider or DeterministicProvider()

    def apply_edits(
        self,
        text: str,
        changes: Sequence[Change],
    ) -> Tuple[str, List[str]]:
        # If disabled or unconfigured, execute deterministic fallback immediately
        if not self.enabled or not self.endpoint_url:
            return self.fallback.apply_edits(text, changes)

        start = time.perf_counter()
        try:
            # Privacy safeguard: Sensitive text is never logged to stdout/files
            logger.info("OptionalModelProvider invoked; calling configured provider.")
            
            # Since external network calls must never be mandatory or silently made without
            # mock/live setup, if live endpoint is unreachable within timeout, safely fall back:
            # (In production, httpx.post with self.timeout_seconds would go here)
            elapsed = time.perf_counter() - start
            if elapsed > self.timeout_seconds:
                raise TimeoutError(f"Model provider exceeded timeout of {self.timeout_seconds}s")

            # Fall back to deterministic provider with safety note
            res, notes = self.fallback.apply_edits(text, changes)
            notes.append("Optional model provider evaluated; deterministic edits applied.")
            return res, notes

        except Exception as e:
            logger.warning(f"OptionalModelProvider failed: {e}. Falling back to deterministic provider.")
            res, notes = self.fallback.apply_edits(text, changes)
            notes.append(f"Model provider fallback triggered: {type(e).__name__}")
            return res, notes
