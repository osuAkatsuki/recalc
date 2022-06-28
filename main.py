#!/usr/bin/env python3.9
from __future__ import annotations

import asyncio
import traceback
from collections import defaultdict

import logger
import services
import usecases.beatmap
import usecases.performance
from models.beatmap import Beatmap
from models.score import Score
from objects.path import Path


async def get_scores() -> list[Score]:
    db_scores = []

    for table in ("scores", "scores_relax", "scores_ap"):
        _db_scores = await services.database.fetch_all(
            f"SELECT * FROM {table} WHERE completed > 1 ORDER BY beatmap_md5",  # get all non-failed scores
        )

        db_scores.extend(Score.from_dict(db_score) for db_score in _db_scores)

    logger.info(f"Got {len(db_scores):,} scores!")
    return db_scores


async def recalculate_scores(scores: list[Score]) -> None:
    # stupid temp shit for memory efficiency
    _scores: defaultdict[str, list[Score]] = defaultdict(list)
    bmap_count = len(_scores)

    for score in scores:
        _scores[score.map_md5].append(score)

    for beatmap_md5 in list(_scores.keys()):
        score_list = _scores[beatmap_md5]

        beatmap = await usecases.beatmap.fetch_by_md5(beatmap_md5)
        if not beatmap or not beatmap.has_leaderboard:
            del _scores[beatmap_md5]
            continue

        del _scores[beatmap_md5]
        asyncio.create_task(recalculate_map(beatmap, score_list))

    del _scores
    logger.info(f"Calculated scores for {len(bmap_count):,} beatmaps!")


async def recalculate_map(beatmap: Beatmap, scores: list[Score]) -> None:
    await asyncio.gather(
        *[recalculate_score(beatmap, score) for score in scores],
        return_exceptions=True,
    )

    logger.info(f"Completed calculating {beatmap.song_name}!")
    del beatmap


async def recalculate_score(beatmap: Beatmap, score: Score) -> None:
    try:
        beatmap_path = Path("/home/akatsuki/lets/.data/maps")
        osu_file_path = beatmap_path / f"{beatmap.id}.osu"
        if not await usecases.performance.check_local_file(
            osu_file_path,
            beatmap.id,
            beatmap.md5,
        ):
            await services.database.execute(
                f"DELETE FROM {score.mode.scores_table} WHERE id = :id",
                {"id": score.id},
            )

        usecases.performance.calculate_score(score, osu_file_path)
        await services.database.execute(
            f"UPDATE {score.mode.scores_table} SET pp = :pp WHERE id = :id",
            {"pp": score.pp, "id": score.id},
        )
    except Exception:
        logger.error(traceback.format_exc())


async def main() -> int:
    exit_code = 0

    usecases.performance.ensure_oppai()

    try:
        await services.connect_services()

        scores = await get_scores()
        await recalculate_scores(scores)

        # TODO: recalculate user pp, ranks
    except KeyboardInterrupt:
        exit_code = 0
    except:
        logger.error(traceback.format_exc())
        exit_code = 1

    await services.disconnect_services()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
