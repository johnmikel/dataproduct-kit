from __future__ import annotations

import tomllib
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator

from dataproduct_kit.models import StrictModel
from dataproduct_kit.profiles import DEFAULT_PROFILE, ReadinessProfile

CONFIG_FILENAME = "dataproduct-kit.toml"


class ConfigLoadError(ValueError):
    pass


class CiConfig(StrictModel):
    include: list[str] = Field(default_factory=lambda: ["**"])
    exclude: list[str] = Field(default_factory=list)
    fail_on: Literal["fail", "warn"] = "fail"
    profile: ReadinessProfile = DEFAULT_PROFILE


class SuppressionConfig(StrictModel):
    code: str
    path: str
    reason: str
    expires: date

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason must not be blank")
        return value


class KitConfig(StrictModel):
    ci: CiConfig = Field(default_factory=CiConfig)
    suppressions: list[SuppressionConfig] = Field(default_factory=list)


def load_config(root: Path) -> KitConfig:
    root = root.resolve()
    config_path = root / CONFIG_FILENAME
    if not config_path.exists():
        return KitConfig()
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigLoadError(f"{CONFIG_FILENAME}: TOML parse error: {error}") from error
    try:
        return KitConfig.model_validate(payload)
    except ValidationError as error:
        details = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
        raise ConfigLoadError(f"{CONFIG_FILENAME}: {details}") from error
