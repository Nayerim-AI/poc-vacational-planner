from __future__ import annotations

from app.models.schemas import Preferences


class PreferencesTool:
    def merge_with_defaults(self, incoming: Preferences) -> Preferences:
        return Preferences(**incoming.dict())
