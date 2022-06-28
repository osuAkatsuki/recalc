from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from constants.mode import Mode
from constants.mods import Mods
from constants.score_status import ScoreStatus


@dataclass
class Score:
    id: int
    map_md5: str

    user_id: int

    mode: Mode
    mods: Mods

    pp: float
    sr: float

    score: int
    max_combo: int
    acc: float

    n300: int
    n100: int
    n50: int
    nmiss: int
    ngeki: int
    nkatu: int

    passed: bool
    quit: bool
    full_combo: bool
    status: ScoreStatus

    time: int
    time_elapsed: int = 0  # TODO: store this in db

    rank: int = 0
    old_best: Optional[Score] = None
    using_patcher: bool = False

    @property
    def db_dict(self) -> dict:
        return {
            "beatmap_md5": self.map_md5,
            "userid": self.user_id,
            "score": self.score,
            "max_combo": self.max_combo,
            "full_combo": self.full_combo,
            "mods": self.mods.value,
            "300_count": self.n300,
            "100_count": self.n100,
            "50_count": self.n50,
            "katus_count": self.nkatu,
            "gekis_count": self.ngeki,
            "misses_count": self.nmiss,
            "time": self.time,
            "play_mode": self.mode.as_vn,
            "completed": self.status.value,
            "accuracy": self.acc,
            "pp": self.pp,
            "patcher": self.using_patcher,
            # "playtime": self.time_elapsed,
        }

    @classmethod
    def from_dict(cls, result: dict) -> Score:
        return cls(
            id=result["id"],
            map_md5=result["beatmap_md5"],
            user_id=result["userid"],
            score=result["score"],
            max_combo=result["max_combo"],
            full_combo=result["full_combo"],
            mods=Mods(result["mods"]),
            n300=result["300_count"],
            n100=result["100_count"],
            n50=result["50_count"],
            nkatu=result["katus_count"],
            ngeki=result["gekis_count"],
            nmiss=result["misses_count"],
            time=int(result["time"]),
            mode=Mode.from_lb(result["play_mode"], result["mods"]),
            status=ScoreStatus(result["completed"]),
            acc=result["accuracy"],
            pp=result["pp"],
            sr=0.0,  # irrelevant in this case
            # time_elapsed=result["playtime"],
            passed=result["completed"] > ScoreStatus.FAILED,
            quit=result["completed"] == ScoreStatus.QUIT,
        )
