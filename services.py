from __future__ import annotations

from contextlib import AsyncExitStack

import aiohttp
import aioredis
import databases

import settings

database = databases.Database(
    "mysql+asyncmy://{user}:{passwd}@{host}:{port}/{name}".format(
        user=settings.DB_USER,
        passwd=settings.DB_PASS,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        name=settings.DB_NAME,
    ),
)

redis: aioredis.Redis = aioredis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
)

http: aiohttp.ClientSession

exit_stack = AsyncExitStack()


async def connect_services() -> None:
    global http
    http = aiohttp.ClientSession()

    await exit_stack.enter_async_context(database)
    await exit_stack.enter_async_context(redis)


async def disconnect_services() -> None:
    await http.close()
    await exit_stack.aclose()
