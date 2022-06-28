from __future__ import annotations

import asyncio
import random
import time
from typing import Optional

import services
import settings
from constants.mode import Mode
from constants.ranked_status import RankedStatus
from models.beatmap import Beatmap

MD5_CACHE: dict[str, Beatmap] = {}
UPDATED_CACHE: dict[str, Beatmap] = {}
UNSUB_CACHE: set[str] = set()


async def update_beatmap(beatmap: Beatmap) -> Optional[Beatmap]:
    if not beatmap.deserves_update:
        return beatmap

    if updated_beatmap := UPDATED_CACHE.get(beatmap.md5):
        return updated_beatmap

    new_beatmap = await id_from_api(beatmap.id)
    if new_beatmap:
        # handle deleting the old beatmap etc.

        if new_beatmap.md5 != beatmap.md5:
            # delete any instances of the old map
            MD5_CACHE.pop(beatmap.md5, None)

            await services.database.execute(
                "DELETE FROM beatmaps WHERE beatmap_md5 = :old_md5",
                {"old_md5": beatmap.md5},
            )

            for table in ("scores", "scores_relax", "scores_ap"):
                await services.database.execute(
                    f"DELETE FROM {table} WHERE beatmap_md5 = :old_md5",
                    {"old_md5": beatmap.md5},
                )

            if beatmap.frozen:
                # if the previous version is status frozen, we should force the old status on the new version
                new_beatmap.status = beatmap.status

            UPDATED_CACHE[beatmap.md5] = new_beatmap
    else:
        # it's now unsubmitted!
        await services.database.execute(
            "DELETE FROM beatmaps WHERE beatmap_md5 = :old_md5",
            {"old_md5": beatmap.md5},
        )

        for table in ("scores", "scores_relax", "scores_ap"):
            await services.database.execute(
                f"DELETE FROM {table} WHERE beatmap_md5 = :old_md5",
                {"old_md5": beatmap.md5},
            )

        return None

    # update for new shit
    new_beatmap.last_update = int(time.time())

    asyncio.create_task(save(new_beatmap))  # i don't trust mysql for some reason
    MD5_CACHE[new_beatmap.md5] = new_beatmap

    return new_beatmap


async def fetch_by_md5(md5: str) -> Optional[Beatmap]:
    if md5 in UNSUB_CACHE:
        return None

    if beatmap := md5_from_cache(md5):
        return beatmap

    if beatmap := await md5_from_database(md5):
        MD5_CACHE[md5] = beatmap

        return beatmap

    if beatmap := await md5_from_api(md5):
        MD5_CACHE[md5] = beatmap

        return beatmap

    UNSUB_CACHE.add(md5)


def md5_from_cache(md5: str) -> Optional[Beatmap]:
    return MD5_CACHE.get(md5)


async def md5_from_database(md5: str) -> Optional[Beatmap]:
    db_result = await services.database.fetch_one(
        "SELECT * FROM beatmaps WHERE beatmap_md5 = :md5",
        {"md5": md5},
    )

    if not db_result:
        return None

    bmap = Beatmap.from_dict(db_result)
    return await update_beatmap(bmap)


GET_BEATMAP_URL = "https://old.ppy.sh/api/get_beatmaps"


async def save(beatmap: Beatmap) -> None:
    await services.database.execute(
        (
            "REPLACE INTO beatmaps (beatmap_id, beatmapset_id, beatmap_md5, song_name, ar, od, mode, rating, "
            "difficulty_std, difficulty_taiko, difficulty_ctb, difficulty_mania, max_combo, hit_length, bpm, playcount, "
            "passcount, ranked, latest_update, ranked_status_freezed, file_name) VALUES (:beatmap_id, :beatmapset_id, :beatmap_md5, :song_name, "
            ":ar, :od, :mode, :rating, :difficulty_std, :difficulty_taiko, :difficulty_ctb, :difficulty_mania, :max_combo, :hit_length, :bpm, "
            ":playcount, :passcount, :ranked, :latest_update, :ranked_status_freezed, :file_name)"
        ),
        beatmap.db_dict,
    )


async def md5_from_api(md5: str) -> Optional[Beatmap]:
    api_key = random.choice(settings.API_KEYS)

    async with services.http.get(
        GET_BEATMAP_URL,
        params={"k": api_key, "h": md5},
    ) as response:
        if not response or response.status != 200:
            return None

        response_json = await response.json()
        if not response_json:
            return None

    beatmaps = parse_from_osu_api(response_json)

    for beatmap in beatmaps:
        asyncio.create_task(save(beatmap))

    for beatmap in beatmaps:
        if beatmap.md5 == md5:
            return beatmap


async def id_from_api(id: int) -> Optional[Beatmap]:
    api_key = random.choice(settings.API_KEYS)

    async with services.http.get(
        GET_BEATMAP_URL,
        params={"k": api_key, "b": id},
    ) as response:
        if not response or response.status != 200:
            return None

        response_json = await response.json()
        if not response_json:
            return None

    beatmaps = parse_from_osu_api(response_json)

    for beatmap in beatmaps:
        asyncio.create_task(save(beatmap))

    for beatmap in beatmaps:
        if beatmap.id == id:
            return beatmap


IGNORED_BEATMAP_CHARS = dict.fromkeys(map(ord, r':\/*<>?"|'), None)

FROZEN_STATUSES = (RankedStatus.RANKED, RankedStatus.APPROVED, RankedStatus.LOVED)


def parse_from_osu_api(
    response_json_list: list[dict],
    frozen: bool = False,
) -> list[Beatmap]:
    maps = []

    for response_json in response_json_list:
        md5 = response_json["file_md5"]
        id = int(response_json["beatmap_id"])
        set_id = int(response_json["beatmapset_id"])

        filename = ("{artist} - {title} ({creator}) [{version}].osu").format(
            **response_json
        )

        song_name = (
            ("{artist} - {title} [{version}]")
            .format(**response_json)
            .translate(IGNORED_BEATMAP_CHARS)
        )

        hit_length = int(response_json["hit_length"])

        if _max_combo := response_json.get("max_combo"):
            max_combo = int(_max_combo)
        else:
            max_combo = 0

        ranked_status = RankedStatus.from_osu_api(int(response_json["approved"]))
        if ranked_status in FROZEN_STATUSES:
            frozen = True  # beatmaps are always frozen when ranked/approved/loved

        mode = Mode(int(response_json["mode"]))

        if _bpm := response_json.get("bpm"):
            bpm = round(float(_bpm))
        else:
            bpm = 0

        od = float(response_json["diff_overall"])
        ar = float(response_json["diff_approach"])

        maps.append(
            Beatmap(
                md5=md5,
                id=id,
                set_id=set_id,
                song_name=song_name,
                status=ranked_status,
                plays=0,
                passes=0,
                mode=mode,
                od=od,
                ar=ar,
                difficulty_std=0.0,
                difficulty_taiko=0.0,
                difficulty_ctb=0.0,
                difficulty_mania=0.0,
                hit_length=hit_length,
                last_update=int(time.time()),
                max_combo=max_combo,
                bpm=bpm,
                filename=filename,
                frozen=frozen,
                rating=10.0,
            ),
        )

    return maps
