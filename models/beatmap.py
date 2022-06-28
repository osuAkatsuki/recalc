from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from constants.mode import Mode
from constants.ranked_status import RankedStatus


@dataclass
class Beatmap:
    md5: str
    id: int
    set_id: int

    song_name: str

    status: RankedStatus

    plays: int
    passes: int
    mode: Mode

    od: float
    ar: float

    difficulty_std: float
    difficulty_taiko: float
    difficulty_ctb: float
    difficulty_mania: float

    hit_length: int

    last_update: int = 0

    max_combo: int = 0
    bpm: int = 0
    filename: str = ""
    frozen: bool = False
    rating: Optional[float] = None

    @property
    def gives_pp(self) -> bool:
        return self.status in (RankedStatus.RANKED, RankedStatus.APPROVED)

    @property
    def db_dict(self) -> dict:
        return {
            "beatmap_md5": self.md5,
            "beatmap_id": self.id,
            "beatmapset_id": self.set_id,
            "song_name": self.song_name,
            "ranked": self.status.value,
            "playcount": self.plays,
            "passcount": self.passes,
            "mode": self.mode.value,
            "od": self.od,
            "ar": self.ar,
            "difficulty_std": self.difficulty_std,
            "difficulty_taiko": self.difficulty_taiko,
            "difficulty_ctb": self.difficulty_ctb,
            "difficulty_mania": self.difficulty_mania,
            "hit_length": self.hit_length,
            "latest_update": self.last_update,
            "max_combo": self.max_combo,
            "bpm": self.bpm,
            "file_name": self.filename,
            "ranked_status_freezed": self.frozen,
            "rating": self.rating,
        }

    @classmethod
    def from_dict(cls, result: dict) -> Beatmap:
        return cls(
            md5=result["beatmap_md5"],
            id=result["beatmap_id"],
            set_id=result["beatmapset_id"],
            song_name=result["song_name"],
            status=RankedStatus(result["ranked"]),
            plays=result["playcount"],
            passes=result["passcount"],
            mode=Mode(result["mode"]),
            od=result["od"],
            ar=result["ar"],
            difficulty_std=result["difficulty_std"],
            difficulty_taiko=result["difficulty_taiko"],
            difficulty_ctb=result["difficulty_ctb"],
            difficulty_mania=result["difficulty_mania"],
            hit_length=result["hit_length"],
            last_update=result["latest_update"],
            max_combo=result["max_combo"],
            bpm=result["bpm"],
            filename=result["file_name"],
            frozen=result["ranked_status_freezed"],
            rating=result["rating"],
        )