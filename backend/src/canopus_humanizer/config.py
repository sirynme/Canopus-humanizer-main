"""Configuration module for canopus-humanizer engine."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def find_project_root() -> Path:
    """Locate backend project root."""
    current = Path(__file__).resolve().parent
    for p in [current, current.parent, current.parent.parent]:
        if (p / "configs" / "global_config.json").exists() or (p / "rules").exists():
            return p
    return Path(__file__).resolve().parent.parent.parent


class ConfigNamespace:
    """Configuration container matching global_config.json and environment variables."""

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        d = config_dict or {}
        pipeline = d.get("pipeline_defaults", {})
        api_cfg = d.get("api_settings", {})

        # Core Identity
        self.APP_NAME: str = d.get("app_name", "canopus-humanizer")
        self.VERSION: str = d.get("version", "4.2.0")
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", d.get("environment", "production"))

        # Pipeline Aggressiveness & Style Defaults
        self.INTENSITY: float = float(os.getenv("CANOPUS_INTENSITY", pipeline.get("intensity", 70.0)))
        self.STYLE: str = os.getenv("CANOPUS_STYLE", pipeline.get("style", "academic"))

        # Stage Toggles
        self.ENABLE_SYNONYMS: bool = self._bool_env("CANOPUS_SYNONYMS", pipeline.get("enable_synonyms", True))
        self.SYNONYM_ALIGNMENT: float = float(os.getenv("CANOPUS_SYNONYM_ALIGNMENT", pipeline.get("synonym_alignment", 0.85)))
        self.RANDOM_ALIGNMENT: bool = self._bool_env("CANOPUS_RANDOM_ALIGNMENT", pipeline.get("random_alignment", False))

        self.ENABLE_PHRASE_REWRITE: bool = self._bool_env("CANOPUS_PHRASE_REWRITE", pipeline.get("enable_phrase_rewrite", True))
        self.ENABLE_DETERMINER_SWAP: bool = self._bool_env("CANOPUS_DETERMINER_SWAP", pipeline.get("enable_determiner_swap", True))
        self.ENABLE_DISCOURSE_ROTATE: bool = self._bool_env("CANOPUS_DISCOURSE_ROTATE", pipeline.get("enable_discourse_rotate", True))

        self.ENABLE_VOICE_TRANSFORM: bool = self._bool_env("CANOPUS_VOICE_TRANSFORM", pipeline.get("enable_voice_transform", False))
        self.ENABLE_SENTENCE_FUSION: bool = self._bool_env("CANOPUS_SENTENCE_FUSION", pipeline.get("enable_sentence_fusion", True))
        self.ENABLE_TRANSITION_INJECT: bool = self._bool_env("CANOPUS_TRANSITION_INJECT", pipeline.get("enable_transition_inject", False))
        self.ENABLE_CLAUSE_REORDER: bool = self._bool_env("CANOPUS_CLAUSE_REORDER", pipeline.get("enable_clause_reorder", False))
        self.ENABLE_WORD_REORDER: bool = self._bool_env("CANOPUS_WORD_REORDER", pipeline.get("enable_word_reorder", False))
        self.ENABLE_NOMINALIZATION: bool = self._bool_env("CANOPUS_NOMINALIZATION", pipeline.get("enable_nominalization", False))
        self.ENABLE_APPOSITIVE: bool = self._bool_env("CANOPUS_APPOSITIVE", pipeline.get("enable_appositive", False))
        self.ENABLE_CONTRACTION: bool = self._bool_env("CANOPUS_CONTRACTION", pipeline.get("enable_contraction", False))
        self.ENABLE_NGRAM_AUDIT: bool = self._bool_env("CANOPUS_NGRAM_AUDIT", pipeline.get("enable_ngram_audit", False))
        self.ENABLE_SPLIT_COMPOUND: bool = self._bool_env("CANOPUS_SPLIT_COMPOUND", pipeline.get("enable_split_compound", False))
        self.ENABLE_AI_TELL_SCRUBBER: bool = self._bool_env("CANOPUS_AI_TELL_SCRUBBER", pipeline.get("enable_ai_tell_scrubber", True))

        # Per-Stage Fire Rates (Probabilities: 0.0 to 1.0)
        self.VOICE_TRANSFORM_RATE: float = float(os.getenv("CANOPUS_VOICE_RATE", pipeline.get("voice_transform_rate", 0.0)))
        self.SENTENCE_FUSION_RATE: float = float(os.getenv("CANOPUS_FUSION_RATE", pipeline.get("sentence_fusion_rate", 0.20)))
        self.TRANSITION_INJECT_RATE: float = float(os.getenv("CANOPUS_TRANSITION_RATE", pipeline.get("transition_inject_rate", 0.0)))
        self.WORD_REORDER_RATE: float = float(os.getenv("CANOPUS_REORDER_RATE", pipeline.get("word_reorder_rate", 0.0)))
        self.NOMINALIZATION_RATE: float = float(os.getenv("CANOPUS_NOMINAL_RATE", pipeline.get("nominalization_rate", 0.0)))
        self.APPOSITIVE_RATE: float = float(os.getenv("CANOPUS_APPOSITIVE_RATE", pipeline.get("appositive_rate", 0.0)))
        self.DISCOURSE_ROTATE_RATE: float = float(os.getenv("CANOPUS_DISCOURSE_RATE", pipeline.get("discourse_rotate_rate", 0.50)))

        # API Security & Server
        self.AUTH_REQUIRED: bool = self._bool_env("AUTH_REQUIRED", api_cfg.get("auth_required", False))
        self.MAX_TEXT_LENGTH: int = int(api_cfg.get("max_text_length", 50000))
        self.RATE_LIMIT_PER_MINUTE: int = int(api_cfg.get("rate_limit_per_minute", 120))

    @staticmethod
    def _bool_env(var_name: str, default: bool) -> bool:
        val = os.getenv(var_name)
        if val is None:
            return bool(default)
        return val.lower() in ("true", "1", "yes", "on")


def load_config(config_path: Optional[str] = None) -> ConfigNamespace:
    """Load configuration from global_config.json with environment variable overrides."""
    root = find_project_root()
    path = Path(config_path) if config_path else root / "configs" / "global_config.json"

    config_dict = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                config_dict = json.load(f)
        except Exception as e:
            print(f"[Warning] Failed to parse global_config.json: {e}")

    return ConfigNamespace(config_dict)


GLOBAL_CONFIG = load_config()
