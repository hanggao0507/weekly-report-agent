from __future__ import annotations

from abc import ABC, abstractmethod

from src.models import MemberProfile, NormalizedWorkItem, TimeWindow


class DataSourceAdapter(ABC):
    @abstractmethod
    def fetch(
        self,
        member: MemberProfile | None,
        window: TimeWindow,
        source_config: object | None = None,
    ) -> list[NormalizedWorkItem]:
        raise NotImplementedError

