"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ForecastConfig:
    """Validated access to the experiment configuration."""

    raw: dict[str, Any]
    path: Path

    @property
    def http(self) -> dict[str, Any]:
        return self.raw["http"]

    @property
    def paths(self) -> dict[str, Path]:
        return {name: Path(value) for name, value in self.raw["paths"].items()}

    @property
    def topics(self) -> dict[str, dict[str, Any]]:
        # Prefer CrossRef topics (enabled replacement for OpenAlex); fall back to OpenAlex
        if "crossref" in self.raw and self.raw["crossref"].get("enabled", False):
            academic = self.raw["crossref"]["topics"]
        else:
            academic = self.raw["openalex"]["topics"]
        corporate = self.raw["gdelt"]["topics"]
        if set(academic) != set(corporate):
            raise ValueError("Academic and GDELT must define the same topic keys")
        return academic


def load_config(path: str | Path) -> ForecastConfig:
    """Load YAML configuration and validate required sections."""

    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError("Configuration root must be a mapping")
    required = {"version", "paths", "http", "gdelt", "scoring"}
    # At least one academic source must be present
    if "openalex" not in raw and "crossref" not in raw:
        raise ValueError("Configuration must define either 'openalex' or 'crossref' academic source")
    missing = required.difference(raw)
    if missing:
        raise ValueError(f"Missing configuration sections: {sorted(missing)}")
    if str(raw["version"]) != "00":
        raise ValueError("This experiment requires configuration version 00")
    return ForecastConfig(raw=raw, path=config_path)
