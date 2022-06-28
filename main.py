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

# returns a dict of {map_md5: [score, score, ...]}
async def sort_scores(scores: list[Score]) -> dict[str, list[Score]]:
    result: dict[Beatmap, list[Score]] = defaultdict(list)

    for score in scores:
        beatmap = await usecases.beatmap.fetch_by_md5(score.map_md5)
        if not beatmap or not beatmap.has_leaderboard:
            continue

        result[score.map_md5].append(score)

    logger.info(f"Filtered scores into {len(result.keys()):,} beatmaps!")
    return dict(result)


async def get_scores() -> list[Score]:
    db_scores = []

    for table in ("scores", "scores_relax", "scores_ap"):
        _db_scores = await services.database.fetch_all(
            f"SELECT * FROM {table} WHERE completed > 1",  # get all non-failed scores
        )

        db_scores.extend(Score.from_dict(db_score) for db_score in _db_scores)

    logger.info(f"Got {len(db_scores):,} scores!")
    return db_scores


async def recalculate_score(beatmap: Beatmap, score: Score) -> None:
    try:
        beatmap_path = Path("/home/akatsuki/lets/.data/maps")
        osu_file_path = beatmap_path / f"{beatmap.id}.osu"

        usecases.performance.calculate_score(score, osu_file_path)
        await services.database.execute(
            f"UPDATE {score.mode.scores_table} SET pp = :pp WHERE id = :id",
            {"pp": score.pp, "id": score.id},
        )
    except Exception:
        logger.error(traceback.format_exc())


async def recalculate_map(beatmap: Beatmap, scores: list[Score]) -> None:
    await asyncio.gather(
        *[recalculate_score(beatmap, score) for score in scores],
        return_exceptions=True,
    )
    logger.info(f"Completed calculating {beatmap.song_name}!")


async def main() -> int:
    exit_code = 0

    try:
        await services.connect_services()

        scores = await get_scores()
        sorted_scores = await sort_scores(scores)

        for beatmap, scores in sorted_scores.items():
            asyncio.create_task(recalculate_map(beatmap, scores))

        logger.info(f"Finished recalculating scores")

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
