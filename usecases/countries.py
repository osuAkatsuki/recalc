from __future__ import annotations

import asyncio

import logger
import services

COUNTRIES: dict[int, str] = {}
FIVE_MINUTES = 60 * 5


async def get_country(user_id: int) -> str:
    if user_id in COUNTRIES:
        return COUNTRIES[user_id]

    country = await services.database.fetch_val(
        "SELECT country FROM users_stats WHERE id = :id",
        {"id": user_id},
    )

    if not country:
        COUNTRIES[user_id] = "XX"
        return "XX"  # xd

    COUNTRIES[user_id] = country
    return country
