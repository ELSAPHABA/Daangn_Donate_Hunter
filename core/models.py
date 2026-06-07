from __future__ import annotations

from dataclasses import dataclass


ALL_KEYWORD = "전체"


@dataclass(frozen=True)
class Region:
    full_name: str
    code: str

    @property
    def dong_name(self) -> str:
        return self.full_name.split()[-1] if self.full_name.split() else self.full_name


@dataclass(frozen=True)
class Subscription:
    region: Region
    keyword: str
    detect_link: str


@dataclass(frozen=True)
class ScrapedItem:
    title: str
    url: str
