from __future__ import annotations

from typing import Literal

ReadinessProfile = Literal["starter", "production", "regulated"]

DEFAULT_PROFILE: ReadinessProfile = "starter"
PROFILE_NAMES: tuple[ReadinessProfile, ...] = ("starter", "production", "regulated")
